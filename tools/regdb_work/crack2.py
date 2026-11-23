import struct
r1 = open('r1.bin','rb').read()
r2 = open('r2.bin','rb').read()
WANT1, WANT2 = 0xcea2, 0xe969

def crc16(data, poly, init, refin=False, refout=False, xorout=0):
    def reflect(b,n=16):
        r=0
        for i in range(n):
            if b&(1<<i): r|=1<<(n-1-i)
        return r
    crc=init
    for c in data:
        if refin: c=reflect(c,8)
        crc^=c<<8
        for _ in range(8):
            crc=((crc<<1)^poly)&0xffff if crc&0x8000 else (crc<<1)&0xffff
    if refout: crc=reflect(crc)
    return crc^xorout

polys = [0x1021,0x8005,0x0589,0x3d65,0x8bb7,0xa097,0x8408,0x1dcf,0x3b26,0x75f5,0x2f65,0xc867,0x8005]
def sum16(b): return sum(b)&0xffff
def xsum16(b):
    x=0
    for c in b: x^=c
    return x
def words16(b):
    s=0
    for i in range(0,len(b)&~1,2): s=(s+b[i]+(b[i+1]<<8))&0xffffffff
    return s&0xffff
def sum16_be(b):
    s=0
    for i in range(0,len(b)&~1,2): s=(s+(b[i]<<8)+b[i+1])&0xffffffff
    return s&0xffff

algos = {}
def add(name, fn): algos[name]=fn
add('sum16',sum16); add('xsum16',xsum16); add('words16le',words16); add('words16be',sum16_be)
for p in set(polys):
    for init in (0,0xffff,0x1d0f,0x800d):
        add('crc16_%04x_%04x'%(p,init), (lambda pp,ii: lambda d: crc16(d,pp,ii))(p,init))

# scopes: zero the header checksum field, then hash a range
def scopes(data):
    d = bytearray(data)
    out = {}
    out['[2:]'] = bytes(d[2:])
    out['[4:]'] = bytes(d[4:])
    out['[0:]z01']=bytes(d)  # caller zeroes
    z = bytearray(data); z[0]=z[1]=0
    out['zero[0:2] all']=bytes(z)
    out['zero[0:2] [4:]']=bytes(z[4:])
    out['zero[0:2] [2:]']=bytes(z[2:])
    return out

for data,want,tag in [(r1,WANT1,'stock'),(r2,WANT2,'xiaomi')]:
    found=False
    for sname, sdata in scopes(data).items():
        for aname, fn in algos.items():
            if fn(sdata)==want:
                print('MATCH %s scope=%s algo=%s =%04x'%(tag,sname,aname,want)); found=True
    if not found: print(tag,'no match among %d algos'%len(algos))
print('done')
