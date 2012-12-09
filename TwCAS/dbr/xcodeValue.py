# -*- coding: utf-8 -*-

from defs import DBF
from info import dbf_element_size

__all__ = ['valueEncode','valueDecode']

import array
try:
    import numpy as np
except ImportError:
    np = None

if np:
    _wire_dtype = {
        DBF.STRING: np.dtype('S40'),
        DBF.CHAR: np.int8,
        DBF.SHORT: np.dtype('>i2'),
        DBF.ENUM: np.dtype('>i2'),
        DBF.LONG: np.dtype('>i4'),
        DBF.FLOAT:np.dtype('>f4'),
        DBF.DOUBLE:np.dtype('>f8'),
    }
    _host_dtype = {
        DBF.STRING: np.dtype('S40'),
        DBF.CHAR: np.int8,
        DBF.SHORT: np.int16,
        DBF.ENUM: np.int16,
        DBF.LONG: np.int32,
        DBF.FLOAT:np.float32,
        DBF.DOUBLE:np.float64,
    }

_arr_type = {
    DBF.STRING: None,
    DBF.CHAR: 'b',
    DBF.SHORT: 'h',
    DBF.ENUM: 'h',
    DBF.LONG: 'i',
    DBF.FLOAT:'f',
    DBF.DOUBLE:'d',
}

import sys
_swap = sys.byteorder!='big'

def _ca_str(inp):
    if len(inp)>40:
        return inp[:40]
    else:
        padlen = (40 - len(inp)%40)%40
        return inp + '\0'*padlen

def valueEncode(dbf, val):
    if isinstance(val, list):
        if np:
            val = np.asarray(val, dtype=_wire_dtype[dbf])
        elif dbf!=DBF.STRING:
            val = array.array(_arr_type[dbf], val)
        else:
            # special handling for list of strings
            # since array can't represent this.
            val = map(_ca_str, val)
            val = ''.join(val)
            return val

    if isinstance(val, array.ArrayType):
        if _swap:
            # Avoid clobbering the original
            val = array.array(val.typecode, val)
            val.byteswap()
        val = val.tostring()

    elif np and isinstance(val, np.ndarray):
        val = np.asarray(val, dtype=_wire_dtype[dbf])
        val = val.tostring()

    else:
        raise ValueError("Can't encode objects of type %s"%type(val))

    return val

def valueDecode(dbf, data, dcount, forcearray=False):
    dbytes = dbf_element_size(dbf) * dcount
    data = buffer(data, 0, dbytes)

    if np and not forcearray:
        val = np.frombuffer(data, dtype=_wire_dtype[dbf])
        val = np.asarray(val, dtype=_host_dtype[dbf])

    elif dbf==DBF.STRING:
        out = []
        while len(data):
            D = data[:40]
            D = D.rstrip('\0') if D[0]!='\0' else ''
            out.append(D)
            data = buffer(data, 40)
        val = out

    else:
        val = array.array(_arr_type[dbf])
        val.fromstring(data[:])
        if _swap:
            val.byteswap()

    return val
