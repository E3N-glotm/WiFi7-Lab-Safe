import struct
import numpy as np
r1 = open('r1.bin','rb').read()
r2 = open('r2.bin','rb').read()
h1 = struct.unpack('<H', r1[:2])[0]
h2 = struct.unpack('<H', r2[:2])[0]

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

P0 = 0x860F
Rpolys = {'refl(0x860f)': refl16(P0), '0x860f': P0}

def build_ref_table(Rpoly):
    t=[]
    for b in range(256):
        crc=b
        for _ in range(8):
            crc=(crc>>1)^(Rpoly if (crc&1) else 0)
        t.append(crc)
    return np.array(t, dtype=np.uint16)

def states_all_init(data_bytes, T):
    st = np.arange(0x10000, dtype=np.uint16)
    for c in data_bytes:
        st = ((st>>8) ^ T[st & 0xFF ^ c]) & 0xFFFF
    return st

# L: reflected finalization, L[s] = 16 steps of (s>>1)^(Rpoly if s&1)
def build_L(Rpoly):
    M = np.zeros((16,16), dtype=np.uint8)
    for bit in range(16):
        v = 1<<bit
        x = v
        for _ in range(16):
            x = (x>>1) ^ (Rpoly if (x&1) else 0)
        for b in range(16):
            if (x>>b)&1:
                M[b,bit]=1
    return M

results=[]
for rname, Rpoly in Rpolys.items():
    T = build_ref_table(Rpoly)
    M = build_L(Rpoly)
    d1 = bytes(refl8(b) for b in r1)
    d2 = bytes(refl8(b) for b in r2)
    S1 = states_all_init(d1, T)
    S2 = states_all_init(d2, T)
    # outputs for all inits, xorout=0 : O_k = L[S_k]
    O1 = np.array([int(M @ ((S1[i]>>j)&1 for j in range(16)).__iter__().__class__ and 0) for i in range(1)] , dtype=np.uint16)  # placeholder
    # vectorized: build bit matrix of states
    B1 = np.zeros((16, 0x10000), dtype=np.uint8)
    B2 = np.zeros((16, 0x10000), dtype=np.uint8)
    for j in range(16):
        B1[j] = ((S1 >> j) & 1).astype(np.uint8)
        B2[j] = ((S2 >> j) & 1).astype(np.uint8)
    O1 = ((M @ B1) % 2).astype(np.uint8)
    O2 = ((M @ B2) % 2).astype(np.uint8)
    O1 = np.zeros(0x10000, dtype=np.uint16)
    O2 = np.zeros(0x10000, dtype=np.uint16)
    for j in range(16):
        O1 |= O1 | (O1[j*0x10000+j] * 0)  # noop
    # simpler: recompute O from bit matrix
    O1v = np.zeros(0x10000, dtype=np.uint16)
    O2v = np.zeros(0x10000, dtype=np.uint16)
    for j in range(16):
        O1v |= ((O1[j] & 1) << j)
        O2v |= ((O2[j] & 1) << j)
    # xorout effect: out(xorout) = O ^ L[xorout]  (linearity over GF(2), init independent)
    # find init such that out1(init, xo)=h1 and out2(init,xo)=h2 for the SAME xo.
    # out(init,xo) = O1v[init] ^ L[xo] = h1  =>  L[xo] = O1v[init]^h1
    #            and out2: O2v[init] ^ L[xo] = h2 => L[xo] = O2v[init]^h2
    # so need O1v[init]^h1 == O2v[init]^h2  =>  O1v[init]^O2v[init] == h1^h2
    need = h1 ^ h2
    diff = (O1v ^ O2v) & 0xFFFF
    inits = np.where(diff == need)[0]
    print('Rpoly=%s : %d init(s) consistent for some common xorout' % (rname, len(inits)))
    for i in inits[:8]:
        init=int(i)
        xo_bits = (O1v[init] ^ h1) & 0xFFFF
        # verify with scalar
        def rcrc_scalar(data, Rpoly, init, xorout):
            crc=init
            for c in data:
                crc=(crc>>8) ^ T_scalar[c ^ (crc & 0xFF)]
            return crc
        T_scalar = [0]*256
        for b in range(256):
            crc=b
            for _ in range(8):
                crc=(crc>>1)^(Rpoly if (crc&1) else 0)
            T_scalar[b]=crc
        a = rcrc_scalar(bytes(refl8(b) for b in r1), Rpoly, init, 0)
        a = a ^ 0
        # apply xorout via L
        def Lapply(v, Rpoly):
            x=v
            for _ in range(16):
                x=(x>>1)^(Rpoly if (x&1) else 0)
            return x
        v1 = a ^ 0
        out1 = v1 ^ Lapply(xo_bits, Rpoly)
        b2s = rcrc_scalar(bytes(refl8(b) for b in r2), Rpoly, init, 0)
        out2 = b2s ^ Lapply(xo_bits, Rpoly)
        print('   init=%04x xorout=%04x  stock=%04x(x%04x) xiaomi=%04x(x%04x)' %
              (init, xo_bits, out1, h1, out2, h2))
        if out1==h1 and out2==h2:
            print('   >>> CONFIRMED ALGORITHM: reflected input, Rpoly=%04x, init=%04x, xorout=%04x' % (Rpoly, init, xo_bits))
            results.append((Rpoly, init, xo_bits))
if not results:
    print('no confirmed (init,xorout) -> differential hit was coincidental; header checksum is NOT a plain reflected-CRC16 of this form.')
