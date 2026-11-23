import re, struct
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
            struct.unpack('<H',raw[9:11])[0],
            struct.unpack('<H',raw[11:13])[0],
            struct.unpack('<H',raw[13:15])[0], raw[15]))
    return out
E1 = get_entries(r1); E2 = get_entries(r2)

cands = {}
cands['sum_f01'] = (sum(x[1] for x in E1)&0xffff, sum(x[1] for x in E2)&0xffff)
cands['sum_b2']  = (sum(x[2] for x in E1)&0xffff, sum(x[2] for x in E2)&0xffff)
cands['sum_tag'] = (sum(x[3] for x in E1)&0xffff, sum(x[3] for x in E2)&0xffff)
cands['sum_grp'] = (sum(x[4] for x in E1)&0xffff, sum(x[4] for x in E2)&0xffff)
cands['sum_ptr'] = (sum(x[5] for x in E1)&0xffff, sum(x[5] for x in E2)&0xffff)
cands['sum_fl']  = (sum(x[6] for x in E1)&0xffff, sum(x[6] for x in E2)&0xffff)
cands['xor_f01'] = (lambda L: __import__('functools').reduce(lambda a,b:a^b, L))( [x[1] for x in E1] ), None
def xr(L):
    x=0
    for v in L: x^=v
    return x
cands['xor_f01'] = (xr([x[1] for x in E1]), xr([x[1] for x in E2]))
cands['xor_ptr'] = (xr([x[5] for x in E1]), xr([x[5] for x in E2]))
# index byte sums with header zeroed / not
for name, (a0,a1,b0,b1) in {
 'idx_zeroed': (4, 4+237*16, 4, 4+238*16),
 'idx_raw': (0, 4+237*16, 0, 4+238*16),
 'tail2': (2, len(r1), 2, len(r2)),
 'tail4': (4, len(r1), 4, len(r2)),
}.items():
    za = bytearray(r1); za[0]=za[1]=0
    zb = bytearray(r2); zb[0]=zb[1]=0
    if 'zeroed' in name:
        sa = sum(za[a0:a1])&0xffff; sb = sum(zb[b0:b1])&0xffff
    else:
        sa = sum(r1[a0:a1])&0xffff; sb = sum(r2[b0:b1])&0xffff
    cands['sum_'+name] = (sa, sb)

print('target: stock=%04x xiaomi=%04x' % (h1,h2))
for k,(a,b) in cands.items():
    m1 = '  <== stock' if a==h1 else ''
    m2 = '  <== xiaomi' if b==h2 else ''
    if m1 or m2:
        print('%-12s %04x %04x%s%s' % (k,a,b,m1,m2))
print('--- all candidates for manual check ---')
for k,(a,b) in cands.items():
    print('%-12s %04x %04x' % (k,a,b))

# also show the index-region head of both files
print('stock 000-020:', r1[0:0x20].hex())
print('xiaomi 000-020:', r2[0:0x20].hex())
# hypothesis: f01 of each entry == sum of that country's band-record power bytes?
# Check US: entry f01=ea. find US band records via pointer f5=0x4508 (zero).
# Instead test: f01 == (some function of b2, grp, ptr, fl)?
# US: f01=0xea b2=0x21 fl=2 ; GB: f01=0x6e b2=0x03 fl=3 ; DE: f01=0x27 b2=0x02 fl=1
# CN: f01=0x74 b2=0 fl=0 ; FR: f01=0x27 b2=0x02 fl=0
# DE and FR share f01=0x27 b2=0x02 but fl differs (1 vs 0) and grp/ptr differ.
# So f01 depends on (b2, something else). Let's list all entries with b2=2:
print('--- entries with b2==2 ---')
for x in E1:
    if x[2]==2:
        print('%-3s f01=%02x b2=%02x grp=%04x ptr=%04x fl=%d' % (x[0],x[1],x[2],x[4],x[5],x[6]))
