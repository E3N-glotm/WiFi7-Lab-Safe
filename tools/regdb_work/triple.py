import struct
r1 = open('r1.bin','rb').read()
r2 = open('r2.bin','rb').read()
r3 = open('r3.bin','rb').read()
H1 = struct.unpack('<H', r1[:2])[0]
H2 = struct.unpack('<H', r2[:2])[0]
H3 = struct.unpack('<H', r3[:2])[0]
print('H1=%04x H2=%04x H3=%04x' % (H1,H2,H3))

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

# LSB-first crc with reflected poly Rpoly, init, xorout
def lsb_crc(data, Rpoly, init, xorout, inrefl):
    tbl=[0]*256
    for b in range(256):
        x=b
        for _ in range(8):
            x=(x>>1)^(Rpoly if (x&1) else 0)
        tbl[b]=x
    crc=init
    for c in data:
        if inrefl: c=refl8(c)
        crc=(crc>>8)^tbl[(crc&0xFF)^c]
    return (crc ^ xorout) & 0xFFFF

# MSB-first crc with poly P, init, xorout
def msb_crc(data, P, init, xorout):
    tbl=[0]*256
    for b in range(256):
        x=b<<8
        for _ in range(8):
            x=((x<<1)^P)&0xffff if x&0x8000 else (x<<1)&0xffff
        tbl[b]=x
    crc=init
    for c in data:
        crc=((crc<<8)&0xffff)^tbl[(crc>>8)^c]
    return (crc ^ xorout) & 0xFFFF

scopes = {
 's0'  : (0, None),
 'idx' : (4, 4+237*16),
 'band': (0x1000, None),
}

# candidates from crack7: (name, scope, kind, poly_reported, target_kind)
# kind 'refl' = LSB-first with Rpoly=refl16(poly) (or poly itself if it's already the refl one); input reflected
# We test BOTH the reported poly and its reflection as Rpoly.
cands = [
 ('s0-0x860f', 's0', 0x860f, True, True),   # inrefl, outrefl, LE target
 ('idx-0x75e1', 'idx', 0x75e1, True, False),
 ('idx-0xa4c1', 'idx', 0xa4c1, True, False),
 ('idx-0xa6be', 'idx', 0xa6be, True, False),
 ('band-0xb553', 'band', 0xb553, True, False),
]

def evaluate(scope, Rpoly, inrefl, outrefl, data):
    a0,a1 = scopes[scope]
    dd = data[a0:a1]
    v = lsb_crc(dd, Rpoly, 0, 0, inrefl)
    if outrefl: v = refl16(v)
    return v

print()
print('=== triple consistency: need (H^A) equal across r1,r2,r3 ===')
for name, scope, poly, inrefl, outrefl in cands:
    for rname, Rpoly in (('as-is', poly), ('refl16', refl16(poly))):
        A1 = evaluate(scope, Rpoly, inrefl, outrefl, r1)
        A2 = evaluate(scope, Rpoly, inrefl, outrefl, r2)
        A3 = evaluate(scope, Rpoly, inrefl, outrefl, r3)
        c1 = (H1^A1) & 0xFFFF
        c2 = (H2^A2) & 0xFFFF
        c3 = (H3^A3) & 0xFFFF
        status = ''
        if c1==c2==c3:
            status = '  <<< TRIPLE CONSISTENT (xorout-or-init constant = %04x)' % c1
        print('%-14s Rpoly=%04x(%s)  c123=%04x %04x %04x%s' % (name, Rpoly, rname, c1, c2, c3, status))

# Also solve r1->r3 differential candidates independently (fresh, may differ from r1->r2 set)
# Quick targeted: does any of the same polys satisfy r1/r3 differential at those scopes?
print()
print('=== r1 vs r3 differential check (same orientations) ===')
d3 = bytes(a^b for a,b in zip(r1,r3))
d3z = bytearray(d3); d3z[0]=0; d3z[1]=0
T3le = H1 ^ H3
T3be = refl16(H1 ^ H3)
# use the linear single-diff approach: for LSB orientation the linear operator on diff is:
# lsb_crc(x, R, 0,0,inrefl) is linear in x (GF2), so L(x1^x2)=L(x1)^L(x2)
# check L(d3) against targets
for name, scope, poly, inrefl, outrefl in cands:
    for rname, Rpoly in (('as-is', poly), ('refl16', refl16(poly))):
        L = evaluate(scope, Rpoly, inrefl, outrefl, bytes(d3z))
        m1 = ' T_LE' if L==T3le else ''
        m2 = ' T_BE' if L==T3be else ''
        print('%-14s Rpoly=%04x(%s) L(d13)=%04x%s%s' % (name, Rpoly, rname, L, m1, m2))
