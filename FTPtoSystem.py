import ftplib
import os
import configparser
from dataclasses import dataclass
import requests
import traceback
import logging
import time


@dataclass
class Config:
    host: str
    telegram_token: str
    telegram_chat_id: str
    port: int = 21
    user: str = ""
    password: str = ""
    source_path: str = ''
    target_path: str = "videos"


def send_telegram_message(conf, message):
    url = f"https://api.telegram.org/bot{conf.telegram_token}/sendMessage"
    payload = {
        "chat_id": conf.telegram_chat_id,
        "text": message
    }
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        logging.error(f"Failed to send message: {response.content}")


def readconfig(file=f"{os.path.dirname(os.path.abspath(__file__))}/config.ini") -> Config:
    conf = configparser.ConfigParser(allow_no_value=True)
    conf.read(file)
    return Config(**conf['main'])


def is_directory(ftp, path):
    current = ftp.pwd()
    try:
        ftp.cwd(path)
        ftp.cwd(current)
        return True
    except ftplib.error_perm:
        return False
    except EOFError as e:
        logging.error(f"EOFError while checking if {path} is a directory: {e}")
        reconnect_ftp(ftp, conf)
        return False
    except ConnectionAbortedError as e:
        logging.error(f"ConnectionAbortedError while checking if {path} is a directory: {e}")
        reconnect_ftp(ftp, conf)
        return False


def transfer_file(ftp, conf, file):
    try:
        logging.info(f"Transferring file: {file}")
        ftp.voidcmd('TYPE I')
        ftp_file_size = ftp.size(file)
        local_file_path = f'{conf.target_path}/{os.path.basename(file)}'
        with open(local_file_path, 'wb') as local_file:
            ftp.retrbinary('RETR ' + file, local_file.write)

        local_file_size = os.path.getsize(local_file_path)
        if local_file_size == ftp_file_size:
            logging.info(f"Transfer and validation - ok: {file}")
            ftp.delete(file)
        else:
            logging.error(f"Validation failed: {file}")
            os.remove(local_file_path)

    except Exception as e:
        error_message = f"FTPloader\nTransfer error: {file}, {e}"
        logging.error(error_message)
        send_telegram_message(conf, error_message)  # Отправка сообщения в Telegram при возникновении ошибки
        reconnect_ftp(ftp, conf)


def reconnect_ftp(ftp, conf):
    while True:
        try:
            logging.info(f"Reconnecting to {conf.host}:{conf.port}")
            ftp.connect(conf.host, int(conf.port))
            ftp.login(user=conf.user, passwd=conf.password)
            return
        except Exception as e:
            logging.error(f"Error reconnecting: {e}")
            time.sleep(5)


def fileslist_and_transfer(ftp, conf):
    stack = [conf.source_path]
    noop_counter = 0
    while stack:
        current_path = stack.pop()
        logging.info(f"Listing files in {current_path}")
        try:
            entries = ftp.nlst(current_path)
        except ftplib.error_perm as e:
            logging.error(f"Error listing files in {current_path}: {e}")
            continue
        except EOFError as e:
            logging.error(f"EOFError while listing files in {current_path}: {e}")
            reconnect_ftp(ftp, conf)
            stack.append(current_path)
            continue
        except ConnectionAbortedError as e:
            logging.error(f"ConnectionAbortedError while listing files in {current_path}: {e}")
            reconnect_ftp(ftp, conf)
            stack.append(current_path)
            continue

        for entry in (path for path in entries if path not in ('.', '..')):
            full_path = f"{current_path}/{entry}".strip('/')
            if is_directory(ftp, full_path):
                stack.append(full_path)
            else:
                transfer_file(ftp, conf, full_path)

            # Отправляем команду NOOP каждые несколько файлов для поддержания соединения
            noop_counter += 1
            if noop_counter >= 5:
                try:
                    ftp.voidcmd("NOOP")
                    logging.info("Sent NOOP command to keep connection alive")
                except EOFError as e:
                    logging.error(f"EOFError while sending NOOP: {e}")
                    reconnect_ftp(ftp, conf)
                except ConnectionAbortedError as e:
                    logging.error(f"ConnectionAbortedError while sending NOOP: {e}")
                    reconnect_ftp(ftp, conf)
                noop_counter = 0


def tranfer_files_ftp(conf):
    logging.info(f"Target path: {conf.target_path}")
    if not os.path.exists(conf.target_path):
        os.mkdir(conf.target_path)

    with ftplib.FTP(timeout=300) as ftp:  # Увеличиваем таймаут до 300 секунд
        reconnect_ftp(ftp, conf)  # Подключаемся к FTP серверу

        fileslist_and_transfer(ftp, conf)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    conf = readconfig()
    try:
        tranfer_files_ftp(conf)
    except Exception as e:
        error_message = f"FTPloader\nError: {e}\n\nTraceback: {traceback.format_exc()}"
        logging.error(error_message)
        send_telegram_message(conf, error_message)
