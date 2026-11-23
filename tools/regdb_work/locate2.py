"""Locate the 2.4G 2402-2472@40 records inside r2.bin (= the file the driver
actually downloads: /vendor/firmware_mnt/image/peach/regdb_xiaomi.bin, proven
from dmesg "cnss: Downloading REGDB: peach/regdb_xiaomi.bin").

Also decode the whole plausible-record window and print every candidate power
byte offset, so the bind-mount experiment edits a *power* byte (offset +8 of
the record) rather than a flag/padding byte.
"""
import struct

d = open('r2.bin', 'rb').read()
print('len', len(d), 'header checksum field', d[:2].hex(' '))

def rec(b, i):
    return struct.unpack('<HHHHBBBB', b[i:i + 12])

print()
print('=== 2402-2472 @40 records in r2.bin ===')
hits = []
for i in range(0x2000, len(d) - 12, 2):
    s, e, bw, fl, p = struct.unpack('<HHHHB', d[i:i + 9])
    if s == 2402 and bw == 40 and p <= 63:
        hits.append(i)
        print('  @0x%05x  %d-%d @%d flags=0x%04x pwr=%d x=(%d,%d,%d)  power-byte-abs=0x%05x (%d)'
              % (i, s, e, bw, fl, p, d[i + 9], d[i + 10], d[i + 11], i + 8, i + 8))
if not hits:
    print('  none with start=2402; scanning 2.4G band generally')
    for i in range(0x2000, 0x3100, 2):
        s, e, bw, fl, p = struct.unpack('<HHHHB', d[i:i + 9])
        if 2400 <= s <= 2500 and p <= 63 and bw in (5, 10, 20, 40):
            print('  @0x%05x  %d-%d @%d flags=0x%04x pwr=%d' % (i, s, e, bw, fl, p))

print()
print('=== full plausible decode 0x2030..0x3000 (r2/xiaomi) ===')
for i in range(0x2030, 0x3000, 12):
    s, e, bw, fl, p, x1, x2, x3 = rec(d, i)
    if 2400 <= s <= 7200 and s < e <= 7200 and bw in (5, 10, 20, 40, 80, 160, 320, 2160) and p <= 63:
        print('  @0x%05x  %5d-%-5d @%-4d flags=0x%04x pwr=%-3d x=(%d,%d,%d)'
              % (i, s, e, bw, fl, p, x1, x2, x3))

print()
print('=== r1 (stock) vs r2 (xiaomi) diff bytes in pool window ===')
r1 = open('r1.bin', 'rb').read()
diffs = [(i, r1[i], d[i]) for i in range(0x2000, 0x3100) if r1[i] != d[i]]
print('  differing bytes in 0x2000-0x3100:', len(diffs))
for i, a, b in diffs[:40]:
    print('   @0x%05x %02x -> %02x' % (i, a, b))
