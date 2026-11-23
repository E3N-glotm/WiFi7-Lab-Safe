import struct

for f in ['r1.bin', 'r2.bin', 'r3.bin']:
    d = open(f, 'rb').read()
    print('===', f, 'len', len(d))
    print('  head16 :', d[0:16].hex(' '), '| cc@4:', repr(d[4:6]), 'cc@10:', repr(d[10:12]))
    print('  [0:2]=', d[0:2].hex(), ' [2:4]u16=', struct.unpack('<H', d[2:4])[0])
    print('  rec1   :', d[16:32].hex(' '), '| cc@20:', repr(d[20:22]), 'iso@18=', struct.unpack('<H', d[18:20])[0])
    print('  rec2   :', d[32:48].hex(' '), '| cc@36:', repr(d[36:38]), 'iso@34=', struct.unpack('<H', d[34:36])[0])

# GhostUnlock model: records start at 0, [0:2]=pad, [2:4]=ISO numeric code.
# Ours: header(4) + records with cc at +4/+8. Check both readings against
# the known ISO numeric list for the first entries (AF=4, AX=248, AL=8, DZ=12).
iso = {'AF': 4, 'AX': 248, 'AL': 8, 'DZ': 12, 'AS': 16, 'AD': 20, 'AO': 24, 'AQ': 10, 'AG': 28, 'AR': 32, 'AM': 51, 'AW': 533, 'AU': 36, 'AT': 40, 'AZ': 31}
d = open('r1.bin', 'rb').read()
print()
print('ISO cross-check, our model (code at +6 rel entry, iso would be at +2):')
for i in range(4):
    e = 4 + i * 16
    cc = d[e + 6: e + 8]
    val = struct.unpack('<H', d[e + 2: e + 4])[0] if i else None
    print('  entry', i, 'cc', cc, 'field[2:4]=', val, 'expected iso=', iso.get(cc.decode(errors="replace")))
