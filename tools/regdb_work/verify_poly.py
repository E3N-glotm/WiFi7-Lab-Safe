import struct
import numpy as np
r1 = open('r1.bin','rb').read()
r2 = open('r2.bin','rb').read()
h1le = struct.unpack('<H', r1[:2])[0]   # cea2
h2le = struct.unpack('<H', r2[:2])[0]   # e969

def reflect16(a):
    r=0
    for i in range(16):
        if a&(1<<i): r|=1<<(15-i)
    return r
def reflect8(b):
    r=0
    for i in range(8):
        if b&(1<<i): r|=1<<(7-i)
    return r

def crc16(data, poly, init, refin, refout, xorout):
    crc=init
    for c in data:
        if refin: c=reflect8(c)
        if refin:
            crc = (crc >> 8) ^ table_ref[c ^ (crc & 0xFF)]
        else:
            crc = ((crc << 8) & 0xFFFF) ^ table_norm[(crc >> 8) ^ c]
    if refout: crc = reflect16(crc)
    return crc ^ xorout

def build_norm(poly):
    t=[]
    for b in range(256):
        crc=b<<8
        for _ in range(8):
            crc=((crc<<1)^poly)&0xffff if crc&0x8000 else (crc<<1)&0xffff
        t.append(crc)
    return t
def build_ref(poly):
    rp=reflect16(poly)
    t=[]
    for b in range(256):
        crc=b
        for _ in range(8):
            crc=(crc>>1)^(rp if crc&1 else 0)
        t.append(crc)
    return t

cand_polys = [0x860F]
inits = [0x0000,0xFFFF,0x8005,0x1D0F,0x800D,0x89EC,0xB2AA,0x0840,0x8408]
xors  = [0x0000,0xFFFF,0x8005,0x1D0F,0xB001]

# scope options
scopes = {
 'full': 0,
 'from2': 2,
 'from4': 4,
}

found=False
for poly in cand_polys:
    table_norm=build_norm(poly); table_ref=build_ref(poly)
    for sname,s0 in scopes.items():
        d1=r1[s0:]; d2=r2[s0:]
        for refin in (True,False):
            for refout in (True,False):
                for init in inits:
                    v1=crc16(d1,poly,init,refin,refout,0)
                    # find xorout that makes v1==h1le
                    xo=v1^h1le
                    v2=crc16(d2,poly,init,refin,refout,xo)
                    if v2==h2le and xo in xors:
                        print('VALID poly=%04x scope=%s refin=%s refout=%s init=%04x xorout=%04x -> stock=%04x xiaomi=%04x'%(
                            poly,sname,refin,refout,init,xo,h1le,h2le))
                        found=True
                    elif v1==h1le and xo==0:
                        print('  partial (stock matches, xorout=0): poly=%04x scope=%s refin=%s refout=%s init=%04x v2=%04x'%(
                            poly,sname,refin,refout,init,v2))
if not found:
    print('candidate 0x860F did NOT validate with common (init,xorout) over these scopes')
