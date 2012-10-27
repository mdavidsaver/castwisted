# -*- coding: utf-8 -*-

__all__ = ['dbf_element_size',
           'dbr_info',
           'dbr_size',
           'dbr_count',
           'DBF', 'DBR',
           'metaEncode','metaDecode',
           ]

from defs import DBF, DBR
from xcode import metaDecode, metaEncode

_dbf_element_size={DBF.STRING:40,
                   DBF.SHORT :2,  # DBF_INT and DBF_SHORT
                   DBF.FLOAT :4,
                   DBF.ENUM  :2,
                   DBF.CHAR  :1,
                   DBF.LONG  :4,
                   DBF.DOUBLE:8
                  }
def dbf_element_size(dbf):
    """Return the element size in bytes of the given DBF type
    """
    return _dbf_element_size.get(dbf, 1)

_dbr_info = {
    # Plain DBR
    DBR.STRING: (DBF.STRING, 0),
    DBR.SHORT: (DBF.SHORT, 0),
    DBR.FLOAT: (DBF.FLOAT, 0),
    DBF.ENUM: (DBF.ENUM, 0),
    DBF.CHAR: (DBF.CHAR, 0),
    DBF.LONG: (DBF.LONG, 0),
    DBF.DOUBLE: (DBF.DOUBLE, 0),
    # DBR_STS
    DBR.STS_STRING: (DBF.STRING, 4),
    DBR.STS_SHORT: (DBF.SHORT, 4),
    DBR.STS_FLOAT: (DBF.FLOAT, 4),
    DBR.STS_ENUM: (DBF.ENUM, 4),
    DBR.STS_CHAR: (DBF.CHAR, 5),
    DBR.STS_LONG: (DBF.LONG, 4),
    DBR.STS_DOUBLE: (DBF.DOUBLE, 8),
    # DBR_TIME
    DBR.TIME_STRING: (DBF.STRING, 12),
    DBR.TIME_SHORT: (DBF.SHORT, 14),
    DBR.TIME_FLOAT: (DBF.FLOAT, 12),
    DBR.TIME_ENUM: (DBF.ENUM, 12),
    DBR.TIME_CHAR: (DBF.CHAR, 15),
    DBR.TIME_LONG: (DBF.LONG, 12),
    DBR.TIME_DOUBLE: (DBF.DOUBLE, 16),
    # DBR_GR
    DBR.GR_STRING: (DBF.STRING, 4), # same meta ad DBR_STS_STRING
    DBR.GR_SHORT: (DBF.SHORT, 24),
    DBR.GR_FLOAT: (DBF.FLOAT, 40),
    DBR.GR_ENUM: (DBF.ENUM, 422),
    DBR.GR_CHAR: (DBF.CHAR, 19),
    DBR.GR_LONG: (DBF.LONG, 36),
    DBR.GR_DOUBLE: (DBF.DOUBLE, 64),
    # DBR_CTRL
    DBR.CTRL_STRING: (DBF.STRING, 4), # same meta ad DBR_STS_STRING
    DBR.CTRL_SHORT: (DBF.SHORT, 28),
    DBR.CTRL_FLOAT: (DBF.FLOAT, 48),
    DBR.CTRL_ENUM: (DBF.ENUM, 422), # same as DBR_GR_ENUM
    DBR.CTRL_CHAR: (DBF.CHAR, 21),
    DBR.CTRL_LONG: (DBF.LONG, 44),
    DBR.CTRL_DOUBLE: (DBF.DOUBLE, 80),
    # Specials
    DBR.PUT_ACKT: (DBF.SHORT, 0), # PUT_ACKT
    DBR.PUT_ACKS: (DBF.SHORT, 0), # PUT_ACKS
    DBR.STSACK_STRING: (DBF.STRING, 8), # STSACK_STRING
    DBR.CLASS_NAME: (DBF.STRING, 0), # CLASS_NAME
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
