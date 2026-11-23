import struct
import numpy as np
r1 = open('r1.bin','rb').read()
r2 = open('r2.bin','rb').read()
h1 = struct.unpack('<H', r1[:2])[0]
h2 = struct.unpack('<H', r2[:2])[0]

def reflect16(a):
    r=0
    for i in range(16):
        if a&(1<<i): r|=1<<(15-i)
    return r

POLY = 0x860F
RP = reflect16(POLY)
tbl=[]
for b in range(256):
    crc=b
    for _ in range(8):
        crc=(crc>>1)^(RP if crc&1 else 0)
    tbl.append(crc)
T = np.array(tbl, dtype=np.uint16)
ROWS = np.arange(0x10000, dtype=np.intp)

def run_all_inits(data):
    st = np.arange(0x10000, dtype=np.uint16)   # one column per init value
    for b in data:
        st = ((st >> 8) ^ T[(st & 0xFF) ^ b]) & 0xFFFF
    out = np.array([reflect16(int(x)) for x in st], dtype=np.uint16)
    return out

import time
t0=time.time()
o1 = run_all_inits(r1[2:])
o2 = run_all_inits(r2[2:])
print('computed in %.1fs' % (time.time()-t0), flush=True)

# find inits such that out1==h1 and out2==h2 (xorout=0)
both = np.where((o1==h1)&(o2==h2))[0]
print('xorout=0  inits matching BOTH: %s' % ([hex(int(x)) for x in both[:32]]))

# xorout=0xFFFF case
both2 = np.where((o1==(h1^0xFFFF))&(o2==(h2^0xFFFF)))[0]
print('xorout=ffff inits matching BOTH: %s' % ([hex(int(x)) for x in both2[:32]]))

# how many inits match each file individually (sanity)
n1 = np.count_nonzero(o1==h1)
n2 = np.count_nonzero(o2==h2)
print('inits matching stock only: %d ; xiaomi only: %d' % (n1, n2))

# what xorout does init=0 imply?
xo = int(o1[0]) ^ h1
print('init=0 implies xorout=%04x ; check xiaomi: %04x (need %04x)' % (xo, int(o2[0])^xo, h2))
xo_ff = int(o1[0xFFFF]) ^ h1
print('init=ffff implies xorout=%04x ; check xiaomi: %04x' % (xo_ff, int(o2[0xFFFF])^xo_ff))
