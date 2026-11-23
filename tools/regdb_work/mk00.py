"""Build a regdb variant that clones the US record as country '00'.

Layout (GhostUnlock-verified): 16-byte records from offset 0:
  [0:2] checksum/reserved, [2:4] ISO numeric country LE16,
  [4:6] reg_dmn_pair_id LE16, [6] 6GHz super domain,
  [7:10] alpha2+NUL, [10:13] alpha2 dup, [13:15] tag 0x0328, [15] tail
"""
import struct
import sys

SRC = 'r1.bin'
d = bytearray(open(SRC, 'rb').read())

# locate last valid record and first all-zero slot
last = None
for o in range(0, 0x1000, 16):
    a1 = d[o + 7:o + 9]
    if all(48 <= b <= 90 for b in a1) and a1 == d[o + 10:o + 12]:
        last = o
print('last record @', hex(last), bytes(d[last:last + 16]).hex(' '))
free = last + 16
print('first free slot @', hex(free), 'bytes', bytes(d[free:free + 16]).hex(' '))
assert bytes(d[free:free + 16]) == b'\x00' * 16, 'slot not empty'

# US record clone with alpha2 '00', ISO country 0
us = struct.unpack_from('<HH', d, last + 2)
print('last record ctry/pair:', us)
rec = bytearray(16)
struct.pack_into('<H', rec, 0, 0)          # checksum field: 0 (verified loadable)
struct.pack_into('<H', rec, 2, 0)          # ISO numeric country 0 = world
pair = struct.unpack_from('<H', d, 0xdd0 + 4)[0]   # real US record pair id
s6 = d[0xdd0 + 6]
struct.pack_into('<H', rec, 4, pair)
rec[6] = s6
rec[7:10] = b'00\x00'
rec[10:13] = b'00\x00'
struct.pack_into('<H', rec, 13, 0x0328)
rec[15] = 0x05
print('new record', bytes(rec).hex(' '), 'pair=%d super6g=%s' % (pair, hex(s6)))
d[free:free + 16] = rec

out = sys.argv[1] if len(sys.argv) > 1 else 'r00clone.bin'
# header checksum: keep original a2ce (test whether records are covered at all)
open(out, 'wb').write(bytes(d))
print('wrote', out, 'len', len(d), 'head', bytes(d[:4]).hex(' '))
