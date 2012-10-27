# -*- coding: utf-8 -*-

__all__ = ['DBF','DBR']

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
