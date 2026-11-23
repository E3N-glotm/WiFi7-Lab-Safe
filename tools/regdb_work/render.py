"""Render the exact iw-style regulatory rows a given reg_dmn_pair id produces.

The live self-managed table is this built-in render (proved by pair 234
matching the live US rows byte-for-byte), so this predicts what a record
carrying pair=<id> will show, before spending a device reload -- and gives the
row-by-row checklist to verify the reload against afterwards.
"""
import sys
import hosttables as H


def band_of(s):
    if 2400 <= s < 2500:
        return '2.4'
    if 4900 <= s < 5925:
        return '5'
    return '6'


def rows_for(pair_id):
    sym = next((s for s, i in H.PAIR_IDS.items() if i == pair_id and s in H.PAIRS), None)
    if not sym:
        print('pair id %d has no built-in pair row' % pair_id)
        return None, []
    p = H.PAIRS[sym]
    out = []
    for dmn in (p.get('dmn2'), p.get('dmn5')):
        d = H.DOMAINS.get(dmn, {})
        for n in d.get('rules', []):
            r = H.RULES.get(n)
            if r:
                out.append((band_of(r['start']), dmn, r))
    return sym, out


def show(title, pair_id):
    sym, rows = rows_for(pair_id)
    print('=== pair %d = %s (%s) ===' % (pair_id, sym, title))
    if not rows:
        return
    ctl = {d: H.DOMAINS.get(d, {}).get('ctl') for d in
           (H.PAIRS[sym].get('dmn2'), H.PAIRS[sym].get('dmn5'))}
    print('  domains: 2g=%s 5g=%s ctl=%s' %
          (H.PAIRS[sym].get('dmn2'), H.PAIRS[sym].get('dmn5'), ctl))
    for band, dmn, r in rows:
        flags = []
        f = r['flags']
        if 'RADAR' in f:
            flags.append('DFS')
        if 'NO_IR' in f or 'NO-IR' in f:
            flags.append('NO-IR')
        if 'NO_OUTDOOR' in f or 'INDOOR' in f:
            flags.append('INDOOR' if 'INDOOR' in f else 'NO-OUTDOOR')
        print('  %-3s (%5d - %5d @ %-4d), (%s, %2d) %s   [%s]' %
              (band, r['start'], r['end'], r['bw'], dmn, r['pwr'],
               ','.join(flags) or '-', r['flags']))


ids = [int(x, 0) for x in sys.argv[1:]] or [234, 116, 231]
for i in ids:
    show('candidate', i)
    print()
