import struct
r1 = open('r1.bin','rb').read()
r2 = open('r2.bin','rb').read()

# 1) Are band-data regions (>=0x1000) identical?
diff_hi = [i for i in range(0x1000, len(r1)) if r1[i]!=r2[i]]
print('diff bytes >=0x1000:', len(diff_hi))
if diff_hi[:20]:
    print('first hi diffs:', [hex(x) for x in diff_hi[:20]])

# 2) Header checksum candidates. stock header u16 LE = 0xcea2, xiaomi = 0xe969
def sum16(b): return (sum(b) & 0xffff)
def xsum16(b):
    x=0
    for c in b: x^=c
    return x
def words16(b):
    s=0
    for i in range(0,len(b)-1,2): s=(s+ (b[i]|(b[i+1]<<8)))&0xffffffff
    s=(s&0xffff)+(s>>16)
    return s&0xffff
def crc16_ccitt(b, poly=0x1021, init=0xffff):
    crc=init
    for c in b:
        crc^=c<<8
        for _ in range(8):
            crc=((crc<<1)^poly)&0xffff if crc&0x8000 else (crc<<1)&0xffff
    return crc
def crc16_ibm(b, poly=0x8005, init=0x0000):
    crc=init
    for c in b:
        crc^=c
        for _ in range(8):
            crc=((crc<<1)^poly)&0xffff if crc&0x8000 else (crc<<1)&0xffff
    return crc

targets = {'stock':0xcea2, 'xiaomi':0xe969}
for name, data, want in [('stock',r1,0xcea2),('xiaomi',r2,0xe969)]:
    for rng_name, rng in [('skip2',data[2:]),('skip4',data[4:]),('full',data)]:
        cands = {
            'sum16': sum16(rng),
            'xsum16': xsum16(rng),
            'words16': words16(rng),
            'crc16ccitt': crc16_ccitt(rng),
            'crc16ccitt0': crc16_ccitt(rng, init=0),
            'crc16ibm': crc16_ibm(rng),
            'sum16+1': (sum16(rng)+1)&0xffff,
            'inv_sum': (0xffff-sum16(rng))&0xffff,
        }
        hits = [k for k,v in cands.items() if v==want]
        if hits:
            print('MATCH %s %s -> %s = %04x' % (name, rng_name, ','.join(hits), want))
    # also try: header stored as BE
    print('%s header bytes: %s  (LE=%04x BE=%04x)' % (name, data[:4].hex(), struct.unpack('<H',data[:2])[0], struct.unpack('>H',data[:2])[0]))
print('done header candidates')
