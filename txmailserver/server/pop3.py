import os

from zope.interface import implements

from twisted.mail import pop3, maildir
from twisted.internet import protocol, defer

class UserInbox(maildir.MaildirMailbox):
    """
    maildir.MaildirMailbox already implements the pop3.IMailbox
    interface, so methods will only need to be defined to
    override the default behavior. For non-maildir mailboxes,
    you'd have to implement all of pop3.IMailbox. 
    """
    def __init__(self, userdir):
        inboxDir = os.path.join(userdir, 'Inbox')
        print "Expecting maildir to be %s" % inboxDir
        maildir.MaildirMailbox.__init__(self, inboxDir)

class POP3Protocol(pop3.POP3):
    debug = True
    
    def sendLine(self, line):
        if self.debug: print "POP3 SERVER:", line
        pop3.POP3.sendLine(self, line)

    def lineReceived(self, line):
        if self.debug: print "POP3 CLIENT:", line
        pop3.POP3.lineReceived(self, line)

class POP3Factory(protocol.Factory):
    protocol = POP3Protocol
    portal = None
    
    def buildProtocol(self, address):
        p = self.protocol()
        p.portal = self.portal
        p.factory = self
        return p
