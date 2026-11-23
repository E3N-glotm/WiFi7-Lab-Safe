import struct
r1 = open('r1.bin','rb').read()
r2 = open('r2.bin','rb').read()
r3 = open('r3.bin','rb').read()
H = {1:struct.unpack('<H',r1[:2])[0], 2:struct.unpack('<H',r2[:2])[0], 3:struct.unpack('<H',r3[:2])[0]}

def wsum(data, start, base=1):
    s=0
    for i in range(start, len(data)):
        s = (s + (base+i)*data[i]) & 0xFFFF
    return s

def wsum16(data, start, base=0):
    # weighted sum of u16 words
    s=0
    for i in range(start, len(data)-1, 2):
        w = data[i] | (data[i+1]<<8)
        s = (s + (base+i//2)*w) & 0xFFFF
    return s

def wsum_be(data, start, base=1):
    s=0
    for i in range(start, len(data)):
        s = (s + (base+i)*(data[i]<<8)) & 0xFFFF
    return s

tests = {
 'ws_k_b0_s0': lambda d: wsum(d,0,0),
 'ws_k_b1_s0': lambda d: wsum(d,0,1),
 'ws_k_b2_s2': lambda d: wsum(d,2,0),
 'ws_k_b4_s4': lambda d: wsum(d,4,0),
 'ws16_s4': lambda d: wsum16(d,4,0),
 'ws16_s0': lambda d: wsum16(d,0,0),
 'ws_be_s0': lambda d: wsum_be(d,0,0),
 'ws_mod256x256': None,
}
for name, fn in tests.items():
    if fn is None: continue
    v = {k: fn(d) for k,d in ((1,r1),(2,r2),(3,r3))}
    # does v match header for all? or is (H - v) constant?
    c = {k: (H[k]-v[k])&0xFFFF for k in v}
    match = all(v[k]==H[k] for k in v)
    const = len(set(c.values()))==1
    tag = '  <<< MATCH' if match else ('  (constant offset %04x)'%list(c.values())[0] if const else '')
    print('%-14s %04x %04x %04x  hdr %04x %04x %04x%s' % (name, v[1],v[2],v[3], H[1],H[2],H[3], tag))

# also: maybe checksum = sum of f01 + sum of ptr + ... weighted per field index
import re
def fields(data):
    out=[]
    for mm in re.finditer(rb'([A-Z]{2})\x00\1\x00', data[:4096]):
        e=mm.start()-3
        out.append((e, struct.unpack('<H',data[e:e+2])[0], data[e+2],
                    struct.unpack('<H',data[e+11:e+13])[0],
                    struct.unpack('<H',data[e+13:e+15])[0], data[e+15]))
    return out
F={1:fields(r1),2:fields(r2),3:fields(r3)}
for name, idx in (('f01',1),('b2',2),('grp',3),('ptr',4),('fl',5)):
    vals={k:sum(x[idx] for x in F[k])&0xFFFF for k in (1,2,3)}
    c={k:(H[k]-vals[k])&0xFFFF for k in vals}
    print('fieldsum %-4s %04x %04x %04x  const-offset=%s' % (name, vals[1],vals[2],vals[3], len(set(c.values()))==1))
print('done')
