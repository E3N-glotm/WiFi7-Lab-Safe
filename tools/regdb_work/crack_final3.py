import struct
import numpy as np
r1 = open('r1.bin','rb').read()
r2 = open('r2.bin','rb').read()
h1 = struct.unpack('<H', r1[:2])[0]
h2 = struct.unpack('<H', r2[:2])[0]

def refl16(a):
    r=0
    for i in range(16):
        if a&(1<<i): r|=1<<(15-i)
    return r
def refl8(b):
    r=0
    for i in range(8):
        if b&(1<<i): r|=1<<(7-i)
    return r

REV16 = np.array([refl16(i) for i in range(0x10000)], dtype=np.uint16)

def rcrc_scalar(data, Rpoly, init, xorout):
    tbl=[0]*256
    for b in range(256):
        x=b
        for _ in range(8):
            x=(x>>1)^(Rpoly if (x&1) else 0)
        tbl[b]=x
    crc=init
    for c in data:
        crc=(crc>>8)^tbl[(crc&0xFF)^c]
    return refl16(crc) ^ xorout

P0=0x860F
z1 = bytearray(r1); z1[0]=0; z1[1]=0
z2 = bytearray(r2); z2[0]=0; z2[1]=0
d1 = bytes(refl8(b) for b in z1)
d2 = bytes(refl8(b) for b in z2)

found_any=False
for rname, Rpoly in (('refl(0x860f)=f061',refl16(P0)), ('0x860f', P0)):
    tbl=[0]*256
    for b in range(256):
        x=b
        for _ in range(8):
            x=(x>>1)^(Rpoly if (x&1) else 0)
        tbl[b]=x
    T=np.array(tbl,dtype=np.uint16)
    def states(data):
        st=np.arange(0x10000,dtype=np.uint16)
        for c in data:
            st=((st>>8)^T[st&0xFF^c])&0xFFFF
        return st
    S1=states(d1)
    S2=states(d2)
    O1v=REV16[S1]
    O2v=REV16[S2]
    need=h1^h2
    diff=(O1v^O2v)&0xFFFF
    inits=np.where(diff==need)[0]
    print('Rpoly=%s: %d init(s) satisfy diff condition' % (rname, len(inits)))
    for i in inits[:16]:
        init=int(i)
        xo=int((O1v[init]^h1)&0xFFFF)
        out1=rcrc_scalar(z1, Rpoly, init, xo)
        out2=rcrc_scalar(z2, Rpoly, init, xo)
        ok = (out1==h1 and out2==h2)
        if ok: found_any=True
        print('   init=%04x xo=%04x stock=%04x xiaomi=%04x %s' %
              (init, xo, out1, out2, '<<< CONFIRMED' if ok else ''))
if not found_any:
    print('STILL NO (init,xorout) -> 0x860f family definitively coincidental.')
