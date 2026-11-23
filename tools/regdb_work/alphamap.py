"""Which alpha2 codes already select the high-power pairs we found?

The live pair-exchange test disproved the "edit record pair -> table changes"
model: patching the loaded regdb's US record from 234 to 231 left the iw table
byte-identical. The consistent model is that the host resolves the built-in
pair from alpha2, while the record's 6GHz super-domain byte does come from the
file (which is why GhostUnlock's one-byte superdomain edit worked).

So the practical knob for 2.4/5 GHz is the country code itself. Map each
interesting pair id to the alpha2 codes that already carry it in real dumps --
any of those can be requested through `cmd wifi force-country-code` with no
file edit at all.
"""
import struct
import sys
import collections

import hosttables as H

FILES = ['r1.bin', 'r2.bin', 'r3.bin', 'net/giulia_kiwi.bin',
         'net/oplus_kiwi.bin', 'net/kiwi_nuwa_lfs.bin']

WANT = {int(x, 0) for x in sys.argv[1:]} or {231, 117, 114, 109, 234, 116}

for f in FILES:
    d = open(f, 'rb').read()
    hits = collections.defaultdict(list)
    for o in range(0, 0x1000, 16):
        a = d[o + 7:o + 9]
        if len(a) == 2 and all(48 <= b <= 90 for b in a) and a == d[o + 10:o + 12]:
            p = struct.unpack_from('<H', d, o + 4)[0]
            if p in WANT:
                hits[p].append((a.decode(), hex(d[o + 6])))
    if hits:
        print('===', f)
        for p in sorted(hits):
            sym = next((s for s, i in H.PAIR_IDS.items() if i == p and s in H.PAIRS), '?')
            codes = ' '.join('%s(s6=%s)' % t for t in hits[p])
            print('  pair %-4d %-14s -> %s' % (p, sym, codes))
