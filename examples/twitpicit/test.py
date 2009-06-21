#!/usr/bin/env python
import sys

from smtplib import SMTP
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

# TWITTER
USERNAME = "greut"
PASSWORD = "##########"

def main(argv):
    if len(argv) <> 3:
        print 'Usage %s "Message" image.jpg'
        return 0

    to = "%s+%s@twitpicit.org" % (USERNAME, PASSWORD)

    message = MIMEMultipart()
    message["Subject"] = argv[1]
    message["To"] = to
    
    fp = open(argv[2], "rb")
    message.attach(MIMEImage(fp.read()))
    fp.close()

    smtp = SMTP("localhost", "2525")
    smtp.sendmail("yoan@dosimple.ch", to, message.as_string())
    smtp.quit()
    return 1

if __name__ == "__main__":
    sys.exit(main(sys.argv))
