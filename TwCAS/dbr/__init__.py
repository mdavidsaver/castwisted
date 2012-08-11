# -*- coding: utf-8 -*-

__all__ = ['dbf_element_size',
           'dbr_info',
           'dbr_size',
           'dbr_count']

_dbf_element_size={0:40,  # DBF_STRING
                   1 :2,  # DBF_INT and DBF_SHORT
                   2 :4,  # DBF_FLOAT
                   3 :2,  # DBF_ENUM
                   4 :1,  # DBF_CHAR
                   5 :4,  # DBF_LONG
                   6 :8   # DBF_DOUBLE
                  }
def dbf_element_size(dbf):
    """Return the element size in bytes of the given DBF type
    """
    return _dbf_element_size.get(dbf, 1)

_dbr_info = {
    # Plain DBR
    0: (0, 0),
    1: (1, 0),
    2: (2, 0),
    3: (3, 0),
    4: (4, 0),
    5: (5, 0),
    6: (6, 0),
    # DBR_STS
    7: (0, 4),
    8: (1, 4),
    9: (2, 4),
    10: (3, 4),
    11: (4, 5),
    12: (5, 4),
    13: (0, 8),
    # DBR_TIME
    14: (0, 12),
    15: (1, 14),
    16: (2, 12),
    17: (3, 12),
    18: (4, 15),
    19: (5, 12),
    20: (6, 16),
    # DBR_GR
    21: (0, 4), # same meta ad DBR_STS_STRING
    22: (1, 24),
    23: (2, 40),
    24: (3, 422),
    25: (4, 19),
    26: (5, 36),
    27: (6, 64),
    # DBR_CTRL
    28: (0, 4), # same meta ad DBR_STS_STRING
    29: (1, 28),
    30: (2, 48),
    31: (3, 422), # same as DBR_GR_ENUM
    32: (4, 21),
    33: (5, 44),
    34: (6, 80),
    # Specials
    35: (1, 0), # PUT_ACKT
    36: (1, 0), # PUT_ACKS
    37: (0, 8), # STSACK_STRING
    38: (0, 0), # CLASS_NAME
}
def dbr_info(dbr):
    """Returns a tuple (DBF, MetaLen)
    
    Gives the element
    """
    return _dbr_info.get(dbr, (-1, 0))

def dbr_size(dtype, dcount, pad=False):
    """Compute size of encoded DBR data
    """
    dbf, mlen = dbr_info(dtype)
    S = mlen + dcount * dbf_element_size(dbf)
    pad = (8-(S%8))&7 if pad else 0
    return S + pad

def dbr_count(dtype, dbrlen):
    """Find dcount from dbr type and a given buffer size.
    
    Assumes all padding has been removed.

    The following will always be true.
    
    dbr_size(dbr, dbr_info(dbr,len(buffer))) == len(buffer)
    
    dbr_info(dbr, dbr_count(dbr, len(buffer))) <= len(buffer)
    """
    dbf, mlen = dbr_info(dtype)
    dbrlen -= mlen
    return dbrlen/dbf_element_size(dbf)
