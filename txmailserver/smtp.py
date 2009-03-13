import os
import re

from email.Header import Header
from subprocess import Popen, PIPE
from cStringIO import StringIO

from zope.interface import implements

from twisted.mail import smtp, maildir, mail
from twisted.internet import protocol, defer
from twisted.internet.threads import deferToThread
from twisted.application.internet import TimerService
from twisted.python import log

from txmailserver.util import runDspam, VALID_DSPAM_PREFIX
from txmailserver.domain import Alias, Actual, Maillist, CatchAll, Script


def processMessageData(user, data, dspamEnabled):
    if dspamEnabled:
        data = runDspam(user, data)
    return data

def scriptTask(user, data, callback):
    d = defer.Deferred()
    
    callback(user, data)

    d.callback(None)
    
    return d

class ScriptMessageWriter(object):
    implements(smtp.IMessage)

    def __init__(self, user, func):
        self.user = user
        self.func = func
        self.lines = []

    def lineReceived(self, line):
        self.lines.append(line)

    def eomReceived(self):
        log.msg("Message data complete.")
        self.lines.append('') # add a trailing newline
        data = '\n'.join(self.lines)
        return scriptTask(self.user, data, self.func)
    
    def connectionLost(self):
        log.msg("Connection lost unexpectedly!")
        # unexpected loss of connection; don't save
        del(self.lines)

class MaildirMessageWriter(object):
    implements(smtp.IMessage)

    def __init__(self, userDir, dspamEnabled):
        self.dspamEnabled = dspamEnabled
        self.user = os.path.split(userDir)[-1]
        if not os.path.exists(userDir):
            os.mkdir(userDir)
        inboxDir = os.path.join(userDir, 'INBOX')
        self.mailbox = maildir.MaildirMailbox(inboxDir)
        self.lines = []
    
    def lineReceived(self, line):
        self.lines.append(line)

    def eomReceived(self):
        # message is complete, store it
        log.msg("Message data complete.")
        self.lines.append('') # add a trailing newline
        data = '\n'.join(self.lines)
        messageData = processMessageData(self.user, data, self.dspamEnabled)
        return self.mailbox.appendMessage(messageData)

    def connectionLost(self):
        log.msg("Connection lost unexpectedly!")
        # unexpected loss of connection; don't save
        del(self.lines)

class MaildirListMessageWriter(MaildirMessageWriter):

    def __init__(self, userDirList, dspamEnabled):
        self.dspamEnabled = dspamEnabled
        self.mailboxes = {}
        self.lines = {}
        self.dspamUsers = {}
        for userDir in userDirList:
            if not os.path.exists(userDir):
                os.mkdir(userDir)
            inboxDir = os.path.join(userDir, 'INBOX')
            self.mailboxes[userDir] = maildir.MaildirMailbox(inboxDir)
            self.lines[userDir] = []

    def lineReceived(self, line):
        for key in self.lines.keys():
            self.lines[key].append(line)

    def eomReceived(self):
        dl = []
        for key in self.lines.keys():
            # message is complete, store it
            self.lines[key].append('')
            log.msg("Message data complete for %s." % key)
            user = os.path.split(key)[-1]
            data = '\n'.join(self.lines[key])
            messageData = processMessageData(user, data, dspamEnabled)
            dl.append(self.mailboxes[key].appendMessage(messageData))
        return defer.DeferredList(dl)

class LocalDelivery(object):
    implements(smtp.IMessageDelivery)

    def __init__(self, baseDir, validDomains, domainQueuer, dspamEnabled):
        if not os.path.isdir(baseDir):
            raise ValueError, "'%s' is not a directory" % baseDir
        self.baseDir = baseDir
        self.validDomains = validDomains
        self.domainQueuer = domainQueuer
        self.dspamEnabled = dspamEnabled
        self.blacklist = self.whitelist = self.whitelistQueue = []
    
    def receivedHeader(self, helo, origin, recipients):
        myHostname, clientIP = helo
        headerValue = "by %s from %s with ESMTP ; %s" % (
            myHostname, clientIP, smtp.rfc822date())
        # email.Header.Header used for automatic wrapping of long lines
        return "Received: %s" % Header(headerValue)

    def updateWhitelist(self, user):
        if user not in self.whitelist:
            self.whitelistQueue.append(user)

    def validateFrom(self, helo, originAddress):
        log.msg("validateFrom(): %s" % originAddress)
        if originAddress in self.whitelist + self.whitelistQueue:
            return originAddress
        elif originAddress in self.blacklist:
            log.msg("Sender in blacklist! Denying message...")
            raise smtp.SMTPBadSender(originAddress)
        return originAddress
    
    def validateTo(self, user):
        log.msg("validateTo: %s" % user)
        destDomain = user.dest.domain.lower()
        destUser = user.dest.local.lower()
        origDomain = user.orig.domain.lower()
        origUser = user.orig.local.lower()
        localDomains = self.validDomains.keys()
        localUsersOrig = self.validDomains.get(origDomain)
        localUsersDest = self.validDomains.get(destDomain)
        if not destDomain in localDomains:
            # get all local users
            localUsers = ([x.initial for x in localUsersOrig] +
                          [x.dest for x in localUsersOrig])
            if (origDomain in localDomains and origUser in localUsers):
                # startMessage returns 
                # createNewMessage returns (headerFile, FileMessage)
                d = self.domainQueuer
                msg = lambda: d.startMessage(user)
                d.exists = lambda: msg
                dest = "%s@%s" % (destUser, destDomain)
                if dest not in localUsers:
                    self.updateWhitelist(dest)
                return defer.maybeDeferred(d.exists)
            # Not a local user. raising SMTPBadRcpt...
            raise smtp.SMTPBadRcpt(user)
        for userType in localUsersDest:
            # set 'nospam-' and 'spam-' prefixes to user names as valid
            # recipients
            name = userType.initial
            # with dspam
            #if userType.validate(destUser, prefixes=VALID_DSPAM_PREFIX):
            if userType.validate(destUser):
                ## no DSPAM
                ##if destUser != name:
                ##    userType.dest = "%s@%s" % (destUser, destDomain)
                ##    log.msg("Setting DSPAM username as:")
                log.msg("Accepting mail for %s..." % user.dest)
                if isinstance(userType, Alias):
                    finalDest = userType.dest
                elif isinstance(userType, Actual):
                    finalDest = user.dest
                elif isinstance(userType, Maillist):
                    addressDirs = [self._getAddressDir(x)
                                   for x in userType.dest]
                    log.msg("Looks like destination is a mail list...")
                    log.msg("list addresses: %s" % addressDirs)
                    return lambda: MaildirListMessageWriter(
                        addressDirs, self.dspamEnabled)
                elif isinstance(userType, CatchAll):
                    finalDest = userType.dest
                else:
                    log.err(userType)
                
                if not isinstance(userType, Script):
                    return lambda: MaildirMessageWriter(
                        self._getAddressDir(finalDest), self.dspamEnabled)
                else:
                    return lambda: ScriptMessageWriter(
                        user.dest, userType.func)
        raise smtp.SMTPBadRcpt(user.dest)

    def _getAddressDir(self, address):
        return os.path.join(self.baseDir, "%s" % address)
    
class SMTPFactory(protocol.ServerFactory):

    def __init__(self, baseDir, configDir, validDomains, domainQueuer):
        self.baseDir = baseDir
        self.whitelistFile = os.path.join(configDir, 'whitelist.txt')
        self.blacklist = open(os.path.join(configDir, 'blacklist.txt')).readlines()
        self.whitelist = self._getWhitelistFromFile()
        self.whitelistQueue = []
        self.validDomains = validDomains
        self.domainQueuer = domainQueuer
        self.configDir = None
        self.dspamEnabled = False
        self.whitelistPurgeTimer = TimerService(300, self.purgeWhitelistQueue)

    def getDelivery(self):
        ld = LocalDelivery(
            self.baseDir, self.validDomains, self.domainQueuer,
            self.dspamEnabled)
        ld.blacklist = self.blacklist
        ld.whitelist = self.whitelist
        ld.whitelistQueue = self.whitelistQueue
        return ld

    def buildProtocol(self, addr):
        delivery = self.getDelivery()
        smtpProtocol = smtp.SMTP(delivery)
        smtpProtocol.factory = self
        return smtpProtocol

    def _getWhitelistFromFile(self):
        wl = open(self.whitelistFile).readlines()
        return list(set(wl))

    def purgeWhitelistQueue(self):
        # XXX there's a race condition between this and the local delivery
        # instantiation updating the whitelist attribute
        log.msg("Entries in whitelist: %s" % len(self.whitelist))
        log.msg("Entries in whitelist queue: %s" % len(self.whitelistQueue))
        wl = self._getWhitelistFromFile()
        uniq = list(set(self.whitelistQueue + wl))
        #fh = open(self.whitelistFile, 'w+')
        #fh.write('\n'.join(uniq))
        #fh.close()
        self.whitelistQueue = []
        self.whitelist = self._getWhitelistFromFile()
        log.msg("Entries in whitelist (updated): %s" % len(self.whitelist))
