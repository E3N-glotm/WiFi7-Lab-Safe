"""Locate the contiguous US regulatory block in r2 (the file the driver loads)
by matching the *ordered* ground-truth rows that `iw reg get` prints for US.

Ground truth (live, self-managed phy):
  2402-2472 @40  pwr30  AUTO-BW
  5170-5250 @80  pwr24  AUTO-BW
  5250-5330 @80  pwr24  DFS
  5490-5730 @160 pwr24  DFS
  5735-5855 @80  pwr30  AUTO-BW
  5855-5925 @40  pwr30  NO-OUTDOOR
  5945-7105 @160 pwr24  AUTO-BW
  5925-7105 @320 pwr24  NO-OUTDOOR

If a contiguous run of 12-byte records matches this sequence, its offset is
US's real block, and editing that block is the surgical test. If no run exists
at any alignment/stride, the 12-byte-stride model is wrong and the "structure
is cracked" claim must be dropped.
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


def rows(b, stride, start=0x2000):
    out = []
    for i in range(start, len(b) - 12, stride):
        s, e, bw, fl, p = struct.unpack('<HHHHB', b[i:i + 9])
        out.append((i, s, e, bw, fl, p))
    return out


for name in ('r1.bin', 'r2.bin'):
    b = open(name, 'rb').read()
    print('=====', name, '=====')
    for stride in (12, 2, 1):
        rs = rows(b, stride)
        best = (0, 0)
        for k in range(len(rs) - len(WANT)):
            hit = 0
            while hit < len(WANT):
                i, s, e, bw, fl, p = rs[k + hit]
                if (s, e, bw, p) == WANT[hit]:
                    hit += 1
                else:
                    break
            if hit > best[0]:
                best = (hit, k)
            if hit == len(WANT):
                break
        hit, k = best
        if hit >= 3:
            print('  stride=%d best contiguous match %d/%d starting @0x%05x'
                  % (stride, hit, len(WANT), rs[k][0]))
            for j in range(hit):
                i, s, e, bw, fl, p = rs[k + j]
                print('     @0x%05x %5d-%-5d @%-4d flags=0x%04x pwr=%-3d powbyte=%d'
                      % (i, s, e, bw, fl, p, i + 8))
        else:
            print('  stride=%d no contiguous run >=3 (best %d)' % (stride, hit))
    print()
