"""Pool layout decoder for the qca_cld3 regdb.bin.

The iw reg get output is *range* records, but the file pool stores per-channel
entries (LE16 MHz + power). This script locates channel frequencies, infers
the record stride, and cross-validates against the live US readback captured
on 2026-11-23:

    2402-2472 @40 -> 30 dBm      5170-5250 @80 -> 24
    5250-5330 @80 -> 24 DFS       5490-5730 @160 -> 24 DFS
    5735-5855 @80 -> 30           5855-5925 @40 -> 30 NO-OUTDOOR
    5945-7105 @160 -> 24          5925-7105 @320 -> 24 NO-OUTDOOR
"""
import struct, re, sys

d = open('r1.bin', 'rb').read()
print('len', len(d))

# 1. Are iw's range records present verbatim?
for (s, e, bw) in [(2402, 2472, 40), (5735, 5855, 80), (5945, 7105, 160)]:
    pat = struct.pack('<HHH', s, e, bw)
    hits = [m.start() for m in re.finditer(re.escape(pat), d)]
    print('range %d-%d@%d hits=%s' % (s, e, bw, [hex(h) for h in hits[:6]]))

# 2. Channel frequencies as LE16.
ch24 = [2412 + 5 * i for i in range(11)]          # ch1..11
ch24_extra = [2467, 2472]                          # ch12/13 region
ch5 = [5180 + 5 * i for i in range(0, 12)] + [5500 + 5 * i for i in range(0, 20)] + [5745 + 5 * i for i in range(0, 20)]
ch6 = [5955 + 5 * i for i in range(0, 117)]        # 6G 20MHz channels 1..233

def findall_le16(v):
    pat = struct.pack('<H', v)
    return [m.start() for m in re.finditer(re.escape(pat), d)]

print()
print('=== frequency-anchor hit counts ===')
for v in [2412, 2417, 2422, 2427, 2432, 2437, 2442, 2447, 2452, 2457,
          2462, 2467, 2472, 5180, 5200, 5210, 5220, 5500, 5510, 5520,
          5745, 5755, 5775, 5775, 5955, 5965, 5975, 7115, 7125]:
    h = findall_le16(v)
    print('  %-5d (0x%04x): %2d hits %s' % (v, v, len(h), [hex(x) for x in h[:8]]))

# 3. Try to infer stride from consecutive 2.4G channel hits.
print()
print('=== 2.4G channel offsets and deltas ===')
offs = []
for v in ch24:
    h = findall_le16(v)
    offs.append((v, h))
    print('  ch %4d: %s' % (v, [hex(x) for x in h[:6]]))

def dump(off, n, label):
    print('--- %s @%04x ---' % (label, off))
    for i in range(0, n, 16):
        print('%05x  %s' % (off + i, ' '.join('%02x' % b for b in d[off + i:off + i + 16])))

# 4. Dump the neighbourhood of the first 2412 hit: 96 bytes before, 96 after.
h = findall_le16(2412)
if h:
    o = max(0, h[0] - 96)
    dump(o, 192, 'around first 2412')

# 5. Count LE16 values that look like wifi frequencies in the pool area.
print()
print('=== density scan: LE16 in wifi range per 16B-aligned row from 0x1000 ===')
def is_freq(v):
    return (2400 <= v <= 2495) or (4900 <= v <= 5950) or (5925 <= v <= 7130)

den = []
for base in range(0x1000, min(len(d) - 16, 0x1000), 1):
    break
# just report the first strong alignment candidate
cands = []
for stride_start in range(0, 8):
    cnt = 0
    for i in range(0x1000, len(d) - 1, 2):
        if (i % 8) == stride_start and is_freq(struct.unpack('<H', d[i:i + 2])[0]):
            cnt += 1
    cands.append((stride_start, cnt))
print('  mod-8 alignment freq counts:', cands)

# 6. Known anchor from prior notes: 30dBm (0x1e) for 2.4G near 0x203b.
dump(0x2000, 0x80, 'notes anchor 0x203b area')

# 7. Global 00 record anchors: global 00 power = 20 (0x14) for 2.4G/5G.
# Search for records containing both a 2.4G freq and 0x1e/0x14 nearby.
print()
print('=== per-2.4G-channel context (8B each side) ===')
for v in [2412, 2417, 2422, 2427, 2432, 2437, 2442, 2447, 2452, 2457, 2462, 2467, 2472]:
    for o in findall_le16(v)[:3]:
        print('  %-5d @%05x  ctx: %s' % (v, o, ' '.join('%02x' % b for b in d[o - 8:o + 10])))
