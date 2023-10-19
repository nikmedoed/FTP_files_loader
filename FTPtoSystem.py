import ftplib
import os
import configparser
from dataclasses import dataclass
import requests
import traceback


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
        print(f"Failed to send message: {response.content}")


def readconfig(file=f"{os.path.dirname(os.path.abspath(__file__))}/config.ini") -> Config:
    conf = configparser.ConfigParser(allow_no_value=True)
    conf.read(file)
    return Config(**conf['main'])


def fileslist(ftp):
    level = []
    for entry in (path for path in ftp.nlst() if path not in ('.', '..')):
        try:
            ftp.cwd(entry)
            subfolder = fileslist(ftp)
            ftp.cwd('..')
            if len(subfolder):
                level.extend([f"{entry}/{i}" for i in subfolder])
            else:
                ftp.rmd(entry)
        except ftplib.error_perm:
            level.append(entry)
    return level


def tranfer_files_ftp(conf):
    print(conf.target_path)
    if not os.path.exists(conf.target_path):
        os.mkdir(conf.target_path)

    with ftplib.FTP(timeout=60) as ftp:
        ftp.connect(conf.host, int(conf.port))
        ftp.login(user=conf.user, passwd=conf.password)
        ftp.cwd(conf.source_path)

        files = fileslist(ftp)
        print(f"filelist:\n\t" + "\n\t".join(files))

        for file in files:
            try:
                ftp.voidcmd('TYPE I')
                ftp_file_size = ftp.size(file)
                local_file_path = f'{conf.target_path}/{os.path.basename(file)}'
                with open(local_file_path, 'wb') as local_file:
                    ftp.retrbinary('RETR ' + file, local_file.write)

                local_file_size = os.path.getsize(local_file_path)
                if local_file_size == ftp_file_size:
                    print(f"transfer and validation - ok: {file}")
                    ftp.delete(file)
                else:
                    print(f"validation failed: {file}")
                    os.remove(local_file_path)
            except Exception as e:
                error_message = f"FTPloader\nTransfer error: {file}, {e}"
                print(error_message)
                send_telegram_message(conf, error_message)  # Отправка сообщения в Telegram при возникновении ошибки


if __name__ == "__main__":
    conf = readconfig()
    try:
        tranfer_files_ftp(conf)
    except Exception as e:
        error_message = f"FTPloader\nError: {e}\n\nTraceback: {traceback.format_exc()}"
        print(error_message)
        send_telegram_message(conf, error_message)
