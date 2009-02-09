from twisted.application import internet, service

from txmailserver import mailservice
from txmailserver.domain import Alias, Actual, Maillist, CatchAll


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
        
        # catch all
        Actual('post'),
        CatchAll('post-[0-9]+', 'post@sample.org'),

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
smtpPort = 2525
pop3Port = 2110
imap4Port = 2143

# setup the application
application = service.Application("smtp, pop and imap server")
svc = service.IServiceCollection(application)

# setup the mail service
ms = mailservice.MailService(mailboxDir, configDir, forwardDir, domains)

# setup the queue checker
queueTimer = ms.relayQueueTimer
if queueTimer:
    queueTimer.setServiceParent(svc)

# setup the SMTP server
smtpFactory = ms.getSMTPFactory()
smtp = internet.TCPServer(smtpPort, smtpFactory)
smtp.setServiceParent(svc)

# setup the whitelist queue timer
whitelistQueueTimer = smtpFactory.whitelistPurgeTimer
whitelistQueueTimer.setServiceParent(svc)

# setup the POP3 server
pop3Factory = ms.getPOP3Factory()
pop3 = internet.TCPServer(pop3Port, pop3Factory)
pop3.setServiceParent(svc)

# setup the IMAP server
imap4Factory = ms.getIMAP4Factory()
imap4 = internet.TCPServer(imap4Port, imap4Factory)
imap4.setServiceParent(svc)

# vim:ft=python:
