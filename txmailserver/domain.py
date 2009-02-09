class AddressType(object):
    pass

class Actual(AddressType):

    def __init__(self, userName):
        self.initial = userName.lower()
        self.dest = userName.lower()

class Alias(AddressType):

    def __init__(self, userName, dest):
        self.initial = userName.lower()
        self.dest = dest.lower()

class Maillist(AddressType):

    def __init__(self, mailListName, recipients):
        if not isinstance(recipients, list):
            raise Exception, "Maillist recipients must be of type list!"
        self.initial = mailListName.lower()
        self.dest = recipients

class CatchAll(AddressType):
    
    def __init__(self, catchName, dest):
        self.initial = catchName.lower()
        self.dest = dest
