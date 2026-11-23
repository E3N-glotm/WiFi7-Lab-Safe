import struct
for n in ['r1.bin', 'r2.bin', 'r3.bin']:
    d = open(n, 'rb').read()
    print(n, 'len', len(d), 'head', d[:16].hex(' '))
    cnt = 0
    for i in range(0x2032, 0x2f6a, 12):
        s, e, bw, fl, p = struct.unpack('<HHHHB', d[i:i + 9])
        if 2400 <= s <= 7200 and s < e <= 7200 and bw in (5, 10, 20, 40, 80, 160, 320, 2160) and p <= 63:
            cnt += 1
    print('   plausible 12B records in 0x2032..0x2f69:', cnt)
    # where does the record region end?
    last = None
    for i in range(0x2000, len(d) - 12, 2):
        s, e, bw, fl, p = struct.unpack('<HHHHB', d[i:i + 9])
        if 2400 <= s <= 7200 and s < e <= 7200 and bw in (5, 10, 20, 40, 80, 160, 320, 2160) and p <= 63:
            last = i
    print('   last plausible record offset:', hex(last) if last else None)
