# -*- coding: utf-8 -*-

from struct import Struct

__all__ = ['metaEncode','metaDecode']

def unpackNone(obj, tup):
    return

def packNone(obj):
    return tuple()

def unpackSts(obj, (sts, sevr)):
    obj.status, obj.severity = sts, sevr

def packSts(obj):
    return (getattr(obj, 'status', 0), getattr(obj, 'severity', 0))

def unpackTime(obj, (sts, sevr, sec, nsec)):
    obj.status, obj.severity = sts, sevr
    obj.timestamp = (sec, nsec)

def packTime(obj):
    sts, sevr = getattr(obj, 'status', 0), getattr(obj, 'severity', 0)
    ts = getattr(obj, 'timestamp', (0,0))
    if isinstance(ts, tuple):
        sec, nsec = ts
    else:
        raise TypeError("Can not encode timestamp from type: %s",type(ts))
    return (sts, sevr, sec, nsec)

def unpackGRInt(obj, args):
    # status, severity, units, dU, dL, aU, wU, wL, aL
    obj.status, obj.severity, obj.units, \
    obj.upper_disp_limit, obj.lower_disp_limit, \
    obj.upper_warning_limit, obj.lower_warning_limit, \
    obj.upper_alarm_limit, obj.lower_alarm_limit = args

__grnumparts = ['upper_disp_limit','lower_disp_limit',
                'upper_alarm_limit','upper_warning_limit',
                'lower_warning_limit','lower_alarm_limit']

def packGRInt(obj):
    return packSts(obj) + (getattr(obj, 'units', ''),) + \
        tuple([getattr(obj, X, 0) for X in __grnumparts])

def unpackGRReal(obj, args):
    # status, severity, precision, units, dU, dL, aU, wU, wL, aL
    obj.status, obj.severity, obj.precision, obj.units, \
    obj.upper_disp_limit, obj.lower_disp_limit, \
    obj.upper_alarm_limit, obj.upper_warning_limit, \
    obj.lower_warning_limit, obj.lower_alarm_limit = args

def packGRReal(obj):
    return packSts(obj) + \
        (getattr(obj, 'precision', 0), getattr(obj, 'units', '')) + \
        tuple([getattr(obj, X, 0) for X in __grnumparts])

def unpackGREnum(obj, args):
    # status, severity, #strings, 26x enum strings
    obj.status, obj.severity = args[:2]
    N = args[2]
    N = min(26, N)
    obj.enums = list(args[3:(3+N)])

def packGREnum(obj):
    enums = getattr(obj, 'enums', [])
    N = min(26, len(enums))
    return packSts(obj) + (N,) + tuple(enums[:N])

def unpackCTRLInt(obj, args):
    # status, severity, units, dU, dL, aU, wU, wL, aL, cU, cL
    unpackGRInt(obj, args[:-2])
    obj.upper_ctrl_limit, obj.lower_ctrl_limit = args[-2:]

def packCTRLInt(obj):
    return packGRInt(obj) + \
        (getattr(obj, 'upper_ctrl_limit', 0),
         getattr(obj, 'lower_ctrl_limit', 0))

def unpackCTRLReal(obj, args):
    # status, severity, precision, units, dU, dL, aU, wU, wL, aL, cU, cL
    unpackGRReal(obj, args[:-2])
    obj.upper_ctrl_limit, obj.lower_ctrl_limit = args[-2:]

def packCTRLReal(obj):
    return packGRReal(obj) + \
        (getattr(obj, 'upper_ctrl_limit', 0),
         getattr(obj, 'lower_ctrl_limit', 0))

def unpackSTSACK(obj, args):
    obj.status, obj.severity, obj.ackt, obj.acks = args

def packSTSACK(obj):    
    return (getattr(obj, 'status', 0), getattr(obj, 'severity', 0),
            getattr(obj, 'ackt', 0), getattr(obj, 'acks', 0))

_dbr_meta={
    # no meta
    0  :(Struct(''), unpackNone, packNone), # DBR_STRING
    1  :(Struct(''), unpackNone, packNone), # DBR_SHORT (aka DBR_INT)
    2  :(Struct(''), unpackNone, packNone), # DBR_FLOAT
    3  :(Struct(''), unpackNone, packNone), # DBR_ENUM
    4  :(Struct(''), unpackNone, packNone), # DBR_CHAR
    5  :(Struct(''), unpackNone, packNone), # DBR_LONG
    6  :(Struct(''), unpackNone, packNone), # DBR_DOUBLE
    # status, severity
    7  :(Struct('!hh'),     unpackSts, packSts),
    8  :(Struct('!hh'),     unpackSts, packSts),
    9  :(Struct('!hh'),     unpackSts, packSts),
    10 :(Struct('!hh'),     unpackSts, packSts),
    11 :(Struct('!hhx'),    unpackSts, packSts),
    12 :(Struct('!hh'),     unpackSts, packSts),
    13 :(Struct('!hhxxxx'), unpackSts, packSts),
    # status, severity, ts_sec, ts_nsec
    14 :(Struct('!hhII'),    unpackTime, packTime),
    15 :(Struct('!hhIIxx'),  unpackTime, packTime),
    16 :(Struct('!hhII'),    unpackTime, packTime),
    17 :(Struct('!hhII'),    unpackTime, packTime),
    18 :(Struct('!hhIIxxx'), unpackTime, packTime),
    19 :(Struct('!hhII'),    unpackTime, packTime),
    20 :(Struct('!hhIIxxxx'),unpackTime, packTime),
    # status, severity, units, dU, dL, aU, wU, wL, aL
    22 :(Struct('!hh8shhhhhh'), unpackGRInt, packGRInt),
    25 :(Struct('!hh8sccccccx'), unpackGRInt, packGRInt),
    26 :(Struct('!hh8siiiiii'), unpackGRInt, packGRInt),
    # status, severity, precision, units, dU, dL, aU, wU, wL, aL
    23 :(Struct('!hhhxx8sffffff'), unpackGRReal, packGRReal),
    27 :(Struct('!hhhxx8sdddddd'), unpackGRReal, packGRReal),
    # status, severity, #strings, 26x enum strings
    24 :(Struct('!hhh' + '26s'*16), unpackGREnum, packGREnum),
    # status, severity, units, dU, dL, aU, wU, wL, aL, cU, cL
    29 :(Struct('!hh8shhhhhhhh'),    unpackCTRLInt, packCTRLInt),
    32 :(Struct('!hh8sccccccccx'),   unpackCTRLInt, packCTRLInt),
    33 :(Struct('!hh8siiiiiiii'),    unpackCTRLInt, packCTRLInt),
    30 :(Struct('!hhhxx8sffffffff'), unpackCTRLReal, packCTRLReal),
    34 :(Struct('!hhhxx8sdddddddd'), unpackCTRLReal, packCTRLReal),
    # Specials
    37 :(Struct('!HHHH'), unpackSTSACK, packSTSACK),
   }
_dbr_meta[21] = _dbr_meta[7] # GR_STRING
_dbr_meta[28] = _dbr_meta[7] # CTRL_STRING
_dbr_meta[31] = _dbr_meta[24] # CTRL_ENUM
_dbr_meta[35] = _dbr_meta[1] # PUT_ACKT
_dbr_meta[36] = _dbr_meta[1] # PUT_ACKS
_dbr_meta[38] = _dbr_meta[0] # CLASS_NAME

def metaDecode(dbr, data, obj):
    """metaDecode(dbr#, bytestring, obj)
    Decode data CA meta-data from the given
    string and store in the given object
    """
    xcode, unpack, _ = _dbr_meta[dbr]
    unpack(obj, xcode.unpack(data))

def metaEncode(dbr, obj):
    xcode, _, pack = _dbr_meta[dbr]
    args = pack(obj)
    return xcode.pack(*args)
