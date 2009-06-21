# requires twitpic:
# $ svn export http://python-twitpic.googlecode.com/svn/trunk/twitpic

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

def twitpic_it(dest, message):
    username,password = dest.local.split("+")
    if message.is_multipart():
        file = None
        
        for payload in message.get_payload():
            if payload.get_content_type() in IMAGES:
                file = tempfile.NamedTemporaryFile(suffix="."+payload.get_content_type().split("/")[1])
                file.write(payload.get_payload(decode=True))
                file.seek(0)
                break

        if file is not None:
            datagen, headers = multipart_encode({
                "username": username,
                "password": password,
                "message": message["Subject"],
                "media": file
            })
            file.close()

            request = urllib2.Request("http://twitpic.com/api/uploadAndPost",
                                      "".join(datagen),
                                      headers)
            log.msg(urllib2.urlopen(request).read())
        else:
            log.msg("No image found")
    else:
        log.msg("No file attached")

domains = {
    "twitpicit.org": [
        Script(r"[a-zA-Z_\-\.0-9]+\+[^@]+", "twitpic", twitpic_it),
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

# vim:ft=python:
