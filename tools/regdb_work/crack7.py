import struct, time
import numpy as np
r1 = open('r1.bin','rb').read()
r2 = open('r2.bin','rb').read()
h1le = struct.unpack('<H', r1[:2])[0]
h2le = struct.unpack('<H', r2[:2])[0]
h1be = struct.unpack('>H', r1[:2])[0]
h2be = struct.unpack('>H', r2[:2])[0]
T_LE = h1le ^ h2le
T_BE = h1be ^ h2be
print('h1le=%04x h2le=%04x h1be=%04x h2be=%04x T_LE=%04x T_BE=%04x' %
      (h1le,h2le,h1be,h2be,T_LE,T_BE), flush=True)

d = np.frombuffer(r1, dtype=np.uint8) ^ np.frombuffer(r2, dtype=np.uint8)

def reflect16_vec(a):
    r = np.zeros_like(a)
    for i in range(16):
        r |= ((a >> i) & 1) << (15-i)
    return r

P = np.arange(0x10000, dtype=np.uint32)
# D[p,x] = 8 MSB-first shifts starting from x
print('building D (MSB table) ...', flush=True)
t = np.arange(256, dtype=np.uint32)[None,:]
for _ in range(8):
    t = np.where(t & 0x8000, (t << 1) ^ P[:,None], t << 1) & 0xFFFF
D = t.astype(np.uint16)

def reflect16(a):
    r = np.zeros_like(a)
    for i in range(16):
        r |= ((a >> i) & 1) << (15-i)
    return r
RP = reflect16(P.astype(np.uint16)).astype(np.uint32)
# RL[p,x] = 8 LSB-first (reflected) steps starting from x
print('building RL (reflected table) ...', flush=True)
t = np.arange(256, dtype=np.uint32)[None,:]
for _ in range(8):
    t = (t >> 1) ^ np.where(t & 1, RP[:,None], 0)
RL = t.astype(np.uint16)

ROWS = np.arange(0x10000, dtype=np.intp)

def process_normal(seq):
    # crc' = (crc<<8) ^ D[(crc>>8) ^ b]
    st = np.zeros(0x10000, dtype=np.uint16)
    for b in seq:
        st = (((st & 0xFF) << 8) ^ D[ROWS, (st >> 8) ^ b]) & 0xFFFF
    return st

def process_reflected(seq):
    # crc' = (crc>>8) ^ RL[(crc&0xFF) ^ b]
    st = np.zeros(0x10000, dtype=np.uint16)
    for b in seq:
        st = ((st >> 8) ^ RL[ROWS, (st & 0xFF) ^ b]) & 0xFFFF
    return st

def reflect8(b):
    r=0
    for i in range(8):
        if b&(1<<i): r|=1<<(7-i)
    return r

scopes = {
 's0'  : slice(0, None),
 'idx' : slice(4, 4+237*16),
 'band': slice(0x1000, None),
}

t_all = time.time()
for name, sl in scopes.items():
    seq = d[sl]
    if name == 's0':
        seq = seq.copy()
        seq[0]=0; seq[1]=0
    t0=time.time()
    st = process_normal(seq)
    hit = []
    for tgt, tag in ((T_LE,'LE'),(T_BE,'BE')):
        w = np.where(st == tgt)[0]
        if len(w): hit.append((tag, [hex(int(x)) for x in w[:16]]))
        w = np.where(reflect16_vec(st) == tgt)[0]
        if len(w): hit.append((tag+'+refl', [hex(int(x)) for x in w[:16]]))
    seq2 = np.array([reflect8(int(b)) for b in seq], dtype=np.uint8)
    st2 = process_reflected(seq2)
    for tgt, tag in ((T_LE,'LE'),(T_BE,'BE')):
        w = np.where(st2 == tgt)[0]
        if len(w): hit.append((tag+'+inrefl', [hex(int(x)) for x in w[:16]]))
        w = np.where(reflect16_vec(st2) == tgt)[0]
        if len(w): hit.append((tag+'+inrefl+refl', [hex(int(x)) for x in w[:16]]))
    dt = time.time()-t0
    if hit:
        print('  [%s] %.1fs HITS: %s' % (name, dt, hit), flush=True)
    else:
        print('  [%s] %.1fs no hit' % (name, dt), flush=True)
print('total %.1fs' % (time.time()-t_all), flush=True)
