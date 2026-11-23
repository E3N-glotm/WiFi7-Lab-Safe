import struct, sys

# GhostUnlock treats the file as a pure stream of 16-byte records from offset 0:
#   [0:2]=pad, [2:4]=country u16, [4:6]=regpair u16, [6]=6g superdomain,
#   [7:10]=alpha2, [10:13]=alpha2dup, [13:16]=tail
# Our notes assumed: [0:1]=global checksum, [2:3]=version, records start at 4.

def analyze(path):
    d = open(path, 'rb').read()
    print('===', path, 'len', len(d), 'first2', d[:2].hex(), 'ver@2', d[2:4].hex())
    nonzero02 = []
    recs = []
    off = 0
    while off + 16 <= 0x1000:
        f02 = struct.unpack_from('<H', d, off)[0]
        ctry = struct.unpack_from('<H', d, off+2)[0]
        pair = struct.unpack_from('<H', d, off+4)[0]
        s6 = d[off+6]
        a1 = d[off+7:off+9]
        if f02 != 0:
            nonzero02.append((off, hex(f02)))
        if all(65 <= b <= 90 for b in a1):
            recs.append((off, a1.decode(), ctry, pair, s6))
        off += 16
    print('records(16B from 0) valid-alpha2:', len(recs), ' nonzero[0:2] count:', len(nonzero02), nonzero02[:8])
    for off, cc, ctry, pair, s6 in recs:
        if cc in ('US','CN','JP','TW','XA','DE','AF'):
            f02 = struct.unpack_from('<H', d, off)[0]
            print(f'  {cc} @0x{off:04x} [0:2]={f02:#06x} ctry={ctry} pair={pair} super6g={s6:#04x}')

for p in sys.argv[1:]:
    analyze(p)
