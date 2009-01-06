import os
import sys
sys.path.append('.')

from twisted.cred import portal
from twisted.application import internet, service

import auth
import mailservice
from domain import Alias, Actual, Maillist

domains = {
    'sample.org': [
        # alice
        Actual('alice'),
        Alias('al', 'alice@sample.org'),

        # bob
        Actual('bob'),
        Alias('bob', 'bob@sample.org'),
        Alias('bob.dobilino', 'bob@sample.org'),

        # admin
        Alias('abuse', 'bob@sample.org'),
        Alias('postmaster', 'alice@sample.org'),

        # lists
        Maillist('test-list', [
            'alice@sample.org', 
            'bob@sample.org',
            ]),
        Maillist('list2', [
            'alice@sample.org',
            ]),
        Maillist('adytum-test-list', [
            'oubiwann@sample.org',
            'duncan@sample.org',
            ]),
    ],
    'example.com': [
        Alias('alice', 'alice@sample.org'),
        Alias('bob', 'bob@sample.org'),
        Alias('abuse', 'bob@sample.org'),
        Alias('postmaster', 'bob@sample.org'),
    ],
}

mailboxDir = 'Maildir'
configDir = 'etc'
forwardDir = 'queue'

# setup the application
application = service.Application("smtp and pop server")
sc = service.IServiceCollection(application)

# setup the mail service
mailService = mailservice.MailService(mailboxDir, configDir, forwardDir, domains)

# setup the queue checker
queueTimer = mailService.relayQueueTimer
queueTimer.setServiceParent(sc)


# setup the SMTP server
factory = mailService.getSMTPFactory()
smtp = internet.TCPServer(25, factory)
smtp.setServiceParent(sc)

# setup the whitelist queue timer
whitelistQueueTimer = factory.whitelistPurgeTimer
whitelistQueueTimer.setServiceParent(sc)

# setup the POP3 server
factory = mailService.getPOP3Factory()
pop3 = internet.TCPServer(110, factory)
pop3.setServiceParent(sc)
