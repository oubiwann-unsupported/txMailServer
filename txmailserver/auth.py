import os

from zope.interface import implements

from twisted.mail import maildir
from twisted.mail.pop3 import IMailbox
from twisted.mail.imap4 import IAccount
from twisted.cred import portal, checkers, credentials, error as credError
from twisted.internet import protocol, reactor, defer
from twisted.python import log

from txmailserver.pop3 import POP3Account
from txmailserver.imap4 import IMAP4Account

class MailUserRealm(object):
    implements(portal.IRealm)
    avatarInterfaces = {
        IMailbox: POP3Account,
        IAccount: IMAP4Account
        }

    def __init__(self, baseDir):
        self.baseDir = baseDir

    def requestAvatar(self, avatarId, mind, *interfaces):
        log.msg(interfaces)
        for requestedInterface in interfaces:
            if self.avatarInterfaces.has_key(requestedInterface):
                # make sure the user dir exists
                userDir = os.path.join(self.baseDir, avatarId)
                if not os.path.exists(userDir):
                    os.mkdir(userDir)
                # return an instance of the correct class
                avatarClass = self.avatarInterfaces[requestedInterface]
                avatar = avatarClass(userDir)
                # null logout function: take no arguments and do nothing
                logout = lambda: None
                return defer.succeed((requestedInterface, avatar, logout))
            
        # none of the requested interfaces was supported
        raise KeyError("None of the requested interfaces is supported") 

class CredentialsChecker(object):
    implements(checkers.ICredentialsChecker)
    credentialInterfaces = (credentials.IUsernamePassword,
                            credentials.IUsernameHashedPassword)

    def __init__(self, passwords):
        "passwords: a dict-like object mapping usernames to passwords"
        self.passwords = passwords

    def requestAvatarId(self, credentials):
        username = credentials.username
        if self.passwords.has_key(username):
            realPassword = self.passwords[username]
            checking = defer.maybeDeferred(
                credentials.checkPassword, realPassword)
            # pass result of checkPassword, and the username that was
            # being authenticated, to self._checkedPassword
            checking.addCallback(self._checkedPassword, username)
            return checking
        else:
            raise credError.UnauthorizedLogin("No such user")
            
    def _checkedPassword(self, matched, username):
        if matched:
            # password was correct
            return username
        else:
            raise credError.UnauthorizedLogin("Bad password")

def passwordFileToDict(filename):
    passwords = {}
    if os.path.exists(filename):
        for line in file(filename):
            if line and line.count(':'):
                username, password = line.strip().split(':')
                passwords[username.strip()] = password.strip()
    else:
        log.err("%s - passwords not found" % filename)
    return passwords

def getPasswords(configDir):
    return os.path.join(configDir, 'passwords.txt')

def getChecker(configDir):
    passwords = passwordFileToDict(passwordFile)
    checker = CredentialsChecker(passwords)
    return checker

