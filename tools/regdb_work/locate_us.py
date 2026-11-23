import re, struct
r1 = open('r1.bin','rb').read()

# index position (0-based) per country, entries at 4 + i*16
pos = {}
for mm in re.finditer(rb'([A-Z]{2})\x00\1\x00', r1[:4096]):
    e = mm.start()-3
    pos[mm.group(1).decode()] = (e-4)//16

# known 2.4G EIRP limits (dBm) for calibration anchors
known = {'US':30, 'DE':20, 'FR':20, 'GB':20, 'CN':20, 'JP':20, 'AX':20}

best = None
for rec in range(12, 19):
    for base in range(0x2020, 0x2048):
        ok = True
        for cc, lim in known.items():
            if cc not in pos: continue
            off = base + pos[cc]*rec
            if off+11 >= len(r1): ok=False; break
            pwr = r1[off+10]
            if pwr != lim: ok=False; break
        if ok:
            print('CANDIDATE rec=%d base=%04x' % (rec, base))
            best=(rec,base)
            # show a few
            for cc in known:
                if cc in pos:
                    off = base + pos[cc]*rec
                    print('  %s pos=%d off=%04x pwr=%d start=%d end=%d span=%d' % (
                        cc, pos[cc], off, r1[off+10],
                        struct.unpack('<H', r1[off+2:off+4])[0],
                        struct.unpack('<H', r1[off+4:off+6])[0],
                        struct.unpack('<H', r1[off+6:off+8])[0]))
if not best:
    # relax: require US + GB + CN match, count how many others match
    print('no perfect candidate; scoring partial...')
    scored=[]
    for rec in range(12, 19):
        for base in range(0x2020, 0x2048):
            hit=0; tot=0
            for cc, lim in known.items():
                if cc not in pos: continue
                off = base + pos[cc]*rec
                if off+11 >= len(r1): continue
                tot+=1
                if r1[off+10]==lim: hit+=1
            if hit>=4:
                scored.append((hit,tot,rec,base))
    for s in sorted(scored, reverse=True)[:10]:
        print('  partial hit=%d/%d rec=%d base=%04x' % s)
