# Ground truth from phone `iw reg get` (country US, self-managed phy):
#   (2402 - 2472 @ 40), 30 dBm
#   (5170 - 5250 @ 80), 24 dBm
#   (5250 - 5330 @ 80), 24 dBm, DFS
#   (5490 - 5730 @ 160), 24 dBm, DFS
#   (5735 - 5855 @ 80), 30 dBm
#   (5855 - 5925 @ 40), 30 dBm, NO-OUTDOOR
#   (5945 - 7105 @ 160), 24 dBm
#   (5925 - 7105 @ 320), 24 dBm, NO-OUTDOOR
import struct
data = open('r1.bin','rb').read()

def find_le16(v):
    b = struct.pack('<H', v)
    out = []
    i = data.find(b)
    while i != -1 and len(out) < 40:
        out.append(i); i = data.find(b, i+1)
    return out

# The most distinctive value is 7105 (0x1BE9) - only used by the 6GHz band.
print('7105 (0x1BE9):', [hex(x) for x in find_le16(7105)])
print('5945 (0x1741):', [hex(x) for x in find_le16(5945)])
print('5490 (0x1572):', [hex(x) for x in find_le16(5490)])
print('5170 (0x1432):', [hex(x) for x in find_le16(5170)])
print('2402 (0x096A):', [hex(x) for x in find_le16(2402)])
