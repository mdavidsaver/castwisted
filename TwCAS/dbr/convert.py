# -*- coding: utf-8 -*-
"""
DBR data conversions
"""

from defs import DBRMeta, DBF

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
    DBF.ENUM:DBF.ENUM,
}

_copy_metas = ['status','severity','timestamp',
               'units','ackt','acks']

_val_metas = ['upper_disp_limit','lower_disp_limit',
              'upper_alarm_limit','upper_warning_limit',
              'lower_warning_limit','lower_alarm_limit',
              'upper_ctrl_limit','lower_ctrl_limit']

def double2int(srcval, srcmeta):
    dstval = map(int,srcval)
    dstmeta = DBRMeta()
    for F in _val_metas:
        setattr(dstmeta, F, int(getattr(srcmeta, F, 0)))
    for F in _copy_metas:
        try:
            setattr(dstmeta, F, getattr(srcmeta, F))
        except AttributeError:
            pass
    return (dstval, dstmeta)

def int2double(srcval, srcmeta):
    dstval = map(float,srcval)
    dstmeta = DBRMeta()
    for F in _val_metas:
        setattr(dstmeta, F, float(getattr(srcmeta, F, 0)))
    for F in _copy_metas:
        try:
            setattr(dstmeta, F, getattr(srcmeta, F))
        except AttributeError:
            pass
    return (dstval, dstmeta)

def enum2int(srcval, srcmeta):
    dstval = srcval
    dstmeta = DBRMeta()
    for F in _copy_metas:
        try:
            setattr(dstmeta, F, getattr(srcmeta, F))
        except AttributeError:
            pass
    return (dstval, dstmeta)

_converts = {
    (_dbf_int, _dbf_float):int2double,
    (_dbf_float, _dbf_int):double2int,
    (DBF.ENUM, _dbf_int):enum2int,
}

def any2string(srcdbf, srcval, srcmeta):
    #TODO: Use precision for floats
    dstval = map(str, srcval)
    dstmeta = DBRMeta()
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
        dstval = map(conv,srcval) # TODO: numpy specialization
    except ValueError:
        raise DBRNoConvert("Can't convert '%s'"%srcval)
    dstmeta = DBRMeta()
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
    if dstdbf==srcdbf:
        return (srcval, srcmeta)

    try:
        dcls, scls = _dbf_cls[dstdbf], _dbf_cls[srcdbf]
    except KeyError:
        raise DBRNoConvert("Conversion type not known")

    if dcls==scls:
        return (srcval, srcmeta)

    elif dstdbf==DBF.STRING:
        return any2string(srcdbf, srcval, srcmeta)
        
    elif srcdbf==DBF.STRING:
        return string2any(dstdbf, srcval, srcmeta)

    try:
        fn=_converts[(scls,dcls)]
    except KeyError:
        raise DBRNoConvert("No Conversion defined")

    return fn(srcval, srcmeta)
