from subprocess import Popen, PIPE

VALID_DSPAM_PREFIX = ['train-spam-', 'nospam-', 'spam-']

def runDspam(user, data):
    cmds = []
    print "runDspam got user value of " + user
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
        print "DSPAM command:"
        print ' '.join(cmd)
        dspam = Popen(cmd, stdout=PIPE, stdin=PIPE)
        output, error = dspam.communicate(input=data)
    except Exception, e:
        # not sure what exceptions are going to be thrown here...
        error = str(e)
    if error:
        print "There was a DSPAM error: "
        print error
    if output:
        print msg
        print output
    else:
        print "dspam produced no message..."
    return output
