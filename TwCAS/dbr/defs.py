# -*- coding: utf-8 -*-

__all__ = ['DBF','allDBF','DBR','allDBR','DBE']

class _DBFEnums(object):
    STRING = 0
    INT   = 1 # alias for SHORT
    SHORT = 1
    FLOAT = 2
    ENUM  = 3
    CHAR  = 4
    LONG  = 5
    DOUBLE= 6

DBF = _DBFEnums()

allDBF = [DBF.STRING, DBF.INT, DBF.SHORT, DBF.FLOAT,
          DBF.ENUM, DBF.CHAR, DBF.LONG, DBF.DOUBLE]

class _DBREnums(object):
    STRING = 0
    INT   = 1 # alias for SHORT
    SHORT = 1
    FLOAT = 2
    ENUM  = 3
    CHAR  = 4
    LONG  = 5
    DOUBLE= 6

    STS_STRING = 7
    STS_INT = 8
    STS_SHORT = 8
    STS_FLOAT = 9
    STS_ENUM = 10
    STS_CHAR = 11
    STS_LONG = 12
    STS_DOUBLE = 13
    
    TIME_STRING = 14
    TIME_INT = 15
    TIME_SHORT = 15
    TIME_FLOAT = 16
    TIME_ENUM = 17
    TIME_CHAR = 18
    TIME_LONG = 19
    TIME_DOUBLE = 20
    
    GR_STRING = 21
    GR_INT = 22
    GR_SHORT = 22
    GR_FLOAT = 23
    GR_ENUM = 24
    GR_CHAR = 25
    GR_LONG = 26
    GR_DOUBLE = 27
    
    CTRL_STRING = 28
    CTRL_INT = 29
    CTRL_SHORT = 29
    CTRL_FLOAT = 30
    CTRL_ENUM = 31
    CTRL_CHAR = 32
    CTRL_LONG = 33
    CTRL_DOUBLE = 34
    
    PUT_ACKT = 35
    PUT_ACKS = 36
    STSACK_STRING = 37
    CLASS_NAME = 38

DBR = _DBREnums()

allDBR = [DBR.STRING, DBR.INT, DBR.SHORT, DBR.FLOAT,
          DBR.ENUM, DBR.CHAR, DBR.LONG, DBR.DOUBLE,
          
          DBR.STS_STRING, DBR.STS_INT, DBR.STS_SHORT, DBR.STS_FLOAT,
          DBR.STS_ENUM, DBR.STS_CHAR, DBR.STS_LONG, DBR.STS_DOUBLE,
          
          DBR.TIME_STRING, DBR.TIME_INT, DBR.TIME_SHORT, DBR.TIME_FLOAT,
          DBR.TIME_ENUM, DBR.TIME_CHAR, DBR.TIME_LONG, DBR.TIME_DOUBLE,
          
          DBR.GR_STRING, DBR.GR_INT, DBR.GR_SHORT, DBR.GR_FLOAT,
          DBR.GR_ENUM, DBR.GR_CHAR, DBR.GR_LONG, DBR.GR_DOUBLE,
          
          DBR.CTRL_STRING, DBR.CTRL_INT, DBR.CTRL_SHORT, DBR.CTRL_FLOAT,
          DBR.CTRL_ENUM, DBR.CTRL_CHAR, DBR.CTRL_LONG, DBR.CTRL_DOUBLE,
          ]

class DBRMeta(object):
    severity = 3 # INVALID
    status = 17 # UDF
    timestamp = (0,0)
    acks = 0

class _DBEEnums(object):
    VALUE = 1
    ARCHIVE = 2
    ALARM = 4
    PROPERTY = 8

DBE = _DBEEnums()
