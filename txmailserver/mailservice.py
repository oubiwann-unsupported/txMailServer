import os
from email.Header import Header

from zope.interface import implements

from twisted.cred import portal
from twisted.mail import mail, relay, relaymanager

from txmailserver import auth
from txmailserver.smtp import SMTPFactory
from txmailserver.pop3 import POP3Factory
from txmailserver.imap4 import IMAP4Factory


class MailService(mail.MailService):

    def __init__(self, baseDir, configDir, forwardDir, validDomains,
                 relayServers=[], relayCheckInterval=15):
        mail.MailService.__init__(self)
        self.baseDir = baseDir
        self.configDir = configDir
        self.forwardDir = forwardDir
        self.validDomains = validDomains
        self.relayServers = relayServers
        self.relayCheckInterval = relayCheckInterval
        self.relayManager = None
        self.relayQueueTimer = None
        self.realm = auth.MailUserRealm(self.baseDir)
        self.portal = portal.Portal(self.realm)
        passwords = auth.passwordFileToDict(auth.getPasswords(configDir))
        self.checker = auth.CredentialsChecker(passwords)

        if not os.path.exists(self.forwardDir):
            os.mkdir(self.forwardDir)
        queue = relaymanager.Queue(self.forwardDir)
        self.queuer = relay.DomainQueuer(self)
        self.setQueue(queue)
        self.domains.setDefaultDomain(self.queuer)
        if relayServers:
            self.relayManager = relaymanager.SmartHostSMTPRelayingManager(
                queue)
            self.relayManager.fArgs += tuple(self.relayServers)
            self.relayQueueTimer = relaymanager.RelayStateHelper(
                self.relayManager, 15)

    def getSMTPFactory(self):
        factory = SMTPFactory(
            self.baseDir, self.configDir, self.validDomains, self.queuer)
        factory.configDir = self.configDir
        factory.portal = self.portal
        factory.portal.registerChecker(self.checker)
        self.smtpPortal = factory.portal
        return factory

    def getPOP3Factory(self):
        factory = POP3Factory()
        factory.portal = self.portal
        factory.portal.registerChecker(self.checker)
        return factory

    def getIMAP4Factory(self):
        factory = IMAP4Factory()
        factory.portal = self.portal
        factory.portal.registerChecker(self.checker)
        return factory

