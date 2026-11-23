"""Brute-force the country-entry index -> rule-table mapping.

The 12-byte-contiguous model failed: no alignment/stride reproduces US's eight
live rows in order, so the earlier "structure cracked" claim was wrong and the
r1-vs-r2 null result proved nothing (those two files share the US data).

Strong constraint instead: the US entry carries several candidate indices
(u16+0 = 234, byte+2 = 0x21, u16+9 = 808, u16+11 = 5, u16+13 = 0x4508). For
each candidate, search every (base, stride) such that base + idx*stride lands
on the FIRST live US row and the following rows match iw's US sequence in
order. A mapping that satisfies US at several plausible record sizes is a real
lead; zero hits means the index model is wrong too.
"""
import struct

WANT = [
    (2402, 2472, 40, 30),
    (5170, 5250, 80, 24),
    (5250, 5330, 80, 24),
    (5490, 5730, 160, 24),
    (5735, 5855, 80, 30),
    (5855, 5925, 40, 30),
    (5945, 7105, 160, 24),
    (5925, 7105, 320, 24),
]

b = open('r2.bin', 'rb').read()
US_RAW = bytes.fromhex('ea 00 21 55 53 00 55 53 00 28 03 05 00 08 45 02'.replace(' ', ''))
CN_RAW = bytes.fromhex('8e 00 00 43 4e 00 43 4e 00 28 03 00 00 00 a2 00'.replace(' ', ''))


def row_at(i):
    if i + 9 > len(b):
        return None
    s, e, bw, fl, p = struct.unpack('<HHHHB', b[i:i + 9])
    return (s, e, bw, p), fl


def match_len(start, stride, need=len(WANT)):
    n = 0
    while n < need:
        got = row_at(start + n * stride)
        if not got or got[0] != WANT[n]:
            break
        n += 1
    return n


cands = {
    'u16+0 US': struct.unpack('<H', US_RAW[0:2])[0],
    'byte+2 US': US_RAW[2],
    'u16+9 US': struct.unpack('<H', US_RAW[9:11])[0],
    'u16+11 US': struct.unpack('<H', US_RAW[11:13])[0],
    'u16+13 US': struct.unpack('<H', US_RAW[13:15])[0],
    'byte+15 US': US_RAW[15],
    'n_entries': 238,
}

hits = []
for label, idx in cands.items():
    if idx <= 0:
        continue
    for stride in range(8, 48):
        for base in range(0x1000, len(b) - 9):
            off = base + idx * stride
            if off + 9 > len(b):
                break
            n = match_len(off, stride)
            if n >= 3:
                hits.append((n, label, idx, stride, hex(base), hex(off)))

hits.sort(reverse=True)
print('candidate indices:', cands)
print('hits with >=3 ordered rows:', len(hits))
for n, label, idx, stride, base, off in hits[:25]:
    print('  %d/%d rows  %s idx=%d stride=%d base=%s -> first row @%s'
          % (n, len(WANT), label, idx, stride, base, off))

print()
print('=== does any stride place the FIRST iw row at a page-aligned base? ===')
first_positions = [i for i in range(0x1000, len(b) - 9, 2)
                   if row_at(i) and row_at(i)[0] == WANT[0]]
print('positions of first US row:', [hex(x) for x in first_positions][:12])
for pos in first_positions[:12]:
    for stride in (12, 14, 16, 20, 24):
        n = match_len(pos, stride)
        if n >= 2:
            print('  first @%s stride=%d ordered=%d/%d  implied idx=%d base=%s'
                  % (hex(pos), stride, n, len(WANT),
                     234, hex(pos - 234 * stride)))
