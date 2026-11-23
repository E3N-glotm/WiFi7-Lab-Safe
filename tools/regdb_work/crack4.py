import struct
r1 = open('r1.bin','rb').read()
r2 = open('r2.bin','rb').read()
n = len(r1)
h1 = struct.unpack('<H', r1[:2])[0]
h2 = struct.unpack('<H', r2[:2])[0]

# prefix sum mod 65536
def pref(b):
    p=[0]*(n+1)
    for i in range(n): p[i+1]=(p[i]+b[i])&0xffff
    return p
P1=pref(r1); P2=pref(r2)

# find all a<b with (P1[b]-P1[a])%M==h1 and (P2[b]-P2[a])%M==h2
M=0x10000
from collections import defaultdict
seen=defaultdict(list)
res=[]
for b in range(n,0,-1):
    # insert index b into map first, then query a<b
    key=(P1[b],P2[b]); seen[key].append(b)
# now for each a, target = (P1[a]+h1, P2[a]+h2); need b>a in map
# rebuild: iterate a from n-1 down, keep map of indices > a
seen=defaultdict(list)
hits=[]
for a in range(n,0,-1):
    t=((P1[a]+h1)&M,(P2[a]+h2)&M)
    bs=seen.get(t)
    if bs:
        for b in bs:
            hits.append((a,b))
    # now add index a
    seen[(P1[a],P2[a])].append(a)
print('SUM scope hits:', len(hits))
for a,b in hits[:40]:
    print('  [a=%d b=%d) len=%d  start=%04x end=%04x'%(a,b,b-a,a,b))

# XOR scope search: prefix xor
def prefx(b):
    p=[0]*(n+1)
    for i in range(n): p[i+1]=p[i]^b[i]
    return p
X1=prefx(r1); X2=prefx(r2)
seen=defaultdict(list); xhits=[]
for a in range(n,0,-1):
    # need b>a: X1[b]^X1[a]==h1 and X2[b]^X2[a]==h2  => X1[b]==X1[a]^h1, X2[b]==X2[a]^h2
    t=((X1[a]^h1)&0xff,(X2[a]^h2)&0xff)
    bs=seen.get(t)
    if bs:
        for b in bs: xhits.append((a,b))
    seen[(X1[a]&0xff,X2[a]&0xff)].append(a)
print('XOR scope hits:', len(xhits))
for a,b in xhits[:40]:
    print('  [a=%d b=%d) len=%d  start=%04x end=%04x'%(a,b,b-a,a,b))
