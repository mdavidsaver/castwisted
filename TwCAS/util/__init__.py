
import re

__all__ = ['splitPVName','InvalidPVNameError']

_recpat = re.compile('^([^.]+) (?: \. ([a-zA-Z_]+) (.*))?$', re.X)

class InvalidPVNameError(RuntimeError):
    pvname = None

def splitPVName(s):
    """Take a PV name string an seperate it into (Rec,Field,Options)
    
    Follows the algorithm used by the IOC (see dbNameToAddr in dbAccess.c).
    
    Returns three strings ("recordname", "FIELD", "?options")
    
    The '.' seperating the record and field is not included.
    However, and the options string includes all charactors
    after the field name.
    
    The record name will always be a non-empty string.
    The other two may be empty strings.
    However, if field name is empty, then options will also be empty.
    """
    M = _recpat.match(s)
    if not M:
        E = InvalidPVNameError("Invalid pattern")
        E.pvname =s
        raise E

    rec, fld, opt = M.groups()
    if not fld and opt:
        E = InvalidPVNameError("Invalid pattern contains options with no field")
        E.pvname =s
        raise E

    return (rec, fld or '', opt or '')

