import re, struct
r1 = open('r1.bin','rb').read()

# country code token "XX\0XX\0"; cc1 sits at entry_start+3
entries = []
for mm in re.finditer(rb'([A-Z]{2})\x00\1\x00', r1[:8192]):
    tok = mm.start()
    estart = tok - 3
    code = mm.group(1).decode()
    entries.append((estart, code))

# de-dup: an entry is valid if entry_start>=0 and bytes[3:5]==code bytes
valid = []
seen = set()
for estart, code in entries:
    if estart < 0 or estart+16 > len(r1):
        continue
    if r1[estart+3:estart+5] != code.encode():
        continue
    if estart in seen:
        continue
    seen.add(estart)
    valid.append((estart, code))

print('total candidate entries:', len(valid))
# print first 12 and the ones we care about
show = {}
for estart, code in valid[:12]:
    show[estart] = code
for estart, code in valid:
    if code in ('US','GB','CN','EG','DE','FR','JP'):
        show[estart] = code
for estart in sorted(show):
    raw = r1[estart:estart+16]
    f01 = struct.unpack('<H', raw[0:2])[0]
    b2 = raw[2]
    tag = struct.unpack('<H', raw[9:11])[0]
    ptr1314 = struct.unpack('<H', raw[13:15])[0]
    print('%5d %-3s | %s | f01=%d b2=%d tag=%d ptr13_14=%d(0x%x) tail=%02x' %
          (estart, show[estart], raw.hex(), f01, b2, tag, ptr1314, ptr1314, raw[15]))

# dump 2.4GHz band region
print()
print('=== band region 0x2020-0x20c0 ===')
seg = r1[0x2020:0x20c0]
for i in range(0, len(seg), 16):
    print('%5x  %s' % (0x2020+i, seg[i:i+16].hex(' ')))
