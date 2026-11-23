import re, struct
r1 = open('r1.bin','rb').read()
r2 = open('r2.bin','rb').read()

def entries(data):
    out=[]
    for mm in re.finditer(rb'([A-Z]{2})\x00\1\x00', data[:4096]):
        e = mm.start()-3
        code = mm.group(1).decode()
        raw = data[e:e+16]
        f01 = struct.unpack('<H', raw[0:2])[0]
        b2 = raw[2]
        tag = struct.unpack('<H', raw[9:11])[0]
        grp = struct.unpack('<H', raw[11:13])[0]
        ptr = struct.unpack('<H', raw[13:15])[0]
        out.append((e, code, f01, b2, tag, grp, ptr, raw[15]))
    return out

E1 = entries(r1); E2 = entries(r2)
print('entries:', len(E1), len(E2))
# map by code
m1 = {x[1]:x for x in E1}
m2 = {x[1]:x for x in E2}

# group stock by (grp, ptr): does f01 vary within group?
from collections import defaultdict
g = defaultdict(list)
for e in E1:
    g[(e[5], e[6])].append(e)
varied = 0
for k, v in g.items():
    f01s = set(x[2] for x in v)
    if len(f01s) > 1:
        varied += 1
        if varied <= 8:
            print('VARY f01 within (grp,ptr)=%s : %s' % (str(k), [(x[1], hex(x[2])) for x in v[:6]]))
print('groups with varying f01:', varied, 'of', len(g))

# Now: which entries differ between stock and xiaomi, field by field
print()
print('=== per-entry field diffs (stock vs xiaomi) ===')
ndiff = 0
for e in E1:
    code = e[1]
    f = m2.get(code)
    if not f: continue
    diffs = []
    if e[2]!=f[2]: diffs.append('f01 %x->%x'%(e[2],f[2]))
    if e[3]!=f[3]: diffs.append('b2 %d->%d'%(e[3],f[3]))
    if e[4]!=f[4]: diffs.append('tag %x->%x'%(e[4],f[4]))
    if e[5]!=f[5]: diffs.append('grp %x->%x'%(e[5],f[5]))
    if e[6]!=f[6]: diffs.append('ptr %x->%x'%(e[6],f[6]))
    if e[7]!=f[7]: diffs.append('tail %d->%d'%(e[7],f[7]))
    if diffs:
        ndiff += 1
        print('%-3s @%5d  %s' % (code, e[0], ', '.join(diffs)))
print('entries with field diffs:', ndiff)
