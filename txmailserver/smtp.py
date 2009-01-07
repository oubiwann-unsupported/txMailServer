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

from txmailserver.util import runDspam
from txmailserver.domain import Alias, Actual, Maillist

def processMessageData(user, data):
    print "processMessageData got user value of " + user
    #if USE_DSPAM:
    #if 'dorthuan' in user:
    #    data = runDspam(user, data)
    return data

class MaildirMessageWriter(object):
    implements(smtp.IMessage)

    def __init__(self, userDir):
        self.user = os.path.split(userDir)[-1]
        if not os.path.exists(userDir):
            os.mkdir(userDir)
        inboxDir = os.path.join(userDir, 'Inbox')
        self.mailbox = maildir.MaildirMailbox(inboxDir)
        self.lines = []
    
    def lineReceived(self, line):
        self.lines.append(line)

    def eomReceived(self):
        # message is complete, store it
        print "Message data complete."
        self.lines.append('') # add a trailing newline
        messageData = processMessageData(self.user, '\n'.join(self.lines))
        return self.mailbox.appendMessage(messageData)

    def connectionLost(self):
        print "Connection lost unexpectedly!"
        # unexpected loss of connection; don't save
        del(self.lines)

class MaildirListMessageWriter(MaildirMessageWriter):

    def __init__(self, userDirList):
        self.mailboxes = {}
        self.lines = {}
        self.dspamUsers = {}
        for userDir in userDirList:
            if not os.path.exists(userDir):
                os.mkdir(userDir)
            inboxDir = os.path.join(userDir, 'Inbox')
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
            print "Message data complete for %s." % key
            user = os.path.split(key)[-1]
            messageData = processMessageData(user, '\n'.join(self.lines[key]))
            dl.append(self.mailboxes[key].appendMessage(messageData))
        return defer.DeferredList(dl)

class LocalDelivery(object):
    implements(smtp.IMessageDelivery)

    def __init__(self, baseDir, validDomains, domainQueuer):
        if not os.path.isdir(baseDir):
            raise ValueError, "'%s' is not a directory" % baseDir
        self.baseDir = baseDir
        self.validDomains = validDomains
        self.domainQueuer = domainQueuer
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
        print "validateFrom():"
        print originAddress
        if originAddress in self.whitelist + self.whitelistQueue:
            return originAddress
        elif originAddress in self.blacklist:
            print "Sender in blacklist! Denying message..."
            raise smtp.SMTPBadSender(originAddress)
        return originAddress
    
    def validateTo(self, user):
        destDomain = user.dest.domain.lower()
        destUser = user.dest.local.lower()
        origDomain = user.orig.domain.lower()
        origUser = user.orig.local.lower()
        localDomains = self.validDomains.keys()
        localUsersOrig = self.validDomains.get(origDomain)
        localUsersDest = self.validDomains.get(destDomain)
        print "in validateTo()..."
        print type(localUsersOrig)
        print localUsersOrig
        print type(localUsersDest)
        print localUsersDest
        #print "Dest: %s, %s" % (destDomain, destUser)
        #print "Orig: %s, %s" % (origDomain, origUser)
        #print "Local domains: %s" % str(localDomains)
        if not destDomain in localDomains:
            # get all local users
            localUsers = [x.initial for x in localUsersOrig] + [x.dest for x in localUsersOrig]
            #print "Variable 'localUsers':"
            #print localUsers
            if (origDomain in localDomains and origUser in localUsers):
                # startMessage returns 
                # createNewMessage returns (headerFile, FileMessage)
                d = self.domainQueuer
                msg = lambda: d.startMessage(user)
                #msg.__call__ = 
                d.exists = lambda: msg
                dest = "%s@%s" % (destUser, destDomain)
                if dest not in localUsers:
                    self.updateWhitelist(dest)
                return defer.maybeDeferred(d.exists)
            # Not a local user. raising SMTPBadRcpt...
            raise smtp.SMTPBadRcpt(user)
        for userType in localUsersDest:
            # set 'nospam-' and 'spam-' prefixes to user names as valid recipients
            name = userType.initial
            prefixes = [ x+name for x in VALID_DSPAM_PREFIX ]
            if destUser in [name] + prefixes:
                if destUser != name:
                    userType.dest = "%s@%s" % (destUser, destDomain)
                    print "Setting DSPAM username as:"
                print "Accepting mail for %s..." % user.dest
                if isinstance(userType, Alias):
                    finalDest = userType.dest
                elif isinstance(userType, Actual):
                    finalDest = str(user.dest)
                elif isinstance(userType, Maillist):
                    addressDirs = [ self._getAddressDir(x) for x in userType.dest ]
                    print "Looks like destination is a mail list..."
                    print "list addresses:"
                    print addressDirs
                    return lambda: MaildirListMessageWriter(addressDirs)
                return lambda: MaildirMessageWriter(
                    self._getAddressDir(finalDest))
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
        self.whitelistPurgeTimer = TimerService(300, self.purgeWhitelistQueue)

    def getDelivery(self):
        ld = LocalDelivery(self.baseDir, self.validDomains, self.domainQueuer)
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
        print "Entries in whitelist: %s" % len(self.whitelist)
        print "Entries in whitelist queue: %s" % len(self.whitelistQueue)
        wl = self._getWhitelistFromFile()
        uniq = list(set(self.whitelistQueue + wl))
        #fh = open(self.whitelistFile, 'w+')
        #fh.write('\n'.join(uniq))
        #fh.close()
        self.whitelistQueue = []
        self.whitelist = self._getWhitelistFromFile()
        print "Entries in whitelist (updated): %s" % len(self.whitelist)
