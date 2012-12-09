# -*- coding: utf-8 -*-
"""
DBR data conversions

Value conversions.

For numeric types, conversions follow (hopefully) C style casting.

For numeric to string, print.

For string to numeric, attempt to convert using appropriate int() or float()

For any to enum, treat as int

For enum to numeric, treat as int, to string use enums

For meta-data conversions

Since python types are used, the only conversions are

int -> float      Convert val meta
float -> int      Convert val meta
string -> float   Nothing
string -> int     Nothing
float -> string   Drop val meta
int -> string     Drop val meta

"""

from defs import DBRMeta, DBF
import xcodeValue

__all__ = ['castDBR']

class DBRNoConvert(ValueError):
    pass

_dbf_int = object()
_dbf_float = object()

_dbf_cls = {
    DBF.STRING:DBF.STRING,
    DBF.CHAR:_dbf_int,
    DBF.SHORT:_dbf_int,
    DBF.LONG:_dbf_int,
    DBF.FLOAT:_dbf_float,
    DBF.DOUBLE:_dbf_float,
    DBF.ENUM:_dbf_int,
}

_copy_metas = ['status','severity','timestamp',
               'units','ackt','acks']

_val_metas = ['upper_disp_limit','lower_disp_limit',
              'upper_alarm_limit','upper_warning_limit',
              'lower_warning_limit','lower_alarm_limit',
              'upper_ctrl_limit','lower_ctrl_limit']

def double2int(srcmeta):
    dstmeta = DBRMeta(udf=None)
    for F in _val_metas:
        setattr(dstmeta, F, int(getattr(srcmeta, F, 0)))
    for F in _copy_metas:
        try:
            setattr(dstmeta, F, getattr(srcmeta, F))
        except AttributeError:
            pass
    return dstmeta

def int2double(srcmeta):
    dstmeta = DBRMeta(udf=None)
    for F in _val_metas:
        setattr(dstmeta, F, float(getattr(srcmeta, F, 0)))
    for F in _copy_metas:
        try:
            setattr(dstmeta, F, getattr(srcmeta, F))
        except AttributeError:
            pass
    return dstmeta

def enum2int(srcmeta):
    dstmeta = DBRMeta(udf=None)
    for F in _copy_metas:
        try:
            setattr(dstmeta, F, getattr(srcmeta, F))
        except AttributeError:
            pass
    return dstmeta

_converts = {
    (_dbf_int, _dbf_float):int2double,
    (_dbf_float, _dbf_int):double2int,
    (DBF.ENUM, _dbf_int):enum2int,
}

def any2string(srcdbf, srcval, srcmeta):
    #TODO: Use precision for floats
    dstval = map(str, srcval)
    dstmeta = DBRMeta(udf=None)
    for F in _copy_metas:
        try:
            setattr(dstmeta, F, getattr(srcmeta, F))
        except AttributeError:
            pass
    return (dstval, dstmeta)

_fromstring = {
    DBF.CHAR:int,
    DBF.SHORT:int,
    DBF.LONG:int,
    DBF.ENUM:int, # not greay, but can't be handled here anyway
    DBF.FLOAT:float,
    DBF.DOUBLE:float,
}    

def string2any(dstdbf, srcval, srcmeta):
    conv = _fromstring[dstdbf]
    try:
        dstval = xcodeValue.valueMake(dstdbf,map(conv,srcval)) # TODO: numpy specialization
    except ValueError:
        raise DBRNoConvert("Can't convert '%s'"%srcval)
    dstmeta = DBRMeta(udf=None)
    for F in _copy_metas:
        try:
            setattr(dstmeta, F, getattr(srcmeta, F))
        except AttributeError:
            pass
    for F in _val_metas:
        try:
            setattr(dstmeta, F, conv(getattr(srcmeta, F)))
        except AttributeError:
            pass
        except ValueError:
            raise DBRNoConvert("Can't convert '%s'"%srcval)
    return (dstval, dstmeta)

def castDBR(dstdbf, srcdbf, srcval, srcmeta):
    """Convert value and meta-data
    
    Expects srcval to be either a python list,
    an array (as in array module), or a numpy ndarray.
    
    Returns a typle (dstval, dstmeta).
    
    dstval will be either an array or ndarry depending
    on the input.  Lists are always transformed into arrays.
    """
    if dstdbf==srcdbf:
        return (srcval, srcmeta)

    try:
        dcls, scls = _dbf_cls[dstdbf], _dbf_cls[srcdbf]
    except KeyError:
        raise DBRNoConvert("Conversion type not known for %s or %s",
                           dstdbf, srcdbf)

    if dcls==scls:
        return (srcval, srcmeta)

    elif dstdbf==DBF.STRING:
        return any2string(srcdbf, srcval, srcmeta)
        
    elif srcdbf==DBF.STRING:
        return string2any(dstdbf, srcval, srcmeta)

    if isinstance(srcval, xcodeValue.array.ArrayType):
        tc = xcodeValue.getArrayType(dstdbf)
        dstval = xcodeValue.array.array(tc, srcval)
    elif xcodeValue.np and isinstance(srcval, xcodeValue.np.ndarray):
        dtype = xcodeValue.getDType(dstdbf)
        dstval = xcodeValue.np.asarray(srcval, dtype=dtype)
    else:
        raise ValueError("No conversion know for %s",srcval)

    try:
        fn=_converts[(scls,dcls)]
    except KeyError:
        raise DBRNoConvert("No Conversion defined")

    return dstval, fn(srcmeta)
