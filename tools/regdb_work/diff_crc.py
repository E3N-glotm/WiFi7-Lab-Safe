import struct
r1 = open('r1.bin','rb').read()
r2 = open('r2.bin','rb').read()
n = len(r1)
CH = [i for i in range(n) if r1[i]!=r2[i]]

# header checksum candidates: bytes0-1 as u16 LE
h1 = struct.unpack('<H', r1[:2])[0]
h2 = struct.unpack('<H', r2[:2])[0]
print('hdr stock=%04x xiaomi=%04x'%(h1,h2))
delta_sum_target = (h2-h1)&0xffff
delta_xor_target = h2^h1
print('delta_sum_target=%04x  delta_xor_target=%04x'%(delta_sum_target, delta_xor_target))

# scope list: (name, start, end)
idx_end = 4 + 237*16
scopes = [
 ('whole[4:]', 4, n),
 ('whole[2:]', 2, n),
 ('whole[0:]', 0, n),
 ('idx[4:end]', 4, idx_end),
 ('idx[0:end]', 0, idx_end),
 ('band[0x1000:]', 0x1000, n),
 ('band[0x2000:]', 0x2000, n),
 ('idxonly[4:0x1000]', 4, 0x1000),
]

def s_delta(a,b,i0,i1):
    return sum(b[i]-a[i] for i in range(i0,i1) if a[i]!=b[i]) & 0xffff
def x_delta(a,b,i0,i1):
    x=0
    for i in range(i0,i1):
        if a[i]!=b[i]: x^=(a[i]^b[i])
    return x

print('--- differential: which scope reproduces the checksum delta? ---')
for name,i0,i1 in scopes:
    sd = s_delta(r1,r2,i0,i1)
    xd = x_delta(r1,r2,i0,i1)
    mark_s = ' <== SUM' if sd==delta_sum_target else ''
    mark_x = ' <== XOR' if xd==delta_xor_target else ''
    print('%-18s sum_delta=%04x xor_delta=%04x%s%s'%(name,sd,xd,mark_s,mark_x))

# Also: maybe checksum = (sum16 of region) directly. Verify by recomputing
# full sum16 of each scope for BOTH files and checking equality to header.
def sum16(a,i0,i1): return sum(a[i] for i in range(i0,i1))&0xffff
def xsum16(a,i0,i1):
    x=0
    for i in range(i0,i1): x^=a[i]
    return x
print('--- direct recompute (does sum/xor of region == header?) ---')
for name,i0,i1 in scopes:
    s1=sum16(r1,i0,i1); x1=xsum16(r1,i0,i1)
    ok_s1 = s1==h1; ok_x1 = x1==h1
    if ok_s1 or ok_x1:
        print('%-18s sum16=%04x xsum16=%04x hdr=%04x  SUM=%s XOR=%s'%(name,s1,x1,h1,ok_s1,ok_x1))
print('done diff')
