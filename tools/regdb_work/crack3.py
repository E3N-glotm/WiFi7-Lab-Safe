import struct
r1 = open('r1.bin','rb').read()
r2 = open('r2.bin','rb').read()
n = len(r1)
h1 = struct.unpack('<H', r1[:2])[0]
h2 = struct.unpack('<H', r2[:2])[0]

def reflect8(b):
    r=0
    for i in range(8):
        if b&(1<<i): r|=1<<(7-i)
    return r
def reflect16(b):
    r=0
    for i in range(16):
        if b&(1<<i): r|=1<<(15-i)
    return r

def crc16(data, poly, init, refin, refout, xorout):
    crc=init
    for c in data:
        if refin: c=reflect8(c)
        crc^=c<<8
        for _ in range(8):
            crc=((crc<<1)^poly)&0xffff if crc&0x8000 else (crc<<1)&0xffff
    if refout: crc=reflect16(crc)
    return crc^xorout

# Full named CRC16 catalog: (name, poly, init, refin, refout, xorout)
cat = [
 ('ARC',0x8005,0x0000,False,False,0x0000),
 ('IBM-31-3-2',0x8005,0x0000,False,False,0x0000),
 ('MAXIM',0x8005,0x8005,True,True,0x0000),
 ('DOW',0x8005,0x8005,True,True,0x0000),
 ('1-DIFC',0x8005,0x0000,False,True,0xFFFF),
 ('X-25',0x1021,0xFFFF,True,True,0xFFFF),
 ('CCITT-FALSE',0x1021,0xFFFF,False,False,0x0000),
 ('CCITT',0x1021,0x0000,True,True,0x0000),
 ('KERMIT',0x1021,0x0000,True,True,0x0000),
 ('XMODEM',0x1021,0x0000,False,False,0x0000),
 ('ACORN',0x1021,0x0000,False,False,0x0000),
 ('T10-DIFC',0x1021,0x0000,False,False,0xFFFF),
 ('DNP',0x3D65,0x0000,True,True,0x0000),
 ('AEC',0x0589,0x0000,True,True,0x0001),
 ('BUYPASS',0x8005,0x0000,False,False,0xFFFF),
 ('GENIBUS',0x1021,0xFFFF,False,False,0xFFFF),
 ('MAXIM-COMPAT',0x8005,0x8005,True,True,0xFFFF),
 ('RCC',0x1021,0xFFFF,False,True,0xFFFF),
 ('RIPEMD128',0x8005,0xB2AA,False,False,0x0000),
 ('TELEDISC',0x1021,0xFFFF,True,True,0x0000),
 ('UMTS',0x8005,0x0000,False,False,0xFFFF),
 ('X-25-COMPAT',0x1021,0xFFFF,True,True,0x0000),
 ('CDMA2000',0xC867,0x0000,True,True,0x0000),
 ('CRSC',0x000A,0x0000,True,True,0x0000),
 ('KERMIT-COMPAT',0x1021,0x0000,True,True,0xFFFF),
 ('MODBUS',0x8005,0xFFFF,True,True,0x0000),
 ('FLEXBUS',0x9005,0x0000,False,False,0xFFFF),
 ('FLEXIBUS',0x9005,0x0000,False,False,0xFFFF),
 ('TMS37157-RLE',0x1021,0x89EC,False,False,0xFFFF),
 ('I-CODEC',0x5935,0x0000,True,True,0x0000),
 ('RSC',0x8005,0xFFFF,True,True,0xFFFF),
 ('BAGATTA-16',0x1021,0x0000,True,True,0xFFFF),
 ('BAGATTA-16-COMPAT',0x1021,0x0000,True,True,0x0000),
 ('BPT',0x3D65,0x0000,True,True,0xFFFF),
 ('ECMA-182',0x8408,0x0000,False,False,0xFFFF),
 ('ECMA-182-COMPAT',0x8408,0x0000,False,False,0x0000),
 ('DENSO-WAVE',0x8005,0xFFFF,True,True,0x0001),
 ('DENSO-WAVE-COMPAT',0x8005,0xFFFF,True,True,0x0000),
 ('DARC',0x0081,0x0000,True,True,0x0000),
 ('V-42',0x1021,0xFFFF,False,True,0xFFFF),
 ('PICC',0x8005,0x0000,True,True,0xFFFF),
 ('RIPEMD128',0x8005,0xB2AA,False,False,0x0000),
 ('CRC-16/1D-63-0',0x8005,0x0000,False,False,0x0000),
]

# scopes with checksum field zeroed
def make_scopes(data):
    z = bytearray(data); z[0]=0; z[1]=0
    zb = bytes(z)
    out = {
     'z01_full': zb,
     'z01_[2:]': zb[2:],
     'z01_[4:]': zb[4:],
     'raw_full': bytes(data),
     'raw_[2:]': bytes(data[2:]),
     'raw_[4:]': bytes(data[4:]),
     'idx_[4:3796]': zb[4:4+237*16],
     'idx_[4:3812]': zb[4:4+238*16],
    }
    return out

hits=[]
for name,poly,init,refin,refout,xorout in cat:
    for sname, sdata in make_scopes(r1).items():
        if crc16(sdata,poly,init,refin,refout,xorout)==h1:
            hits.append((name,sname,'stock'))
    for sname, sdata in make_scopes(r2).items():
        if crc16(sdata,poly,init,refin,refout,xorout)==h2:
            hits.append((name,sname,'xiaomi'))

if hits:
    print('=== CRC16 CATALOG HITS ===')
    for x in hits: print(x)
else:
    print('no catalog hit across %d variants x 8 scopes x 2 files'%len(cat))

# Cross-check: a true algorithm must hit BOTH files in the SAME scope+variant.
# Build set of (name,scope) that hit stock and (name,scope) that hit xiaomi, intersect.
s_hit=set((x[0],x[1]) for x in hits if x[2]=='stock')
x_hit=set((x[0],x[1]) for x in hits if x[2]=='xiaomi')
both = s_hit & x_hit
print('consistent (both files, same variant+scope):', both)
