"""Pool record map under the GhostUnlock layout model.

Records: 16B from offset 0, [2:4]=ISO numeric country, [4:6]=pair id,
[6]=super6g, [7:9]=alpha2. Pool begins after the 0x1000 record table.
Goal: locate every 2402-2472 copy, the 00 record, and per-country plan links.
"""
import struct

FILES = ['r1.bin', 'r2.bin', 'r3.bin', 'net/giulia_kiwi.bin',
         'net/oplus_kiwi.bin', 'net/kiwi_nuwa_lfs.bin']

def records(d):
    out = {}
    for off in range(0, 0x1000, 16):
        ctry = struct.unpack_from('<H', d, off + 2)[0]
        a1 = d[off + 7: off + 9]
        a2 = d[off + 10: off + 12]
        printable = all(48 <= b <= 90 for b in a1 + a2)
        if printable and a1 == a2:
            out[a1.decode(errors='replace')] = dict(
                off=off, ctry=ctry, pair=struct.unpack_from('<H', d, off + 4)[0],
                super6g=d[off + 6], f01=struct.unpack_from('<H', d, off)[0],
                raw=d[off:off + 16].hex(' '))
    return out

def poolscan(d):
    recs = []
    off = 0x1000
    n = len(d)
    while off + 12 <= n:
        s, e, bw, fl, pwr = struct.unpack_from('<HHHBBBx'? if False else '<HHHBB', d, off)[:5] if False else (0,)*5
        s, e, bw, fl = struct.unpack_from('<HHH', d, off) and struct.unpack_from('<HHH', d, off)[0:3] + (struct.unpack_from('<H', d, off + 6)[0],)
        pwr = d[off + 8]
        # 12-byte band rule: <start><end><bw><pad16?>... real layout: s e bw ? pwr
        s2, e2, bw2 = struct.unpack_from('<HHH', d, off)
        w1 = struct.unpack_from('<H', d, off + 6)[0]
        p8, p9, p10 = d[off + 8], d[off + 9], d[off + 10]
        if (2400 <= s2 < 2500 or 4900 <= s2 < 8000) and 0 < e2 - s2 < 1600 and bw2 in (20, 40, 80, 160, 320, 2160, 1600) and p8 <= 60:
            recs.append(dict(off=off, s=s2, e=e2, bw=bw2, w1=w1, p8=p8, p9=p9, p10=p10))
            off += 12
        else:
            off += 1
    return recs

for f in FILES[:3]:
    d = open(f, 'rb').read()
    R = records(d)
    print('===', f, 'records', len(R))
    zero = R.get('00')
    print('  "00" record:', zero)
    for cc in ('US', 'CN', 'JP'):
        r = R.get(cc)
        print('  %s: off=%s pair=%s super6g=%s f01=%s' % (cc, hex(r['off']), r['pair'], hex(r['super6g']), hex(r['f01'])))
    P = poolscan(d)
    print('  pool rules:', len(P))
    for p in P:
        if p['s'] == 2402:
            print('    2.4G @%04x %d-%d bw=%d w1=%04x p8=%d p9=%d p10=%d' % (p['off'], p['s'], p['e'], p['bw'], p['w1'], p['p8'], p['p9'], p['p10']))
    for p in P:
        if p['s'] in (5735, 5725, 5745) or (5700 <= p['s'] <= 5800 and p['e'] > 5800):
            print('    5G-high @%04x %d-%d bw=%d w1=%04x p8=%d p9=%d p10=%d' % (p['off'], p['s'], p['e'], p['bw'], p['w1'], p['p8'], p['p9'], p['p10']))
    for p in P:
        if p['s'] == 5945 or p['s'] == 5925:
            print('    6G @%04x %d-%d bw=%d w1=%04x p8=%d p9=%d p10=%d' % (p['off'], p['s'], p['e'], p['bw'], p['w1'], p['p8'], p['p9'], p['p10']))
