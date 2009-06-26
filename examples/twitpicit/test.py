#!/usr/bin/env python
import sys

from smtplib import SMTP
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

# TWITTER
USERNAME = None
PASSWORD = None

def main(argv):
    if len(argv) <> 3:
        print 'Usage %s image.jpg Message'
        return 0

    if USERNAME is None or PASSWORD is None:
        print 'Please edit username and password'
        return 0

    to = "%s+%s@twitpicit.org" % (USERNAME, PASSWORD)

    message = MIMEMultipart()
    message["Subject"] = "".join(argv[2:])
    message["To"] = to
    
    fp = open(argv[1], "rb")
    message.attach(MIMEImage(fp.read()))
    fp.close()

    smtp = SMTP("localhost", "2525")
    smtp.sendmail("yoan@dosimple.ch", to, message.as_string())
    smtp.quit()
    return 1

if __name__ == "__main__":
    sys.exit(main(sys.argv))
