"""Census reg_dmn_pair ids and 6GHz super domains actually used by real dumps.

A candidate pair is only safe to write if the same firmware family already
ships it (GhostUnlock observed that an out-of-range super domain crashes the
firmware), so "supported by the built-in enum" is not sufficient evidence.
"""
import struct
import collections
import sys

FILES = ['r1.bin', 'r2.bin', 'r3.bin', 'net/giulia_kiwi.bin',
         'net/oplus_kiwi.bin', 'net/kiwi_nuwa_lfs.bin']

pair_uses = collections.Counter()
pair_files = collections.defaultdict(set)
super_uses = collections.Counter()

for f in FILES:
    d = open(f, 'rb').read()
    for o in range(0, 0x1000, 16):
        a = d[o + 7:o + 9]
        if len(a) == 2 and all(48 <= b <= 90 for b in a) and a == d[o + 10:o + 12]:
            p = struct.unpack_from('<H', d, o + 4)[0]
            pair_uses[p] += 1
            pair_files[p].add(f)
            super_uses[d[o + 6]] += 1

probe = [int(x, 0) for x in sys.argv[1:]] or [231, 117, 114, 109, 234, 232, 116, 142]
for p in probe:
    print('pair %-4d uses=%-4d files=%s' % (p, pair_uses.get(p, 0),
                                            sorted(pair_files.get(p, []))))
print('super6g 0x21 uses =', super_uses.get(0x21, 0))
print('super6g histogram (top) =', super_uses.most_common(8))
