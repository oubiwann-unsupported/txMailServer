import os
from email.Header import Header

from zope.interface import implements

from twisted.cred import portal
from twisted.mail import mail, relay, relaymanager

from txmailserver import auth, server

class MailService(mail.MailService):

    def __init__(self, baseDir, configDir, forwardDir, validDomains):
        mail.MailService.__init__(self)
        self.baseDir = baseDir
        self.configDir = configDir
        self.forwardDir = forwardDir
        self.validDomains = validDomains
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
        self.relayManager = relaymanager.SmartHostSMTPRelayingManager(queue)
        # XXX pass this as a parameter
        self.relayManager.fArgs += ('shell3.adytum.us',)
        # XXX pass the time value as a parameter
        self.relayQueueTimer = relaymanager.RelayStateHelper(
            self.relayManager, 15)

    def getSMTPFactory(self):
        factory = server.smtp.SMTPFactory(
            self.baseDir, self.configDir, self.validDomains, self.queuer)
        factory.configDir = self.configDir
        factory.portal = self.portal
        factory.portal.registerChecker(self.checker)
        self.smtpPortal = factory.portal
        return factory

    def getPOP3Factory(self):
        factory = server.pop3.POP3Factory()
        factory.portal = self.portal
        factory.portal.registerChecker(self.checker)
        return factory

