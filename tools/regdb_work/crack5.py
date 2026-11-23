import re, struct
import numpy as np

r1 = open('r1.bin','rb').read()
r2 = open('r2.bin','rb').read()
h1 = struct.unpack('<H', r1[:2])[0]
h2 = struct.unpack('<H', r2[:2])[0]

def get_entries(data):
    out=[]
    for mm in re.finditer(rb'([A-Z]{2})\x00\1\x00', data[:4096]):
        e = mm.start()-3
        raw = data[e:e+16]
        out.append((mm.group(1).decode(),
            struct.unpack('<H',raw[0:2])[0], raw[2],
            struct.unpack('<H',raw[11:13])[0],
            struct.unpack('<H',raw[13:15])[0], raw[15]))
    return out
E1 = get_entries(r1); E2 = get_entries(r2)
m2 = {x[0]:x for x in E2}

# --- aggregate hypotheses on header checksum ---
def s16(v): return v & 0xffff
f01s1 = s16(sum(x[1] for x in E1))
f01s2 = s16(sum(x[1] for x in E2))
b2s1  = s16(sum(x[2] for x in E1)); b2s2 = s16(sum(x[2] for x in E2))
g1    = s16(sum(x[3] for x in E1)); g2   = s16(sum(x[3] for x in E2))
p1    = s16(sum(x[4] for x in E1)); p2   = s16(sum(x[4] for x in E2))
print('hdr stock=%04x xiaomi=%04x' % (h1,h2))
print('sum f01: %04x vs %04x' % (f01s1, f01s2))
print('sum b2 : %04x vs %04x' % (b2s1, b2s2))
print('sum grp: %04x vs %04x' % (g1, g2))
print('sum f5 : %04x vs %04x' % (p1, p2))
# xor variants
def xorv(vals):
    x=0
    for v in vals: x^=v
    return x
print('xor f01: %04x vs %04x' % (xorv([x[1] for x in E1]), xorv([x[1] for x in E2])))
# words16 over index region only
def words16(b):
    s=0
    for i in range(0,len(b)&~1,2): s=(s+b[i]+(b[i+1]<<8))&0xffffffff
    s=(s&0xffff)+(s>>16); s=(s&0xffff)+(s>>16)
    return s&0xffff
idx1 = r1[4:4+237*16]
idx2 = r2[4:4+238*16]
print('words16 idx: stock=%04x xiaomi=%04x (hdr %04x/%04x)' % (words16(idx1), words16(idx2), h1, h2))

# --- full polynomial brute force (CRC16 family, both orientations) ---
print('=== CRC16 full poly brute force ===')
scopes = {
 'full_z':  None,   # handled below with zeroed copy
 'tail2':   2,
 'tail4':   4,
 'idx':     (4, 4+237*16),
}
# zeroed-header copies
z1 = bytearray(r1); z1[0]=z1[1]=0
z2 = bytearray(r2); z2[0]=z2[1]=0
scope_bytes = {
 'full_z': (bytes(z1), bytes(z2)),
 'tail2' : (r1[2:], r2[2:]),
 'tail4' : (r1[4:], r2[4:]),
 'idx'   : (bytes(z1[4:4+237*16]), bytes(z2[4:4+238*16])),
}

POLYS = np.arange(0x10000, dtype=np.uint32)
inits = [0x0000, 0xFFFF, 0x1D0F, 0x800D, 0x8408, 0x0840, 0x89EC, 0xB2AA]

def crc_all_polys(data, polys, init):
    # vectorized over polynomials; data as bytes
    d = np.frombuffer(data, dtype=np.uint8)
    # precompute table for each poly: table[p, b]
    # table[p,b] = crc of byte b with poly p, init=0, normal orientation
    # compute: t[p,b] = (b<<8) then 8 shifts
    # do it stepwise: state[p,b] = b << 8
    state = (np.uint16(d[:1].astype(np.uint32)) << 8)  # not right shape; do generic
    # generic: for each byte, update crc array
    crc = np.full(len(polys), init, dtype=np.uint32)
    for byte in d:
        crc ^= (byte << 8)
        for _ in range(8):
            crc = np.where(crc & 0x8000, (crc << 1) ^ polys, crc << 1) & 0xFFFF
    return crc

# too slow per-byte loop in numpy? 24276 bytes * 8 shifts = 194k vector ops over 65536 -> ~ 194k*~200us = 40s per scope-init. heavy.
# Alternative: precompute per-poly byte tables via numpy broadcasting:
def build_table(polys):
    # table shape (65536, 256) uint16
    b = np.arange(256, dtype=np.uint32)
    t = (b[None,:] << 8).astype(np.uint32)
    for _ in range(8):
        t = np.where(t & 0x8000, (t << 1) ^ (polys[:,None]), t << 1) & 0xFFFF
    return t.astype(np.uint16)

T = build_table(POLYS)  # ~32MB
print('table built')

for sname, (d1, d2) in scope_bytes.items():
    for init in inits:
        crc1 = np.full(0x10000, init, dtype=np.uint32)
        crc2 = np.full(0x10000, init, dtype=np.uint32)
        for byte in d1:
            crc1 = T[(crc1 >> 8) ^ byte]  # gather: T rows indexed by (poly, byte-idx)
            crc2 = T[(crc2 >> 8) ^ byte]
        # NOTE: this treats both files with same byte stream length; d2 may differ in length (idx scope 238 entries).
        m1 = np.where(crc1 == h1)[0]
        if len(m1):
            print('STOCK HIT %s init=%04x polys=%s' % (sname, init, [hex(int(x)) for x in m1[:16]]))
        # d2 handled separately below

# separate pass for d2 (different length in 'idx')
for sname, (d1, d2) in scope_bytes.items():
    if d1 is d2 or len(d1)==len(d2) and d1==d2: continue
    for init in inits:
        crc2 = np.full(0x10000, init, dtype=np.uint32)
        for byte in d2:
            crc2 = T[(crc2 >> 8) ^ byte]
        m2 = np.where(crc2 == h2)[0]
        if len(m2):
            print('XIAOMI HIT %s init=%04x polys=%s' % (sname, init, [hex(int(x)) for x in m2[:16]]))
print('=== done brute force (normal orientation) ===')
