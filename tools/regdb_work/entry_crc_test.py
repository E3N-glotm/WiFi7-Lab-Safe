import re, struct
from collections import defaultdict
r1 = open('r1.bin','rb').read()
r2 = open('r2.bin','rb').read()

def entries(data):
    out=[]
    for mm in re.finditer(rb'([A-Z]{2})\x00\1\x00', data[:4096]):
        e = mm.start()-3
        raw = data[e:e+16]
        out.append(dict(code=mm.group(1).decode(), off=e,
            f01=struct.unpack('<H',raw[0:2])[0], b2=raw[2],
            grp=struct.unpack('<H',raw[11:13])[0],
            ptr=struct.unpack('<H',raw[13:15])[0], fl=raw[15]))
    return out
E1 = {x['code']:x for x in entries(r1)}
E2 = {x['code']:x for x in entries(r2)}

# 1) is f01 a function of (grp, ptr, b2, fl)?
g = defaultdict(set)
for x in E1.values():
    g[(x['grp'],x['ptr'],x['b2'],x['fl'])].add(x['f01'])
vary = {k:v for k,v in g.items() if len(v)>1}
print('groups by (grp,ptr,b2,fl) with varying f01: %d / %d' % (len(vary), len(g)))
for k,v in list(vary.items())[:6]:
    print('  %s -> %s' % (str(k), [hex(t) for t in v]))

# 2) correlation: countries whose f01 CHANGED between stock and xiaomi
#    vs countries whose ptr/grp changed vs whose block bytes changed
changed_f01 = [c for c in E1 if c in E2 and E1[c]['f01']!=E2[c]['f01']]
changed_ptr = [c for c in E1 if c in E2 and (E1[c]['ptr'],E1[c]['grp'])!=(E2[c]['ptr'],E2[c]['grp'])]
print('changed f01:', changed_f01)
print('changed ptr/grp:', changed_ptr)

# 3) where are the high-region diffs, relative to ptr values?
diffs = [i for i in range(len(r1)) if r1[i]!=r2[i]]
hi = [i for i in diffs if i>=0x1000]
print('high diffs: %d bytes, range %x-%x' % (len(hi), min(hi), max(hi)))
# for each changed-f01 country, does its ptr region contain diffs? (guard ptr range)
for c in changed_f01:
    p = E1[c]['ptr']
    if p >= len(r1):
        print('%-3s ptr=%05x OUT-OF-FILE' % (c, p)); continue
    n = sum(1 for i in hi if p-64 <= i < p+1024)
    print('%-3s ptr=%05x diffs in [ptr-64,ptr+1024): %d' % (c, p, n))
# and for unchanged-f01 countries, how many diffs near their ptr (expect few)
unchanged = [c for c in E1 if c in E2 and E1[c]['f01']==E2[c]['f01']]
nn = 0; cnt=0
for c in unchanged:
    p = E1[c]['ptr']
    if p >= len(r1): continue
    cnt+=1
    nn += sum(1 for i in hi if p-64 <= i < p+1024)
print('UNCHANGED-f01 countries (ptr in-file): %d, diffs near their ptrs: %d' % (cnt, nn))

# 4) The high diff block: is it a single contiguous band region?
#    Show the diff histogram by 0x100 bucket to see structure
hist = defaultdict(int)
for i in hi:
    hist[i & 0xFFF00]+=1
print('high-diff buckets (0x1000-aligned):')
for k in sorted(hist):
    print('  %05x: %d bytes' % (k, hist[k]))
