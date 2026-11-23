import struct
r1 = open('r1.bin','rb').read()
r2 = open('r2.bin','rb').read()
h1 = struct.unpack('<H', r1[:2])[0]
h2 = struct.unpack('<H', r2[:2])[0]

def refl16(a):
    r=0
    for i in range(16):
        if a&(1<<i): r|=1<<(15-i)
    return r

# reflected (LSB-first) crc16 with a given reflected polynomial, init, xorout
def rcrc(data, Rpoly, init, xorout):
    crc=init
    for c in data:
        crc ^= c
        for _ in range(8):
            crc = (crc>>1) ^ (Rpoly if (crc&1) else 0)
    return (crc ^ xorout) & 0xFFFF

def rcrc_outrefl(data, Rpoly, init, xorout):
    return refl16(rcrc(data, Rpoly, init, xorout))

P0 = 0x860F
cands_Rpoly = {'P0': P0, 'refl(P0)': refl16(P0)}
scopes = {'from2':2, 'from4':4, 'full':0}

def refl8(b):
    r=0
    for i in range(8):
        if b&(1<<i): r|=1<<(7-i)
    return r

ok_any=False
# The crack7 hit was: reflect16( lsb-crc( reflected(input bytes), Rpoly=refl16(P0), init=0 ) ) ^ X
# so we must feed bit-reflected input. Test all (Rpoly, input-reflection) combos for consistency.
for rname, Rpoly in cands_Rpoly.items():
    for sname, s0 in scopes.items():
        d1 = r1[s0:]; d2 = r2[s0:]
        for inrefl in (False, True):
            if inrefl:
                dd1 = bytes(refl8(b) for b in d1)
                dd2 = bytes(refl8(b) for b in d2)
            else:
                dd1 = d1; dd2 = d2
            for outrefl in (False, True):
                v1 = rcrc(dd1, Rpoly, 0, 0)
                v2 = rcrc(dd2, Rpoly, 0, 0)
                if outrefl:
                    v1 = refl16(v1); v2 = refl16(v2)
                X = v1 ^ h1
                v2x = v2 ^ X
                tag = ('inrefl' if inrefl else 'plain') + '/' + ('outrefl' if outrefl else 'outplain')
                if v2x == h2:
                    print('*** ALGORITHM FOUND *** Rpoly=%s(%04x) scope=%s %s init=0 xorout=%04x' %
                          (rname, Rpoly, sname, tag, X))
                    ok_any=True
                else:
                    print('  Rpoly=%s scope=%s %s: init=0 X=%04x xiaomi=%04x (need %04x)' %
                          (rname, sname, tag, X, v2x, h2))

if ok_any:
    print('VERIFIED: checksum algorithm recovered.')
else:
    print('init=0 not consistent for any orientation; differential hit was coincidental.')

if ok_any:
    print('VERIFIED: checksum algorithm recovered.')
else:
    print('init=0 hypothesis did not verify. Trying full (init,xorout) solve...')
    # brute over init for Rpoly=P0 & refl(P0), scope from2, refout both, xorout=0
    for rname, Rpoly in cands_Rpoly.items():
        for sname,s0 in scopes.items():
            d1=r1[s0:]; d2=r2[s0:]
            for refout in (False,True):
                for init in range(0x10000):
                    if refout:
                        a=rcrc_outrefl(d1,Rpoly,init,0)
                    else:
                        a=rcrc(d1,Rpoly,init,0)
                    if a==h1:
                        b = rcrc_outrefl(d2,Rpoly,init,0) if refout else rcrc(d2,Rpoly,init,0)
                        if b==h2:
                            print('*** FOUND (init,xorout=0) *** Rpoly=%s scope=%s refout=%s init=%04x' %
                                  (rname,sname,refout,init))
                            ok_any=True
    if not ok_any:
        print('no (init) with xorout=0 works either. Algorithm is non-standard or scope differs.')
