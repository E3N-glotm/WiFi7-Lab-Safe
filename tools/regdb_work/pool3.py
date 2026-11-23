"""Full 12-byte record walk of the regdb.bin pool.

Record layout confirmed at 0x2032 (stride 12):
  +0 u16 start_mhz | +2 u16 end_mhz | +4 u16 bw_mhz | +6 u16 f6 | +8 u8 power | +9..11 u8 x3
Cross-anchors (live device readback 2026-11-23):
  US: 2402-2472@40=30, 5170-5250@80=24, 5250-5330@80=24+DFS, 5490-5730@160=24+DFS,
      5735-5855@80=30, 5855-5925@40=30 NO-OUTDOOR, 5945-7105@160=24, 5925-7105@320=24 NO-OUTDOOR
  00: same ranges power 20 (incl 2457-2482, 2474-2494 NO-OFDM, 5735-5835), no 6G ranges
"""
import struct

d = open('r1.bin', 'rb').read()
N = len(d)

def rec(i):
    s, e, bw, f6, p, x1, x2, x3 = struct.unpack('<HHHHBBBB', d[i:i + 12])
    return s, e, bw, f6, p, x1, x2, x3

def looks_rec(i):
    if i + 12 > N:
        return False
    s, e, bw, f6, p, x1, x2, x3 = rec(i)
    if not (2400 <= s <= 7200 and s < e <= 7200 and e - s <= 1300):
        return False
    if bw not in (5, 10, 20, 40, 80, 160, 2160, 320, 240, 160, 80, 40):
        return False
    if p > 60 or x1 > 8 or x2 > 8 or x3 > 8:
        return False
    return True

print('=== contiguous 12-byte record chains (len>=4) ===')
i = 0x1000
chains = []
while i < N - 12:
    if looks_rec(i):
        j = i
        while looks_rec(j):
            j += 12
        if (j - i) // 12 >= 4:
            chains.append((i, (j - i) // 12))
        i = j
    else:
        i += 2
for c, n in chains:
    print('chain @0x%05x len=%d (0x%05x..0x%05x)' % (c, n, c, c + 12 * n))

def dump_chain(c, n):
    print('--- chain @0x%05x (%d recs) ---' % (c, n))
    for k in range(n):
        i = c + 12 * k
        s, e, bw, f6, p, x1, x2, x3 = rec(i)
        print('  @0x%05x %5d-%-5d @%-4d f6=0x%04x pwr=%-3d x=(%d,%d,%d)' % (i, s, e, bw, f6, p, x1, x2, x3))

for c, n in chains[:6]:
    dump_chain(c, min(n, 40))

# locate US block: contains 5735-5855 with pwr 30 and 5170-5250 with pwr 24
print()
print('=== tuples of interest (all hits, decoded) ===')
def find(s, e, bw):
    out = []
    for i in range(0x1000, N - 12):
        if (i & 1) == 0:
            r = rec(i)
            if r[0] == s and r[1] == e and r[2] == bw:
                out.append(i)
    return out

for tup in [(2402, 2472, 40), (5170, 5250, 80), (5735, 5855, 80), (5855, 5925, 40),
            (5945, 7105, 160), (5925, 7105, 320), (5945, 7125, 160), (5925, 7125, 320),
            (5490, 5730, 160), (5250, 5330, 80), (57240 - 50000, 0, 0)][:10]:
    if tup[1] == 0:
        continue
    hits = find(*tup)
    print('(%d,%d,%d): %s' % (tup[0], tup[1], tup[2],
          ['@0x%05x pwr=%d f6=0x%04x x=%s' % (h, rec(h)[4], rec(h)[3], rec(h)[5:]) for h in hits[:10]]))

# 60 GHz record from 00 readback: 57240-63720@2160 - check encoding
print()
print('=== scan for 60GHz-ish (u16 may wrap: 57240>65535? no) ===')
for i in range(0x1000, N - 12, 2):
    r = rec(i)
    if r[0] > 20000:
        print('  @0x%05x' % i, r)

# flag-bit decode: same geometry, differing flags
print()
print('=== flag diff: DFS pair (5490-5730@160 vs 5170-5250@80 same pwr 24) ===')
for t in [(5490, 5730, 160), (5170, 5250, 80)]:
    for h in find(*t)[:6]:
        print('  ', t, '@0x%05x' % h, rec(h), d[h:h + 12].hex(' '))
print('=== flag diff: NO-OUTDOOR pair (5855-5925@40 NO vs 5735-5855@80 plain) ===')
for t in [(5855, 5925, 40), (5735, 5855, 80)]:
    for h in find(*t)[:8]:
        print('  ', t, '@0x%05x' % h, rec(h), d[h:h + 12].hex(' '))
