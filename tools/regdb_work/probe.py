"""Decode the r1(stock)/r2(xiaomi) differing offsets as 12-byte records so the
natural A/B probe is validated before spending another device reload.

r1/r2 are two stock vendor files that both carry a legal header checksum.
They differ in exactly four bytes that decode as 6G end frequencies
(0xd5=7125 in r1, 0xc1=7105 in r2). The device currently loads r2 and iw
prints "5945 - 7105", so if binding r1 moves that to 7125 the pool is the
source; if nothing moves, the pool decode is not what iw reports.
"""
import struct

r1 = open('r1.bin', 'rb').read()
r2 = open('r2.bin', 'rb').read()


def dec(b, i):
    return struct.unpack('<HHHHBBBB', b[i:i + 12])


print('=== decode around the four differing offsets ===')
for off in (0x258c, 0x2598, 0x25a4, 0x25c8):
    for base in (off - 8, off - 2, off):
        a = dec(r1, base)
        b = dec(r2, base)
        print('base=0x%05x r1=%s r2=%s %s'
              % (base, a, b, 'DIFF' if a != b else 'same'))
    print()

print('=== every differing byte in the whole file (not just pool window) ===')
d = [(i, r1[i], r2[i]) for i in range(len(r1)) if r1[i] != r2[i]]
print('total differing bytes:', len(d))
print('first:', hex(d[0][0]), 'last:', hex(d[-1][0]))

print()
print('=== longest identical run check: are r1/r2 same layout? ===')
print('r1 len', len(r1), 'r2 len', len(r2))

print()
print('=== US entry+0 field (0x00ea in both) and record dump at 0x4508 raw ===')
print('r1 @0x4508:', r1[0x4508:0x4560].hex(' '))
print('r2 @0x4508:', r2[0x4508:0x4560].hex(' '))

print()
print('=== scan for a table whose rows match the iw US output exactly ===')
target = [(2402, 2472, 40, 30), (5170, 5250, 80, 24), (5735, 5855, 80, 30)]
for i in range(0, len(r2) - 12, 2):
    s, e, bw, fl, p = struct.unpack('<HHHHB', r2[i:i + 9])
    if (s, e, bw, p) == (2402, 2472, 40, 30) and fl == 0:
        print('  candidate US 2.4G row @0x%05x' % i)
        for k in range(0, 120, 12):
            j = i + k
            if j + 12 > len(r2):
                break
            s2, e2, bw2, fl2, p2, x1, x2, x3 = dec(r2, j)
            print('    @0x%05x %5d-%-5d @%-4d flags=0x%04x pwr=%-3d x=(%d,%d,%d)'
                  % (j, s2, e2, bw2, fl2, p2, x1, x2, x3))
        break
