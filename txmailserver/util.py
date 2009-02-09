import logging
from subprocess import Popen, PIPE
from twisted.python import log


VALID_DSPAM_PREFIX = ['train-spam-', 'nospam-', 'spam-']


def runDspam(user, data):
    cmds = []
    log.msg("runDspam got user value of " + user)
    if user.startswith('train-spam-'):
        user = user.strip('train-spam-')
        cmd = "dspam --deliver=spam --source=corpus --class=spam --mode=tum".split()
        cmd.extend(["--user", user])
        msg = "The following message was trained as spam:"
    elif user.startswith('nospam-'):
        # correct dspam
        user = user.strip('nospam-')
        cmd = "dspam --deliver=innocent --source=error --class=innocent --mode=tum".split()
        cmd.extend(["--user", user])
        msg = "The following message was force-categorized as ham:"
    elif user.startswith('spam-'):
        # force message to be treated as spam
        user = user.strip('spam-')
        cmd = "dspam --deliver=spam --source=error --class=spam --mode=tum".split()
        cmd.extend(["--user", user])
        user = user.split('@')[0]
        cmd.append(user)
        msg = "The following message was force-categorized as spam:"
    else:
        cmd = "dspam --deliver=innocent --mode=tum --stdout".split()
        cmd.extend(["--user", user])
        msg = "The following message was not recognized as spam:"
    try:
        log.msg("DSPAM command: %s" % ' '.join(cmd))
        dspam = Popen(cmd, stdout=PIPE, stdin=PIPE)
        output, error = dspam.communicate(input=data)
    except Exception, e:
        # not sure what exceptions are going to be thrown here...
        error = str(e)
    if error:
        log.error("There was a DSPAM error: %s" % error)
    if output:
        log.msg(msg)
        log.msg(output)
    else:
        log.msg("dspam produced no message...")
    return output
