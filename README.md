# FTP files to system loader
 Download all files by FTP from all directory in target path to directory in your system.

I need it to automatically download video records from my ip camera to file storage on SBC (nano pi neo 3). 
- I created free FTP hosting on ~~[www.uhostfull.com](http://www.uhostfull.com)~~ [runhosting.com](https://runhosting.com/)
- Set up FTP settings on camera
- Made everyday cron task for transferring files from FTP to my storage

Examplet cron task:
```shell
>>> crontab -e

0 */12 * * * python3 $HOME/exec/ftpLoad/FTPtoSystem.py

0 9,21 * * * timeout 2000 python3 $HOME/exec/ftpLoad/FTPtoSystem.py
```