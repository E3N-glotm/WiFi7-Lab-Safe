"""Dump regdb.bin records as (alpha2, ctry, pair, super6g, tail) and stats."""
import struct
import collections
import sys

for f in sys.argv[1:] or ['r1.bin']:
    d = open(f, 'rb').read()
    rows = []
    for o in range(0, 0x1000, 16):
        a1 = d[o + 7:o + 9]
        a2 = d[o + 10:o + 12]
        if all(48 <= b <= 90 for b in a1) and a1 == a2:
            rows.append((a1.decode(), struct.unpack_from('<H', d, o + 2)[0],
                         struct.unpack_from('<H', d, o + 4)[0], d[o + 6],
                         d[o + 15], struct.unpack_from('<H', d, o + 13)[0]))
    print('===', f, 'records', len(rows))
    print('max pair id', max(r[2] for r in rows))
    print('distinct pair ids', len(set(r[2] for r in rows)))
    for r in rows:
        if r[0] in ('US', 'CN', 'JP', '00', 'XA', 'TW', 'DE'):
            print('  %s ctry=%-4d pair=%-4d super6g=%s tail=%s tag13=%s' %
                  (r[0], r[1], r[2], hex(r[3]), hex(r[4]), hex(r[5])))
    print('  super6g hist', collections.Counter(r[3] for r in rows).most_common(10))
    print('  tail15  hist', collections.Counter(r[4] for r in rows).most_common(8))
    print('  tag13   hist', collections.Counter(r[5] for r in rows).most_common(8))
