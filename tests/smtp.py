import nose
from nose import with_setup

from smtplib import SMTP
from poplib import POP3
from imaplib import IMAP4

HOST = "127.0.0.1"
SMTP_PORT = 2525
POP3_PORT = 2110
IMAP4_PORT = 2143

def cleanup(username, password):
    pop = POP3(HOST, POP3_PORT)
    pop.user(username)
    pop.pass_(password)
    (message_count, mailbox_size) = pop.stat()
    (response, messages, size) = pop.list()
    for msg in messages:
        num, size = msg.split(" ")
        pop.dele(num)
    pop.quit()

def setup_cleanup():
    cleanup("bob@sample.org", "4n0th4s3kr1t")
    cleanup("post@sample.org", "post")

@with_setup(setup_cleanup)
def test_pop():
    """
    Sending one and reading one message
    """
    message = "Hello, I'm POP!"
    smtp = SMTP(HOST, SMTP_PORT)
    smtp.sendmail("alice@sample.org", "bob@sample.org", message)
    smtp.quit()

    pop = POP3(HOST, POP3_PORT)
    pop.user("bob@sample.org")
    pop.pass_("4n0th4s3kr1t")
    (message_count, mailbox_size) = pop.stat()
    assert message_count == 1, "one message"
    (response, messages, size) = pop.list()
    (num, size) = messages[0].split(" ")
    (response, lines, size) = pop.retr(num)
    pop.dele(num)
    assert lines[-1] == message, "body is %s" % message
    pop.quit()

@with_setup(setup_cleanup)
def test_imap():
    """
    Sending one and reading one message
    """
    message = "Hello, I'm IMAP!"
    smtp = SMTP(HOST, SMTP_PORT)
    smtp.sendmail("alice@sample.org", "bob@sample.org", message)
    smtp.quit()

    imap = IMAP4(HOST, IMAP4_PORT)
    imap.login("bob@sample.org", "4n0th4s3kr1t")
    (response, inboxes) = imap.list(".")
    (_a, dir, name) = inboxes[0].split(" ")
    name = name[1:-1] # remove the quotes
    assert name == "INBOX", "can haz Inbox"
    (response, size) = imap.select()
    (response, emails) = imap.search(None, "ALL")
    (response, emails) = imap.fetch("1", '(UID BODY[TEXT])')
    (metadata, email) = emails[0]
    assert message in email, "same text"
    #assert email == message, "should work"
    imap.logout()

@with_setup(setup_cleanup)
def test_catchall():
    message = "Hello catchall!"
    smtp = SMTP(HOST, SMTP_PORT)
    smtp.sendmail("bob@sample.org", "post@sample.org", message)
    smtp.sendmail("bob@sample.org", "post-1000@sample.org", message)
    smtp.sendmail("bob@sample.org", "post+hello@sample.org", message)
    smtp.quit()

    pop = POP3(HOST, POP3_PORT)
    pop.user("post@sample.org")
    pop.pass_("post")
    (message_count, mailbox_size) = pop.stat()
    assert message_count == 3, "three messages"
    (response, messages, size) = pop.list()
    for msg in messages:
        (num, size) = msg.split(" ")
        (response, lines, size) = pop.retr(num)
        pop.dele(num)
        assert lines[-1] == message, "body is %s" % message
    pop.quit()


if __name__ == "__main__":
    nose.main()
