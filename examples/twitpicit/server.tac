__author__ = "Yoan Blanc <yoan.dosimple.ch>"

import urllib2
import tempfile

from twisted.application import internet, service
from twisted.python import log

from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
register_openers() # hacking urllib2

from txmailserver import mailservice
from txmailserver.domain import Script


IMAGES = "image/gif", "image/png", "image/jpg"


def file_from_email(message, mimetypes=IMAGES):
    """Find a file of the given mimetypes in the message (email)"""
    file = None
    if message.is_multipart():
        for payload in message.get_payload():
            if payload.get_content_type() in IMAGES:
                file = tempfile.NamedTemporaryFile(suffix="."+payload.get_content_type().split("/")[1])
                file.write(payload.get_payload(decode=True))
                file.seek(0)
                break
    return file


def twitpic_it(dest, message):
    """Post the email to twitpic"""
    username,password = dest.local.split("+")
    
    file = file_from_email(message)

    if file is not None:
        datagen, headers = multipart_encode({
            "username": username,
            "password": password,
            "message": message["Subject"],
            "media": file
        })

        request = urllib2.Request("http://twitpic.com/api/uploadAndPost",
                                  "".join(datagen),
                                  headers)
        
        file.close()
        log.msg(urllib2.urlopen(request).read())
    else:
        log.msg("No image found")


domains = {
    "twitpicit.org": [
        Script(r"[a-zA-Z_\-\.0-9]+\+[^@]+", twitpic_it),
    ]
}


application = service.Application("smtp server")
svc = service.IServiceCollection(application)

# setup the mail service
ms = mailservice.MailService("mail",
                             "etc",
                             "queue",
                             domains)

# setup the queue checker
queueTimer = ms.relayQueueTimer
if queueTimer:
    queueTimer.setServiceParent(svc)

# setup the SMTP server
smtpFactory = ms.getSMTPFactory()
smtp = internet.TCPServer(2525, smtpFactory)
smtp.setServiceParent(svc)

