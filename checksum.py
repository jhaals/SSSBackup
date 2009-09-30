#!/usr/bin/env python
import sys
from zlib import adler32 as get_checksum
CHUNK_SIZE = 1024
try:
     file = open(sys.argv[1], 'rb')
except:
     sys.exit('I/O Error')
current = 0

while True:
    buffer = file.read(CHUNK_SIZE)

    if not buffer:
        break

    current = get_checksum(buffer, current)

print current
file.close()
