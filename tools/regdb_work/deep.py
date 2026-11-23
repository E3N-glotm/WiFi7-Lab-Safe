import struct
r1 = open('r1.bin','rb').read()
r2 = open('r2.bin','rb').read()

def find_bytes(pat, data, cap=20):
    out=[]; i=data.find(pat)
    while i!=-1 and len(out)<cap:
        out.append(i); i=data.find(pat,i+1)
    return out

print('7105 LE16:', [hex(x) for x in find_bytes(struct.pack('<H',7105), r1)])
print('7105 BE16:', [hex(x) for x in find_bytes(struct.pack('>H',7105), r1)])
print('7105 LE32:', [hex(x) for x in find_bytes(struct.pack('<I',7105), r1)])
print('7105 BE32:', [hex(x) for x in find_bytes(struct.pack('>I',7105), r1)])
print('7105/5=1421 LE16:', [hex(x) for x in find_bytes(struct.pack('<H',1421), r1)])
print('2402/5=480 LE16:', [hex(x) for x in find_bytes(struct.pack('<H',480), r1)])

print('=== 6GHz region 0x2560-0x25f0 ===')
seg = r1[0x2560:0x25f0]
for i in range(0,len(seg),16):
    print('%5x  %s'%(0x2560+i, seg[i:i+16].hex(' ')))

print('=== 2.4GHz region 0x2010-0x20a0 ===')
seg = r1[0x2010:0x20a0]
for i in range(0,len(seg),16):
    print('%5x  %s'%(0x2010+i, seg[i:i+16].hex(' ')))

print('=== stock vs xiaomi diff ===')
diffs = [i for i in range(len(r1)) if r1[i]!=r2[i]]
print('total diff bytes:', len(diffs))
if diffs:
    ranges=[]; s=diffs[0]; p=diffs[0]
    for d in diffs[1:]:
        if d==p+1: p=d
        else: ranges.append((s,p)); s=d; p=d
    ranges.append((s,p))
    for a,b in ranges[:40]:
        print('%5x-%5x (%d) stock=%s xiaomi=%s'%(a,b,b-a+1,r1[a:b+1].hex(),r2[a:b+1].hex()))
