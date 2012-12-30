# -*- coding: utf-8 -*-
"""A place for leave factory instances where the
twisted plugin search will find them
"""

from TwCAS.application import DumbFactory, MailboxFactory, SelfFactory

from TwCAS.util import pvs, service

spamfactory = DumbFactory('Spam', pvs.Spam)
cifactory = DumbFactory('ClientInfo', pvs.ClientInfo)
mutexfactory = DumbFactory('Mutex', pvs.Mutex)

mailboxfactory=MailboxFactory()

servicefactory = SelfFactory('Service', service.ServicePV)
