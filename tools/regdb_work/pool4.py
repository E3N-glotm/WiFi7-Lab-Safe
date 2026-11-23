"""Index -> record-list mapping, and flag-bit decoding.

Pool record (12 bytes, first seen @0x2032):
  +0 u16 start | +2 u16 end | +4 u16 bw | +6 u16 flags | +8 u8 power | +9..11 u8
Index entry (16 bytes, from 4):
  +0 u16 planId | +2 u8 b2 | +3..4 cc | +5 u8 | +6..7 cc2 | +8 u8 | +9 u16 tag(0x0328)
  +11 u16 grp | +13 u16 ptr | +15 u8 flags
"""
import re, struct, sys

D = {n: open(n, 'rb').read() for n in ('r1.bin', 'r2.bin', 'r3.bin')}
r1 = D['r1.bin']

REC0 = 0x2032

def rec(d, i):
    s, e, bw, fl, p, x1, x2, x3 = struct.unpack('<HHHHBBBB', d[i:i + 12])
    return s, e, bw, fl, p, x1, x2, x3

# 1) index entries including digit codes (00 world domain!). Previous scans
#    used [A-Z]{2} and therefore MISSED the "00" record entirely.
def index(d):
    out = []
    for m in re.finditer(rb'([A-Z0-9]{2})\x00\1\x00', d[:0x1000]):
        e = m.start() - 3
        raw = d[e:e + 16]
        out.append(dict(off=e, cc=m.group(1).decode(),
                        plan=struct.unpack('<H', raw[0:2])[0],
                        b2=raw[2], tag=struct.unpack('<H', raw[9:11])[0],
                        grp=struct.unpack('<H', raw[11:13])[0],
                        ptr=struct.unpack('<H', raw[13:15])[0], fl=raw[15]))
    return out

E1 = index(r1)
print('index entries (digits included):', len(E1))
by = {x['cc']: x for x in E1}
for cc in ['00', 'US', 'CN', 'JP', 'GB', 'XA']:
    x = by.get(cc)
    print(' ', cc, x)

# 2) enumerate every record slot from REC0 on, and how many slots exist
slots = []
i = REC0
while i + 12 <= len(r1):
    s, e, bw, fl, p, x1, x2, x3 = rec(r1, i)
    ok = (2400 <= s <= 7200 and s < e <= 72000 and bw in (5, 10, 20, 40, 80, 160, 2160, 320) and p <= 63)
    slots.append((i, (s, e, bw, fl, p, x1, x2, x3), ok))
    i += 12
good = [s for s in slots if s[2]]
print()
print('slots from 0x%x: %d total, %d plausible' % (REC0, len(slots), len(good)))
print('first plausible @0x%x, last @0x%x' % (good[0][0], good[-1][0]))

# 3) Try to see whether (grp,ptr) selects a contiguous slice of the slot array.
#    Candidate encodings: rec index = (grp<<16|ptr) scaled, or ptr = slot index,
#    or ptr = byte offset from REC0.
if '00' in by:
    for cc in ['00', 'US', 'CN', 'JP']:
        x = by[cc]
        comb = (x['grp'] << 16) | x['ptr']
        print('%s plan=0x%04x grp=0x%04x ptr=0x%04x comb=0x%08x(%d)  REC0+comb=0x%x  comb/12=%d'
              % (cc, x['plan'], x['grp'], x['ptr'], comb, comb, REC0 + comb, comb / 12))

# 4) Does the count of records for a country equal iw's line count? We know US
#    has 8 range lines and world-00 has 8 lines. Find record groups whose
#    (s,e,bw) multiset equals the live readback.
US = [(2402, 2472, 40, 30), (5170, 5250, 80, 24), (5250, 5330, 80, 24), (5490, 5730, 160, 24),
      (5735, 5855, 80, 30), (5855, 5925, 40, 30), (5945, 7105, 160, 24), (5925, 7105, 320, 24)]
W0 = [(2402, 2472, 40, 20), (2457, 2482, 20, 20), (2474, 2494, 20, 20), (5170, 5250, 80, 20),
      (5250, 5330, 80, 20), (5490, 5730, 160, 20), (5735, 5835, 80, 20)]
print()
print('=== locate live-readback records (s,e,bw,pwr) in pool ===')
for label, tbl in (('US', US), ('W0', W0)):
    print('-- %s --' % label)
    for t in tbl:
        hits = [i for i, r, ok in slots if ok and r[:2] == t[:2] and r[2] == t[2] and r[4] == t[3]]
        if not hits:
            # relax the end value: iw prints rounded range ends
            hits = [i for i, r, ok in slots if ok and (r[0], r[2], r[4]) == (t[0], t[2], t[3])]
        for h in hits[:4]:
            r = rec(r1, h)
            print('   %-3d %-5d @%-4d pwr=%-3d -> @0x%05x flags=0x%04x x=(%d,%d,%d)'
                  % (t[0], t[1], t[2], t[3], h, r[3], r[5], r[6], r[7]))
        if not hits:
            print('   %-3d %-5d @%-4d pwr=%-3d -> NOT FOUND' % t)

# 5) flag-bit decoding: same (s,e,bw,pwr), differing flags => bit semantics.
print()
print('=== flag bit census (plausible records) ===')
from collections import Counter
c = Counter(r[3] for i, r, ok in slots if ok)
for fl, n in sorted(c.items()):
    print('  flags 0x%04x : %d records' % (fl, n))

# 6) specific bit probes with known iw semantics
print()
print('=== targeted bit probes ===')
def show(title, pred, limit=6):
    print('-- %s --' % title)
    n = 0
    for i, r, ok in slots:
        if ok and pred(r):
            print('   @0x%05x %5d-%-5d @%-4d flags=0x%04x pwr=%-3d x=(%d,%d,%d)'
                  % (i, r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]))
            n += 1
            if n >= limit:
                break
    if n == 0:
        print('   none')

# world-00 lines are all PASSIVE-SCAN; the 2474-2494 line additionally NO-OFDM.
show('2474-2494@20 (NO-OFDM in 00)', lambda r: r[0] == 2474 and r[2] == 20)
show('2457-2482@20 (AUTO-BW+PASSIVE in 00)', lambda r: r[0] == 2457 and r[2] == 20)
show('60GHz 57240 area', lambda r: r[0] >= 57000)
show('6G 5945/5925 starts', lambda r: r[0] in (5945, 5925) and r[2] in (160, 320))
