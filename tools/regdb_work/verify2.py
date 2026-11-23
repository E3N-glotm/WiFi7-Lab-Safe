import struct
r1 = open('r1.bin','rb').read()
r2 = open('r2.bin','rb').read()
h1le = struct.unpack('<H', r1[:2])[0]
h2le = struct.unpack('<H', r2[:2])[0]

def reflect16(a):
    r=0
    for i in range(16):
        if a&(1<<i): r|=1<<(15-i)
    return r

POLY = 0x860F
RP = reflect16(POLY)
# standard reflected table
tbl=[]
for b in range(256):
    crc=b
    for _ in range(8):
        crc=(crc>>1)^(RP if crc&1 else 0)
    tbl.append(crc)

def crc_ref(data, init, xorout):
    crc=init
    for c in data:
        crc=(crc>>8)^tbl[(crc^c)&0xFF]
    return (reflect16(crc)^xorout)&0xFFFF

inits=[0x0000,0xFFFF,0x8005,0x1D0F,0x800D,0x89EC,0xB2AA,0x0840,0x8408,0x1234,0x55AA,0xAAAA,0x5555]
xors=[0x0000,0xFFFF,0x8005,0x1D0F,0xB001,0x0001,0x0F0F,0xF0F0]

scopes={'body':slice(2,None),'body4':slice(4,None),'full':slice(0,None)}
ok=False
for sname,sl in scopes.items():
    d1=r1[sl]; d2=r2[sl]
    for init in inits:
        for xo in xors:
            v1=crc_ref(d1,init,xo)
            if v1==h1le:
                v2=crc_ref(d2,init,xo)
                mark = 'XIAOMI-MATCH' if v2==h2le else ('xiaomi=%04x'%v2)
                print('HIT scope=%s init=%04x xorout=%04x stock=%04x %s'%(sname,init,xo,v1,mark))
                ok=True
if not ok:
    print('0x860F NOT confirmed as standard reflected CRC16 (no (init,xorout) reproduces header)')
# also report the init=0,xorout=0 raw values to see the distance
for sname,sl in scopes.items():
    print('scope=%s raw(stock)=%04x raw(xiaomi)=%04x target=%04x/%04x'%(
        sname, crc_ref(r1[sl],0,0), crc_ref(r2[sl],0,0), h1le, h2le))
