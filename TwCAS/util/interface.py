# -*- coding: utf-8 -*-

from zope.interface import Interface, Attribute

class IMailbox(Interface):
    """The public interface of a MailboxPV
    """
    validator = Attribute("Reference to an IMailboxValidator")

    value = Attribute("The value.  An ndarray, array, or list of strings")

    severity = Attribute("The alarm severity.  A number [0-3]")
    status = Attribute("The alarm status.  A number [0-25]")

    timestamp = Attribute("""Time of last value change as a
        Float""")

class IMailboxValidator(Interface):
    nativeDBF = Attribute("""DBF type reported to clients.
        Used only when the getInfo method is not provided
        and the setup() method does not initialize the value""")

    maxCount = Attribute("""The max array size accepted from clients.
        Used only when the getInfo method is not provided""")

    rights = Attribute("""The client access rights.
        Used only when the getInfo method is not provided""")

    longStringSize = Attribute("""maxCount used when a string
        is being requested as a charactor array""")

    putDBF = Attribute("""DBF type new which new put data is
        converted before being passed to this PV.  Set to None
        to disable automatic conversion.""")

    usearray = Attribute("""Controls which container is used
        to pass data with put requests.  If True then data
        will always by an array (from the array module).
        If False then data will be a numpy ndarray.
        If None then numpy is preferred with array
        as a fallback.
        
        Note: As the array module can't represent an array
              of string, this is passed as a list.""")

    putQueueLen = Attribute("""Number of put requests to buffer.
        before dropping.  A value of 0 will not drop any.
        """)

    pv = Attribute("Reference to the IMailbox which is being supported")

    def __init__(self, config, section):
        """A ConfigParser object
        """

    def setup():
        """Called once before any other method except __init__
        
        The pv attribute will be set when this call is made.
        
        This method may return (dbf, value, meta) to set the initial
        value, or None to use a default.
        """

    def shutdown():
        """Called once.  No other method (except __del__)
        will be called after this.
        """

    def getInfo(request):
        """See IDBRPV.getInfo
        
        If not provided then 
        """

    def put((dbf, value, meta), reply=None, chan=None):
        """A client is sending new data.
        
        This function should return either a tuple (dbf, value, meta),
        or a Deferred which will fire with such a tuple.
        If value has not be converted again then the result dbf
        can be None.
        
        dbf   - Originating field type.  If nativeDBR==None then
                this is the actual dtype.
        data  - an ndarray, array, or list of string.
        meta  - Any meta data sent be the client
        reply - If not None, an object which must used to
                acknowledge the completion of the put operation.
        chan  - The Channel from which this put originated, or
                None for local data.
        """

class IMailboxValidatorFactory(Interface):
    """Builds a MailboxValidator using configuration from ConfigParser
    """

    name = Attribute("The unique name this factory is known by")

    def build(config):
        """Build a new validator instance.
        
        config - dictionary of configuration parameters
        
        Returns a instance implementing IDBRPV
        """
