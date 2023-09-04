import ftplib
import os
import configparser
from dataclasses import dataclass


@dataclass
class Config:
    host: str
    port: int = 21
    user: str = ""
    password: str = ""
    source_path: str = ''
    target_path: str = "videos"


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

    with ftplib.FTP() as ftp:
        ftp.connect(conf.host, int(conf.port))
        ftp.login(user=conf.user, passwd=conf.password)
        ftp.cwd(conf.source_path)

        files = fileslist(ftp)
        print(f"filelist:\n\t" + "\n\t".join(files))

        for file in files:
            try:
                with open(f'{conf.target_path}/{os.path.basename(file)}', 'wb') as local_file:
                    ftp.retrbinary('RETR ' + file, local_file.write)

                local_file_path = f'{conf.target_path}/{os.path.basename(file)}'
                local_file_size = os.path.getsize(local_file_path)
                ftp_file_size = ftp.size(file)

                if local_file_size == ftp_file_size and local_file_size != 0:
                    ftp.delete(file)
                    print(f"transfer and verification ok: {file}")
                else:
                    print(f"verification failed: {file}")
            except Exception as e:
                print(f"transfer error: {file}, {e}")


if __name__ == "__main__":
    conf = readconfig()
    tranfer_files_ftp(conf)
