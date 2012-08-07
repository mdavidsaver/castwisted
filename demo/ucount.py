#!/usr/bin/env python

# Use this script with the mailbox demo server.

from time import time
from cothread.catools import camonitor
from cothread import Sleep, WaitForAll

D = [0,0]

def count(value):
	D[0] += 1
	D[1] = value

Before = time()
M = camonitor('spam', count, all_updates=True)

Sleep(3.0)

M.close()
After = time()

I=After-Before

print 'interval',I,'s'
print 'counted',D[0],D[0]/I,'cnt/s'
print 'to',D[1]
