import os

from zope.interface import implements

from twisted.mail import imap4, maildir
from twisted.internet import protocol, defer
from twisted.python import log


class Account:
    implements(imap4.IAccount)
    
    def __init__(self, userdir):
        self.userdir = userdir
        self.mailboxes = {
            "INBOX": UserInbox(userdir)
            }
    
    def addMailbox(self, name, mbox=None):
        """ Add a new mailbox to this account 
        name:str
        mbox:IMailbox
        """
        raise "Not implemented"
        return False

    def create(self, pathspec):
        """ Create a new mailbox from the given hierarchical name. 
        pathspec:str
        """
        raise "Not implemented"
        return False

    def select(self, name, rw=True):
        """ Acquire a mailbox, given its name. 
        name:str
        rw:bool
        """
        if not rw:
            raise "Not implemented"
        log.msg("Select %s (%s)" % (name, rw))
        if name in self.mailboxes:
            return self.mailboxes[name]
        else:
            None

    def delete(self, name):
        """ Delete the mailbox with the specified name.
        name:str
        """
        raise "Not implemented"
        return False

    def rename(self, oldname, newname):
        """ Rename a mailbox
        oldname:str
        newname:str
        """
        raise "Not implemented"
        return False

    def isSubscribed(self, name):
        """ Check the subscription status of a mailbox
        name:str
        """
        raise "Not implemented"
        return False

    def subscribe(self, name):
        """ Subscribe to a mailbox
        name:str
        """
        raise "Not implemented"
        return False

    def unsubscribe(self, name):
        """ Unsubscribe from a mailbox
        name:str
        """
        raise "Not implemented"
        return False

    def listMailboxes(self, ref, wildcard):
        """ List all the mailboxes that meet a certain criteria 
        ref:str
        wildcard:str
        """
        return [(name, mailbox) for name, mailbox in self.mailboxes.iteritems()]

class UserInbox(maildir.MaildirMailbox):
    implements(imap4.IMailbox)
    UID = 0
    """
    maildir.MaildirMailbox already implements the imap4.IMailbox
    interface, so methods will only need to be defined to
    override the default behavior. For non-maildir mailboxes,
    you'd have to implement all of imap4.IAccount 
    """
    def __init__(self, userdir):
        inboxDir = os.path.join(userdir, 'Inbox')
        log.msg("Expecting maildir to be %s" % inboxDir)
        maildir.MaildirMailbox.__init__(self, inboxDir)
        self.flags = []
        UserInbox.UID += 1
        self.uid = UserInbox.UID
        self.listeners = []
    
    # IMailboxInfo
    def getFlags(self):
        """ Return the flags defined in this mailbox """
        return self.flags

    def getHierarchicalDelimiter(self):
        """ Get the character which delimits namespaces for in this mailbox. """
        return "."

    # IMailbox
    def getUIDValidity(self):
        """ Return the unique validity identifier for this mailbox. """
        return self.uid

    def getUIDNext(self):
        """ Return the likely UID for the next message added to this mailbox. """
        raise "Not implemented"
        return 0

    def getUID(self, message):
        """ Return the UID of a message in the mailbox """
        raise "Not implemented"
        return 0
    
    def getMessageCount(self):
        """ Return the number of messages in this mailbox. """
        return len(self.listMessages())
    
    def getRecentCount(self):
        """ Return the number of messages with the 'Recent' flag. """
        return self.getMessageCount()
    
    def getUnseenCount(self):
        """ Return the number of messages with the 'Unseen' flag. """
        return self.getMessageCount()

    def isWriteable(self):
        """ Get the read/write status of the mailbox. """
        return True
    
    def destroy(self):
        """ Called before this mailbox is deleted, permanently."""
        raise "Not implemented"
        return False

    def requestStatus(self, names):
        """ Return status information about this mailbox.
        names:iterable containing MESSAGES, RECENT, UIDNEXT, UIDVALIDITY, UNSEEN
        """
        values = {}
        for name in names:
            value = None
            if name is "MESSAGES":
                value = self.getMessageCount()
            elif name is "RECENT":
                value = self.getRecentCount()
            elif name is "UIDNEXT":
                value = self.getUIDNext()
            elif name is "UIDVALIDITY":
                value = self.getUIDValidity()
            elif name is "UNSEEN":
                value = self.getUnseenCount()
            values[name] = value

    def addListener(self, listener):
        """ Add a mailbox change listener.
        listener:IMailboxListener
        """
        self.listeners.append(listener)
    
    def removeListener(self, listener):
        """ Remove a mailbox change listener.
        listener:IMailboxListener
        """
        self.listeners.remove(listener)
    
    def getMessage(self, id):
        log.msg("getMessage: %s" % id)
        id = id-1
        message = maildir.MaildirMailbox.getMessage(self, id)
        uid = self.getUidl(id)
        return Message(uid, message)

    def addMessage(self, message, flags=(), date=None):
        """ Add the given message to this mailbox.
        message:RFC822 message
        flags:iter or str
        date:str
        """
        raise "Not Implemented"

    def expunge(self):
        """ Remove all messages flagged \Deleted.  """
        raise "Not Implemented"

    def fetch(self, messages, uid):
        """ Retrieve one or more message.
        messages:MessageSet
        uid:bool
        """
        msgs = []
        if not messages.last:
            log.msg("Setting last message to 100")
            messages.last = 100

        for message in messages:
            try:
                msg = self.getMessage(message)
                log.msg(msg)
                msgs.append((msg.getUID(), msg))
            except Exception, e:
                log.err(e)
                break
        
        log.msg(msgs)
        return msgs or None

    def store(self, messages, mode, uid):
        """ Set the flags of one or more messages .
        messages:MessageSet
        flags:sequence of str
        mode:int(-1,0,1)
        uid:bool
        """
        raise "Not Implemented"

class Message:
    implements(imap4.IMessage)
    UID = 0
    def __init__(self, id, message):
        self.message = message
        self.id = id
        Message.UID += 1
        self.uid = Message.UID
        self.flags = ()
    
    def getHeaders(self, negate, *names):
        raise "Not implemented"

    def getBodyFile(self):
        return self.message

    def getSize(self):
        raise "Not implemented"
        return 0

    def isMultipart(self):
        raise "Not implemented"
        return False

    def getSubPart(self, part):
        """ Retrieve a MIME sub-message 
        part:int
        """
        raise "Not implemented"

    def getUID(self):
        return self.uid
        
    def getFlags(self):
        return self.flags

    def getInternalDate(self):
        return "1970-01-01 00:00:00"


class IMAP4Protocol(imap4.IMAP4Server):
    debug = True
    
    def sendLine(self, line):
        if self.debug: log.msg("IMAP4 SERVER:", line)
        imap4.IMAP4Server.sendLine(self, line)

    def lineReceived(self, line):
        if self.debug: log.msg("IMAP4 CLIENT:", line)
        imap4.IMAP4Server.lineReceived(self, line)

class IMAP4Factory(protocol.Factory):
    protocol = IMAP4Protocol
    portal = None
    
    def buildProtocol(self, address):
        p = self.protocol()
        p.portal = self.portal
        p.factory = self
        return p

