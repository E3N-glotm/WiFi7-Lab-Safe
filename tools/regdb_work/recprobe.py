"""Print record offsets/fields for given alpha2 codes in the loaded regdb.

Device patches must use offsets read from the file the driver actually loads
(regdb_xiaomi.bin == r2.bin), computed here rather than assumed.
"""
import struct
import sys

name = sys.argv[1] if len(sys.argv) > 1 else 'r2.bin'
codes = [c.encode() for c in (sys.argv[2:] or ['AR', 'US', 'CN'])]
d = open(name, 'rb').read()
print('file', name, 'len', len(d), 'head', d[0:2].hex())
for cc in codes:
    hit = False
    for o in range(0, 0x1000, 16):
        if d[o + 7:o + 9] == cc and d[o + 10:o + 12] == cc:
            print('  %s rec=0x%03x flags=%s pair=%-4d super6g=0x%02x '
                  'raw=%s   s6_offset=%d' %
                  (cc.decode(), o, d[o:o + 2].hex(),
                   struct.unpack_from('<H', d, o + 4)[0], d[o + 6],
                   d[o:o + 16].hex(' '), o + 6))
            hit = True
            break
    if not hit:
        print('  %s not present' % cc.decode())
