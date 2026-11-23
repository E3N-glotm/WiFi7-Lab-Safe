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

def rcrc_scalar(data, Rpoly, init):
    crc=init
    tbl=[0]*256
    for b in range(256):
        x=b
        for _ in range(8):
            x=(x>>1)^(Rpoly if (x&1) else 0)
        tbl[b]=x
    for c in data:
        crc=(crc>>8)^tbl[(crc&0xFF)^c]
    return crc

def L16(v, Rpoly):
    for _ in range(16):
        v=(v>>1)^(Rpoly if (v&1) else 0)
    return v

P0=0x860F
for rname, Rpoly in (('refl(0x860f)',refl16(P0)),('0x860f',P0)):
    # build table for vectorized all-init state
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
    S1=states(bytes(refl8(b) for b in r1))
    S2=states(bytes(refl8(b) for b in r2))
    # checksum field itself is excluded from the scope: zero header in both files
    z1 = bytearray(r1); z1[0]=0; z1[1]=0
    z2 = bytearray(r2); z2[0]=0; z2[1]=0
    S1=states(bytes(refl8(b) for b in z1))
    S2=states(bytes(refl8(b) for b in z2))
    # L as 16x16 GF(2) matrix
    M=np.zeros((16,16),dtype=np.uint8)
    for bit in range(16):
        v=1<<bit
        for _ in range(16):
            v=(v>>1)^(Rpoly if (v&1) else 0)
        for b in range(16):
            if (v>>b)&1: M[b,bit]=1
    B1=np.stack([((S1>>j)&1).astype(np.uint8) for j in range(16)])
    B2=np.stack([((S2>>j)&1).astype(np.uint8) for j in range(16)])
    O1b=((M@B1)%2)
    O2b=((M@B2)%2)
    O1v=np.zeros(0x10000,dtype=np.uint16)
    O2v=np.zeros(0x10000,dtype=np.uint16)
    for j in range(16):
        O1v|=((O1b[j]&1)<<j)
        O2v|=((O2b[j]&1)<<j)
    need=h1^h2
    diff=(O1v^O2v)&0xFFFF
    inits=np.where(diff==need)[0]
    print('Rpoly=%s(%04x): %d consistent init(s)' % (rname,Rpoly,len(inits)))
    for i in inits[:8]:
        init=int(i)
        xo=(O1v[init]^h1)&0xFFFF
        out1=rcrc_scalar(bytes(refl8(b) for b in r1),Rpoly,init)^L16(xo,Rpoly)
        out2=rcrc_scalar(bytes(refl8(b) for b in r2),Rpoly,init)^L16(xo,Rpoly)
        print('   init=%04x xo=%04x stock=%04x xiaomi=%04x  %s' %
              (init,xo,out1,out2, 'CONFIRMED' if (out1==h1 and out2==h2) else ''))
