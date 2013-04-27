import os
import os.path
import stat
import email
import simplejson as json

from random import randint
from datetime import datetime
from StringIO import StringIO

from zope.interface import implements

from twisted.mail import imap4, maildir
from twisted.python import log


DELIMITER = "."
META = "meta.json"
FLAGS = {
    "SEEN": r"\Seen",
    "UNSEEN": r"\Unseen",
    "DELETED": r"Deleted",
    "FLAGGED": r"Flagged",
    "ANSWERED": r"\Answered",
    "RECENT": r"\Recent"
    }


class Mailbox(maildir.MaildirMailbox):
    """
    POP3 + IMAP4 mailbox, stores the IMAP4 metadatas into a JSON file.
    """
    implements(imap4.IMailbox)

    def __init__(self, path):
        maildir.MaildirMailbox.__init__(self, path)
        self.listeners = []
        self.meta_filename = os.path.join(self.path, META)
        
        if not os.path.exists(self.meta_filename):
            self.meta = {
                "flags": {},
                "uidvalidity": randint(0,2**32),
                "uids": {},
                "uidnext": 1,
                "subscribed": False
                }
        else:
            self.meta = json.loads(file(self.meta_filename, "r").read())
        self.initMeta()
    
    def saveMeta(self):
        json.dump(self.meta, file(self.meta_filename, "w"))
    
    def initMeta(self):
        for mail in self.list:
            filename = os.path.basename(mail)
            if filename not in self.meta["uids"]:
                uid = self.getUIDNext()
                self.meta["uids"][filename] = uid
                self.meta["flags"][filename] = []
        self.saveMeta()

    #POP3
    def deleteMessage(self, i):
        """ delete message """
        filename = os.path.basename(self.list[i])
        log.msg("deleting %s" % filename)
        maildir.MaildirMailbox.deleteMessage(self, i)
        
        del self.meta["uids"][filename]
        del self.meta["flags"][filename]
        self.saveMeta()

    # IMailboxInfo
    def getFlags(self):
        """ Return the flags defined in this mailbox """
        return FLAGS.values()

    def getHierarchicalDelimiter(self):
        """ Get the character which delimits namespaces for in this mailbox. """
        return DELIMITER

    # IMailbox
    def getUIDValidity(self):
        """ Return the unique validity identifier for this mailbox. """
        return self.meta["uidvalidity"]

    def getUIDNext(self):
        """ Return the likely UID for the next message added to this mailbox. """
        uidnext = self.meta["uidnext"]
        self.meta["uidnext"] += 1
        return uidnext

    def getUID(self, message):
        """ Return the UID of a message in the mailbox
        message:int message sequence number"""
        filename = os.path.basename(self.list[message - 1])
        if filename not in self.meta["uids"]:
            uid = self.getUIDNext()
            self.meta["uids"][filename] = uid
            self.saveMeta()
            return uid
        else:
            return self.meta["uids"][filename]
    
    def getFlagCount(self, flag):
        """ Return the number of message with the given flag """
        count = 0
        for message in self.list:
            filename = os.path.basename(message)
            flags = self.meta["flags"][filename]
            if flag in flags:
                count+=1

        self.saveMeta()
        return count

    def getMessageCount(self):
        """ Return the number of messages in this mailbox. """
        return len(self.list)
    
    def getRecentCount(self):
        """ Return the number of messages with the 'Recent' flag. """
        return self.getFlagCount(FLAGS["RECENT"])
    
    def getUnseenCount(self):
        """ Return the number of messages with the 'Unseen' flag. """
        return getMessageCount() - getFlagCount(FLAGS.SEEN)

    def isWriteable(self):
        """ Get the read/write status of the mailbox. """
        return True
    
    def destroy(self):
        """ Called before this mailbox is deleted, permanently."""
        raise imap4.MailboxException("Permission denied")
    
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
        return values

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
    
    def addMessage(self, message, flags=(), date=None):
        """ Add the given message to this mailbox.
        message:RFC822 message
        flags:iter or str
        date:str
        """
        return self.appendMessage(msg).addCallback(self.cbAddedMessage, flags)
    
    def cbAddedMessage(self, _something, flags):
        """ Callback """
        message = os.path.basename(self.list[-1])
        uid = self.getUIDNext()
        self.meta["uids"][message] = uid
        self.meta["flags"][uid] = flags
        self.saveMeta()
    
    def expunge(self):
        """ Remove all messages flagged \Deleted.  """
        for filename in self.list:
            uid = self.meta["uid"][os.path.basename(filename)]
            if FLAGS.DELETED in self.meta["flags"][uid]:
                pos = self.list.index(filename)
                os.remove(filename)
                del self.list[pos]
                yield uid

    def fetch(self, messages, uid):
        """ Retrieve one or more message.
        messages:MessageSet
        uid:bool
        """
        msgs = []
        if uid:
            if not messages.last:
                messages.last = self.meta["uidnext"]
            # reverse mapping (uid -> filename)
            filenames = dict((v, k) for k, v in self.meta["uids"].iteritems())
            for uid in messages:
                if message in filenames:
                    pos = self.meta["uids"].keys().index(uid)
                    filename = filenameself.list[pos]
                    msgs.append((uid, filename))
        else:
            if not messages.last:
                messages.last = max(0, len(self.list) - 1)
            
            for message in messages:
                uid = self.getUID(message)
                filename = self.list[message - 1]
                msgs.append((uid, filename))

        for uid, filename in msgs:
            flags = self.meta["flags"][os.path.basename(filename)]
            ctime = os.stat(filename)[stat.ST_CTIME]
            data = file(filename).read()
            date = datetime.fromtimestamp(ctime)
            yield uid, Message(uid, data, flags, date)
     
    def store(self, messages, flags, mode, uid):
        """ Set the flags of one or more messages .
        messages:MessageSet
        flags:sequence of str
        mode:int(-1,0,1)
        uid:bool
        """
        flags = {}
        for uid, message in self.fetch(messages, uid):
            # replace
            if mode == 0:
                self.meta["flags"][uid] = flags
                self.saveMeta()
                yield uid, flags
            else:
                old_flags = self.meta["flags"][uid]
                # remove
                if mode == 1:
                    new_flags = list(set(old_flags) - set(flags))
                else:
                    new_flags = list(set(old_flags) + set(flags))
                self.meta["flags"][uid] = new_flags
                self.saveMeta()
                yield uid, new_flags


class MessagePart(object):
    implements(imap4.IMessagePart)

    def __init__(self, message):
        self.message = message
        self.data = str(message)

    def getHeaders(self, negate, *names):
        """ Retrieve a group of messag headers.
        names:truple|str
        negate:bool omit the given names?
        """
        if not names:
            names = self.message.keys()

        if not negate:
            for name, header in self.message.keys():
                if name not in names:
                    yield header
        else:
            for name in names:
                yield self.message.get(name, None)

    def getBodyFile(self):
        """ Retrieve a file object containing only the body of this message. """
        return StringIO(self.email.get_payload())

    def getSize(self):
        """ Retrieve the total size, in octets/bytes, of this message. """
        return len(self.data)

    def isMultipart(self):
        """ Indicate whether this message has subparts. """
        return self.message.is_multipart()

    def getSubPart(part):
        """ Retrieve a MIME sub-message.
        part:int indexed from 0
        """
        return MaildirMessagePart(self.message.get_playload(part))


class Message(MessagePart):
    implements(imap4.IMessage)

    def __init__(self, uid, message, flags=None, date=None):
        super(Message, self).__init__(message)
        self.email = email.message_from_string(message)
        self.uid = uid
        self.flags = flags
        self.date = date
    
    def getUID(self):
        return self.uid

    def getFlags(self):
        return self.flags

    def getInternalDate(self):
        return self.date.strftime("%a, %d  %b  %Y  %H:%M:%S")
