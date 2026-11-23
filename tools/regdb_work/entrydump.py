"""Dump the country index entry for US/CN and whatever its ptr field points at.

Index entries start at 4, stride 16, cc at +3..4 and +6..7 (cc NUL cc NUL).
Observed fields (US): f01=0x00EA b2=33 tag=0x0328 grp=5 ptr=0x4528 fl=2
Observed (CN):       f01=0x0074 b2=0  tag=0x0328 grp=0 ptr=0xA200 fl=0
CN ptr 0xA200=41472 exceeds the 24278-byte file, so ptr is not a raw byte
offset for every country: the pair (grp,ptr) must be an index pair, or the
u16s at +11/+13 are one u32 (ptr32 = ptr<<16 | grp or grp<<16 | ptr).
"""
import re, struct

for name in ('r1.bin', 'r2.bin'):
    d = open(name, 'rb').read()
    print('=====', name, 'len', len(d), '=====')
    ents = []
    for m in re.finditer(rb'([A-Z0-9]{2})\x00\1\x00', d[:0x1000]):
        ents.append((m.start() - 3, m.group(1).decode()))
    print('entries:', len(ents), 'first', hex(ents[0][0]), 'last', hex(ents[-1][0]),
          'stride check', ents[1][0] - ents[0][0])
    by = dict((c, o) for o, c in ents)
    for cc in ('US', 'CN', 'GB', 'JP'):
        o = by[cc]
        raw = d[o:o + 16]
        u0 = struct.unpack('<H', raw[0:2])[0]
        u9 = struct.unpack('<H', raw[9:11])[0]
        u11 = struct.unpack('<H', raw[11:13])[0]
        u13 = struct.unpack('<H', raw[13:15])[0]
        lo32 = struct.unpack('<I', raw[8:12])[0]
        hi32 = struct.unpack('<I', raw[12:16])[0]
        print('%s @%5d %s' % (cc, o, raw.hex(' ')))
        print('    u16+0=0x%04x u16+9=0x%04x u16+11=0x%04x u16+13=0x%04x  u32+8=0x%08x u32+12=0x%08x'
              % (u0, u9, u11, u13, lo32, hi32))
        for label, cand in (('u16+13', u13), ('u16+11', u11),
                            ('hi32', hi32 & 0x1FFFF if hi32 < 0x20000 else -1),
                            ('lo32&mask', lo32 & 0xFFFF)):
            if 0 <= cand < len(d) - 48 and cand > 0x1000:
                print('    --> dump @0x%05x (%s)' % (cand, label))
                for k in range(0, 48, 12):
                    i = cand + k
                    s, e, bw, fl, p, x1, x2, x3 = struct.unpack('<HHHHBBBB', d[i:i + 12])
                    print('        @0x%05x %5d-%-5d @%-4d flags=0x%04x pwr=%-3d x=(%d,%d,%d)'
                          % (i, s, e, bw, fl, p, x1, x2, x3))
    print()
    # per-country 4-byte field at entry+0: is it a checksum over the country data?
    print('    entry+0 census (first 12):')
    for o, c in ents[:12]:
        print('      %s %s' % (c, d[o:o + 4].hex(' ')))
