"""Pick the most diagnostic whole-file swap for the cold-boot test.

r1/r2 differ only in ~312 bytes and share the US rows iw prints, so an r1 swap
proves little. r3 is a different device (kiwi) regdb; if its decoded rows for
the same bands differ from pudding's live iw output, binding r3 and cold
booting is an unambiguous test of whether the phy table follows regdb content.
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


def scan(name):
    b = open(name, 'rb').read()
    print('=====', name, 'len', len(b), 'hdr', b[:2].hex(' '), '=====')
    # every 12-byte-aligned (from 0x2000) record that matches a wanted row
    found = {}
    for i in range(0x2000, len(b) - 12, 2):
        s, e, bw, fl, p = struct.unpack('<HHHHB', b[i:i + 9])
        key = (s, e, bw, p)
        if key in WANT:
            found.setdefault(key, []).append((i, fl))
    for key in WANT:
        hits = found.get(key, [])
        loc = ', '.join('0x%05x/f=0x%04x' % (i, fl) for i, fl in hits[:4])
        print('  live-row %-26s hits=%-3d %s' % (str(key), len(hits), loc))
    # 6G end-frequency census: which 71xx values does this file contain?
    ends = {}
    for i in range(0x2000, len(b) - 12, 2):
        s, e, bw, fl, p = struct.unpack('<HHHHB', b[i:i + 9])
        if 5900 <= s <= 7200 and 5900 <= e <= 7300:
            ends.setdefault(e, []).append(i)
    print('  6G end-frequency values:', {k: len(v) for k, v in sorted(ends.items())})
    print()
    return b


r1 = scan('r1.bin')
r2 = scan('r2.bin')
r3 = scan('r3.bin')

d13 = [(i, r1[i], r3[i]) for i in range(min(len(r1), len(r3))) if r1[i] != r3[i]]
d23 = [(i, r2[i], r3[i]) for i in range(min(len(r2), len(r3))) if r2[i] != r3[i]]
print('r1 vs r3 differing bytes:', len(d13))
print('r2 vs r3 differing bytes:', len(d23))
