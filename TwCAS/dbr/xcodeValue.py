# -*- coding: utf-8 -*-

from defs import DBF
from info import dbf_element_size

__all__ = ['valueMake','valueEncode','valueDecode']

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

def getArrayType(dbf):
    if dbf==DBF.STRING:
        return None
    else:
        try:
            return _arr_type[dbf]
        except KeyError: # default to byte array
            return 'b'

if np:
    def getDType(dbf, net=False):
        D = _wire_dtype if net else _host_dtype
        try:
            return D[dbf]
        except KeyError: # default to byte array
            return np.int8

import sys
_swap = sys.byteorder!='big'

def _ca_str(inp):
    if len(inp)>40:
        return inp[:40]
    else:
        padlen = (40 - len(inp)%40)
        return inp + '\0'*padlen

def valueMake(dbf, val, usearray=None):
    """Normalize input as an encodable value.
    """
    if isinstance(val, array.ArrayType):
        return val
    elif np and isinstance(val, np.ndarray):
        return val
    elif isinstance(val, list):
        if np and usearray is not True:
            return np.asarray(val, dtype=_host_dtype[dbf])
        elif not np and usearray is False:
            raise RuntimeError("numpy required, but not present")
        elif dbf!=DBF.STRING:
            return array.array(_arr_type[dbf], val)
        else:
            # special handling needed later for list of strings
            return val
    else:
        # Silently turn scalars into array of length 1
        return array.array(_arr_type[dbf], [val])

def valueEncode(dbf, val):
    if dbf==DBF.STRING and isinstance(val, list):
        # special handling for list of strings
        # since array can't represent this.
        val = map(_ca_str, val)
        val = ''.join(val)
        return val

    elif isinstance(val, array.ArrayType):
        if _swap:
            # Avoid clobbering the original
            val = array.array(val.typecode, val)
            val.byteswap()
        val = val.tostring()

    elif np and isinstance(val, np.ndarray):
        val = np.asarray(val, dtype=_wire_dtype[dbf])
        val = val.tostring()

    else:
        raise ValueError("Can't encode objects of type %s like '%s'"%(type(val),val))

    return val

def valueDecode(dbf, data, dcount, forcearray=False):
    dbytes = dbf_element_size(dbf) * dcount
    if len(data)<dbytes:
        # CA servers can skip sending trailing nils,
        # but we need them for proper decoding
        pad = (dbytes-len(data))*'\0'
        data += pad
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
