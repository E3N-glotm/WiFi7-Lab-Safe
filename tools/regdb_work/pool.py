import struct
r1 = open('r1.bin','rb').read()

# correct 16-byte entry layout:
#  0-1  f01 u16 | 2  b2 | 3-8  cc NUL cc NUL | 9-10  tag u16 | 11-12  f4 u16 | 13-14 f5 u16 | 15 flags
import re
def entries(data):
    out=[]
    for mm in re.finditer(rb'([A-Z]{2})\x00\1\x00', data[:4096]):
        e = mm.start()-3
        raw = data[e:e+16]
        out.append(dict(code=mm.group(1).decode(), off=e,
            f01=struct.unpack('<H',raw[0:2])[0], b2=raw[2],
            tag=struct.unpack('<H',raw[9:11])[0],
            f4=struct.unpack('<H',raw[11:13])[0],
            f5=struct.unpack('<H',raw[13:15])[0], fl=raw[15]))
    return out

ES = {x['code']:x for x in entries(r1)}
for cc in ['US','GB','DE','CN','JP','FR']:
    x = ES[cc]
    print(cc, x)

def dump(off, n, label):
    print('=== %s @%04x ===' % (label, off))
    for i in range(0, n, 16):
        print('%04x  %s' % (off+i, r1[off+i:off+i+16].hex(' ')))

# f5 candidates as direct offsets
for cc in ['US','GB','DE']:
    x = ES[cc]
    if x['f5'] < len(r1):
        dump(x['f5'], 80, cc+' f5')
    else:
        print(cc, 'f5 out of range', x['f5'])

# known: US 2.4G max 30 dBm (0x1e), 5G UNII-1/2 24 (0x18), UNII-3 30 (0x1e), 6G 24 (0x18)
# GB: 2.4G 20 (0x14), 5G 20 (0x14)
# find 0x1e power-byte neighborhoods in 0x4000-0x6000
print('=== scan 0x4000-0x9000 for 16B records with plausible freqs ===')
def scan(base, n):
    cnt=0
    for i in range(base, base+n-12):
        s,e,bw = struct.unpack('<HHH', r1[i:i+6])
        pwr = r1[i+8]
        if (2400<=s<2500 or 5000<=s<8000) and 0<e-s<1500 and 0<bw<=400 and pwr<=40:
            print('%04x start=%d end=%d bw=%d flags=%d pwr=%d' % (i,s,e,bw,struct.unpack('<H',r1[i+6:i+8])[0],pwr))
            cnt+=1
            if cnt>60: return
scan(0x4000, 0x9000-0x4000)
