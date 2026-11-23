"""What does channel 14 actually cost, and can 6 GHz come back with it?

The live AR test showed 2.4 GHz reaches only 2482 MHz, so ch14 (2484 MHz) sits
two megahertz outside the rendered range and stays disabled. Only 2G domains
with a dedicated channel-14 rule cover it. This lists every pair built from
such a domain together with its power ceiling and 6 GHz availability, so the
trade-off is explicit rather than guessed.
"""
import hosttables as H

ch14_domains = sorted(d for d, v in H.DOMAINS.items()
                      if any('CHAN_14' in r for r in v.get('rules', [])))
print('2G domains carrying a channel-14 rule:', ch14_domains)

print()
rows = []
for sym, p in sorted(H.PAIRS.items()):
    if p.get('dmn2') not in ch14_domains:
        continue
    rules = []
    for dmn in (p.get('dmn2'), p.get('dmn5')):
        for n in H.DOMAINS.get(dmn, {}).get('rules', []):
            if n in H.RULES:
                rules.append(H.RULES[n])
    if not rules:
        continue
    p24 = max((r['pwr'] for r in rules if 2400 <= r['start'] < 2500), default=0)
    p5 = max((r['pwr'] for r in rules if 4900 <= r['start'] < 5925), default=0)
    has6 = any(r['start'] >= 5925 for r in rules)
    rows.append((H.PAIR_IDS.get(sym, -1), sym, p24, p5, has6,
                 p.get('dmn2'), p.get('dmn5')))

rows.sort()
print('%-4s %-16s %-6s %-6s %-5s %-10s %s' %
      ('id', 'pair', 'p24', 'p5', '6G', '2g-domain', '5g-domain'))
for pid, sym, p24, p5, has6, d2, d5 in rows:
    print('%-4s %-16s %-6d %-6d %-5s %-10s %s' % (pid, sym, p24, p5, has6, d2, d5))

# Which alpha2 codes carry these pair ids in real dumps?
import struct
want = {r[0] for r in rows}
files = ['r1.bin', 'r2.bin', 'r3.bin', 'net/giulia_kiwi.bin',
         'net/oplus_kiwi.bin', 'net/kiwi_nuwa_lfs.bin']
print()
for f in files:
    d = open(f, 'rb').read()
    found = []
    for o in range(0, 0x1000, 16):
        a = d[o + 7:o + 9]
        if len(a) == 2 and all(48 <= b <= 90 for b in a) and a == d[o + 10:o + 12]:
            pid = struct.unpack_from('<H', d, o + 4)[0]
            if pid in want:
                found.append('%s(id=%d,s6=0x%02x)' % (a.decode(), pid, d[o + 6]))
    if found:
        print('%-26s %s' % (f, ' '.join(found)))
