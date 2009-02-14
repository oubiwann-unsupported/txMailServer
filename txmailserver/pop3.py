import os

from zope.interface import implements

from twisted.mail import pop3, maildir
from twisted.internet import protocol, defer
from twisted.python import log

from txmailserver.mailbox import Mailbox


class POP3Account(Mailbox):
    def __init__(self, userdir):
        Mailbox.__init__(self, os.path.join(userdir, "Inbox"))  


class POP3Protocol(pop3.POP3):
    debug = True
    
    def sendLine(self, line):
        if self.debug: log.msg("POP3 SERVER:", line)
        pop3.POP3.sendLine(self, line)

    def lineReceived(self, line):
        if self.debug: log.msg("POP3 CLIENT:", line)
        pop3.POP3.lineReceived(self, line)


class POP3Factory(protocol.Factory):
    protocol = POP3Protocol
    portal = None
    
    def buildProtocol(self, address):
        p = self.protocol()
        p.portal = self.portal
        p.factory = self
        return p

