"""Rank built-in pairs by per-channel coverage, mirroring what iw enables.

A channel is enabled iff some rendered rule range contains its centre and the
rule carries no restriction flag; the live AR test matched this model exactly
(the nine disabled channels were precisely the gaps between rendered ranges).
The user's "all channels enabled" target is therefore a coverage question:
which pair covers 14 + 28 + 60 channels. This enumerates it offline.
"""
import hosttables as H

CH24 = [(2412 + 5 * i, i + 1) for i in range(13)] + [(2484, 14)]
CH5 = ([(5180 + 5 * i, 36 + i) for i in range(12)] +
       [(5500 + 5 * i, 100 + i) for i in range(20)] +
       [(5745 + 5 * i, 149 + i) for i in range(20)])
CH6 = [(5955 + 5 * i, 1 + 4 * i) for i in range(59)] + \
      [(7115, 233)] if False else [(5955 + 5 * i, 1 + 4 * i) for i in range(59)]


def enabled_channels(rows):
    out = {'2.4': 0, '5': 0, '6': 0}
    detail = {'2.4': [], '5': [], '6': []}
    for band, chans in (('2.4', CH24), ('5', CH5), ('6', CH6)):
        for f, num in chans:
            for r in rows:
                if r['start'] <= f <= r['end']:
                    fl = r['flags']
                    if 'RADAR' in fl or 'NO_IR' in fl or 'NO-IR' in fl:
                        continue  # still enabled in iw, but flagged
                    out[band] += 1
                    detail[band].append(num)
                    break
    return out, detail


def rows_of(pair_sym):
    p = H.PAIRS[pair_sym]
    rows = []
    for dmn in (p.get('dmn2'), p.get('dmn5')):
        for n in H.DOMAINS.get(dmn, {}).get('rules', []):
            if n in H.RULES:
                rows.append(H.RULES[n])
    return rows


best = []
for sym in sorted(H.PAIRS):
    rows = rows_of(sym)
    if not rows:
        continue
    cov, det = enabled_channels(rows)
    total = cov['2.4'] + cov['5'] + cov['6']
    maxp = max((r['pwr'] for r in rows), default=0)
    best.append((cov['2.4'] == 14, total, sym, cov, maxp))

best.sort(key=lambda t: (not t[0], -t[1]))
print('target = 14/28/60 (iw channel counts on this PHY)')
print('\ncandidates with all 14 x 2.4 GHz channels:')
for ch14, total, sym, cov, maxp in best:
    if ch14:
        print('  %-16s id=%-4s 2.4=%-3d 5=%-3d 6=%-3d max=%d' %
              (sym, H.PAIR_IDS.get(sym), cov['2.4'], cov['5'], cov['6'], maxp))
print('\ntop coverage overall:')
for ch14, total, sym, cov, maxp in best[:10]:
    print('  %-16s id=%-4s 2.4=%-3d 5=%-3d 6=%-3d total=%-3d max=%d' %
          (sym, H.PAIR_IDS.get(sym), cov['2.4'], cov['5'], cov['6'], total, maxp))

for probe in (231, 234, 116):
    sym = next((s for s, i in H.PAIR_IDS.items() if i == probe and s in H.PAIRS), None)
    if not sym:
        continue
    cov, det = enabled_channels(rows_of(sym))
    print('\nreference pair %d (%s): 2.4=%d 5=%d 6=%d  missing24=%s' %
          (probe, sym, cov['2.4'], cov['5'], cov['6'],
           [n for _, n in CH24 if n not in det['2.4']]))
