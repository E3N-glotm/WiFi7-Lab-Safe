"""Fingerprint search: locate the exact record block for a country.

We know the live US (phy#0 self-managed) table and the live world-00 (global)
table verbatim from `iw reg get`. We search the pool for a contiguous run of
12-byte records whose decoded (start,end,bw,power) sequence equals that table.
That pins the offsets we must edit, with no guessing.

Flag bits decoded by cross-validation against the same readback:
  0x0008 DFS      0x0002 PASSIVE-SCAN     0x0040 NO-OFDM     0x0200 NO-OUTDOOR
"""
import struct

d = open('r1.bin', 'rb').read()

def rec(i):
    return struct.unpack('<HHHHBBBB', d[i:i + 12])

# Live US table (phy#0). iw prints 5945-7105 but the pool uses 7125; allow both.
US = [(2402, 2472, 40, 30), (5170, 5250, 80, 24), (5250, 5330, 80, 24),
      (5490, 5730, 160, 24), (5735, 5855, 80, 30), (5855, 5925, 40, 30),
      (5945, 7105, 160, 24), (5925, 7105, 320, 24)]

def norm(s, e, bw, p):
    return (s, 7125 if e in (7105, 7125) else e, bw, p)

TARGET = [norm(*t) for t in US]

print('=== ordered-window search for the live US table (8 records) ===')
for i in range(0x2000, len(d) - 96, 2):
    got = [norm(*rec(i + 12 * k)[:4]) for k in range(8)]
    got = [(r[0], r[1], r[2], r[3]) for r in got]
    if got == TARGET:
        print('EXACT ORDERED MATCH @0x%05x' % i)
        for k in range(8):
            j = i + 12 * k
            r = rec(j)
            print('   @0x%05x %5d-%-5d @%-4d flags=0x%04x pwr=%d x=(%d,%d,%d)'
                  % (j, r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]))

print()
print('=== unordered window search (any 8-record window containing the table) ===')
tset = sorted(TARGET)
for i in range(0x2000, len(d) - 96, 2):
    got = sorted((rec(i + 12 * k)[0], 7125 if rec(i + 12 * k)[1] in (7105, 7125) else rec(i + 12 * k)[1],
                  rec(i + 12 * k)[2], rec(i + 12 * k)[4]) for k in range(8))
    if got == tset:
        print('UNORDERED MATCH @0x%05x' % i)

print()
print('=== relaxed: windows containing >=6 of the US tuples ===')
for i in range(0x2000, len(d) - 96, 2):
    got = set((rec(i + 12 * k)[0], 7125 if rec(i + 12 * k)[1] in (7105, 7125) else rec(i + 12 * k)[1],
               rec(i + 12 * k)[2], rec(i + 12 * k)[4]) for k in range(8))
    hit = len(got & set(TARGET))
    if hit >= 6:
        print('  @0x%05x hits=%d' % (i, hit))

# neighbourhood dumps to read the block structure directly
def dump(lo, hi, label):
    print()
    print('=== %s ===' % label)
    for i in range(lo, hi, 12):
        r = rec(i)
        tag = ''
        if 2400 <= r[0] <= 7200 and r[0] < r[1] <= 7200 and r[2] in (5, 10, 20, 40, 80, 160, 320, 2160) and r[4] <= 63:
            tag = '%5d-%-5d @%-4d flags=0x%04x pwr=%-3d x=(%d,%d,%d)' % (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7])
        else:
            tag = d[i:i + 12].hex(' ')
        print('  @0x%05x  %s' % (i, tag))

dump(0x2730, 0x2790, 'around 0x273a (candidate US block)')
dump(0x2580, 0x25e0, 'around 0x258a (6G 24dBm records)')
dump(0x2028, 0x20c8, 'around 0x2032 (2.4G 30/20/36 dBm trio)')
