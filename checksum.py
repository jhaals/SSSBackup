#!/usr/bin/env python
from zlib import adler32
import sys
def checksum_of_file(path, chunk_size=1024):
    file = open(path, 'rb')
    current = 0

    while True:
        buffer = file.read(chunk_size)

        if not buffer:
            break

        current = adler32(buffer, current)

    file.close()

    return current

if __name__ == '__main__':
    try:
        print checksum_of_file(sys.argv[1])
    except IndexError:
        # Wrong number of arguments
        pass
    except:
        # Other error
        pass
