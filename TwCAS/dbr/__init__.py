# -*- coding: utf-8 -*-

__all__ = ['dbf_element_size',
           'dbr_info',
           'dbr_size',
           'dbr_count',
           'DBF', 'DBR', 'DBE',
           'metaEncode','metaDecode',
           'valueEncode','valueDecode',
           'castDBR','valueMake',
           'DBRMeta',
           'DBR2Py',
           ]

from defs import DBF, DBR, DBE, DBRMeta
from xcodeMeta import metaDecode, metaEncode
from xcodeValue import valueDecode, valueEncode, valueMake
from convert import castDBR
from info import dbf_element_size, dbr_info, dbr_size, dbr_count

def DBR2Py(dtype, dcount, dbrdata, meta=None,
           dbf=None, forcearray=None):
    """Process raw DBR data (from a put request)
    
    Returns (value, meta)
    
    If the 'meta' argument is given, then that object
    is modified and returned.
    """
    srcdbf, metaLen = dbr_info(dtype)
    if dbf is None:
        dbf = srcdbf
    if meta is None:
        meta = DBRMeta(udf=None)

    val = valueDecode(srcdbf, dbrdata[metaLen:], dcount,
                          forcearray=forcearray)

    if metaLen>0:
        metaDecode(dtype, dbrdata[:metaLen], meta)

    return castDBR(dbf, srcdbf, val, meta)
