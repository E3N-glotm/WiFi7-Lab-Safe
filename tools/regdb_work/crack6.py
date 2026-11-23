import struct, time
import numpy as np
r1 = open('r1.bin','rb').read()
r2 = open('r2.bin','rb').read()
h1 = struct.unpack('<H', r1[:2])[0]
h2 = struct.unpack('<H', r2[:2])[0]
target = h1 ^ h2
print('h1=%04x h2=%04x target=%04x len=%d' % (h1,h2,target,len(r1)))

d = np.frombuffer(r1, dtype=np.uint8).astype(np.uint16) ^ np.frombuffer(r2, dtype=np.uint8).astype(np.uint16)
d = d.astype(np.uint8)
d[0]=0; d[1]=0   # exclude the checksum field itself

def reflect8(b):
    r=0
    for i in range(8):
        if b&(1<<i): r|=1<<(7-i)
    return r
def reflect16(a):
    # vectorized bit-reverse 16
    r = np.zeros_like(a)
    for i in range(16):
        r |= ((a >> i) & 1) << (15-i)
    return r

POLY = np.arange(0x10000, dtype=np.uint32)

# Normal (MSB-first) table: N[p, b] = result of processing byte b with poly p, init 0
print('building normal table ...', flush=True)
t = (np.arange(256, dtype=np.uint32)[None,:] << 8)
for _ in range(8):
    t = np.where(t & 0x8000, (t << 1) ^ POLY[:,None], t << 1) & 0xFFFF
N = t.astype(np.uint16)

# Reflected (LSB-first) table with reflected polys:
# R[p, b]: crc=b; 8x: crc = (crc>>1) ^ (refpoly[p] if crc&1 else 0)
def reflect16_vec(a):
    r = np.zeros_like(a)
    for i in range(16):
        r |= ((a >> i) & 1) << (15-i)
    return r
RP = reflect16_vec(POLY & 0xFFFF)
print('building reflected table ...', flush=True)
t2 = np.arange(256, dtype=np.uint32)[None,:]
for _ in range(8):
    t2 = (t2 >> 1) ^ np.where(t2 & 1, RP[:,None], 0)
R = (t2 & 0xFFFF).astype(np.uint16)

ROWS = np.arange(0x10000)

scopes = {
 's0'  : slice(0, None),
 's2'  : slice(2, None),
 's4'  : slice(4, None),
 'idx' : slice(4, 4+237*16),
 'band': slice(0x1000, None),
}

def run(name, seq):
    t0=time.time()
    seq = np.frombuffer(seq, dtype=np.uint8)
    crc = np.zeros(0x10000, dtype=np.uint32)
    for b in seq:
        crc = N[ROWS, (crc >> 8) ^ b]
    hit_n = [int(x) for x in np.where((crc & 0xFFFF)==target)[0]]
    cr = np.zeros(0x10000, dtype=np.uint32)
    for b in seq:
        cr = (cr >> 1) ^ R[ROWS, (cr ^ b) & 0xFF]
        cr &= 0xFFFF
    hit_r = [int(x) for x in np.where((cr & 0xFFFF)==target)[0]]
    dt = time.time()-t0
    if hit_n or hit_r:
        print('  [%s] %.1fs  normal=%s reflected=%s' % (name, dt,
            [hex(x) for x in hit_n[:16]], [hex(x) for x in hit_r[:16]]), flush=True)
    else:
        print('  [%s] %.1fs  no hit' % (name, dt), flush=True)

for name, sl in scopes.items():
    run(name, bytes(d[sl]))
print('done', flush=True)
