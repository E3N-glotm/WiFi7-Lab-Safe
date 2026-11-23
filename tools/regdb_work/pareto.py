"""Enumerate every host built-in reg_dmn_pair and score it against the goal.

Goal (user requirement, restated in engine terms): a country-00 record whose
pair/super6g selectors render, from the host built-in tables, a table that is
  * power ceiling >= US everywhere,
  * 5 GHz upper band (5725+) at CN's ceiling,
  * no NO-IR anywhere,
  * widest channel coverage (2.4 GHz ch14, all 5 GHz UNII, 6 GHz).

Because the live iw table is rendered from these built-in tables (proven in
the previous round: pair 234 -> the exact live US rows), the search is fully
offline and any hit is immediately actionable: it is a pair id to write into
record [4:6], not a new rule set to invent.
"""
import itertools
import hosttables as H


def rules_of(dmn):
    d = H.DOMAINS.get(dmn)
    if not d:
        return []
    return [H.RULES[n] for n in d.get('rules', []) if n in H.RULES]


def render(pair_sym):
    p = H.PAIRS[pair_sym]
    return rules_of(p.get('dmn2')) + rules_of(p.get('dmn5'))


def score(rows):
    if not rows:
        return None
    out = dict(rows=len(rows), pwr_max=0, pwr_24=0, pwr_5hi=0, no_ir=0,
               cov_24=set(), cov_5=set(), has6=False, dfs=0)
    for r in rows:
        out['pwr_max'] = max(out['pwr_max'], r['pwr'])
        f = r['flags']
        if 'NO_IR' in f or 'NO-IR' in f:
            out['no_ir'] += 1
        if 'RADAR' in f:
            out['dfs'] += 1
        s, e = r['start'], r['end']
        if 2400 <= s < 2500:
            out['pwr_24'] = max(out['pwr_24'], r['pwr'])
            out['cov_24'].add((s, e))
        elif 4900 <= s < 5925:
            out['cov_5'].add((s, e))
            if s >= 5700:
                out['pwr_5hi'] = max(out['pwr_5hi'], r['pwr'])
        elif s >= 5925:
            out['has6'] = True
    return out


ref_us = score(render('FCC15_FCCA'))
ref_cn = score(render('APL14_CHNA'))
print('reference US (pair 234):', {k: v for k, v in ref_us.items()
                                   if not isinstance(v, set)})
print('   cov24', sorted(ref_us['cov_24']), 'cov5', sorted(ref_us['cov_5']))
print('reference CN (pair 116):', {k: v for k, v in ref_cn.items()
                                   if not isinstance(v, set)})
print('   cov24', sorted(ref_cn['cov_24']), 'cov5', sorted(ref_cn['cov_5']))

rows = []
for sym in sorted(H.PAIRS):
    s = score(render(sym))
    if not s:
        continue
    # goal proxy: beat-or-match US power, reach CN's high-band power, no NO-IR,
    # widest coverage. Ranked by a lexicographic key so ties break sensibly.
    want5hi = max(ref_us['pwr_5hi'], ref_cn['pwr_5hi'])
    key = (
        0 if s['no_ir'] == 0 else 1,
        -(1 if s['pwr_24'] >= ref_us['pwr_24'] else 0),
        -(1 if s['pwr_5hi'] >= want5hi else 0),
        -len(s['cov_24']) - len(s['cov_5']),
        -(1 if s['has6'] else 0),
        -s['pwr_max'],
    )
    rows.append((key, sym, s))

rows.sort()
print('\n=== best pair candidates (offline, host built-in) ===')
for key, sym, s in rows[:14]:
    print('%-16s id=%-4s rows=%-3d pwr24=%-3d pwr5hi=%-3d max=%-3d noIR=%d '
          'dfs=%-2d 6G=%s cov24=%d cov5=%d' %
          (sym, H.PAIR_IDS.get(sym), s['rows'], s['pwr_24'], s['pwr_5hi'],
           s['pwr_max'], s['no_ir'], s['dfs'], s['has6'],
           len(s['cov_24']), len(s['cov_5'])))
print('\nexact goal match (noIR=0, pwr24>=US, pwr5hi>=CN, 6G=yes):')
hits = [sym for _, sym, s in rows
        if s['no_ir'] == 0 and s['pwr_24'] >= ref_us['pwr_24']
        and s['pwr_5hi'] >= max(ref_us['pwr_5hi'], ref_cn['pwr_5hi'])
        and s['has6']]
print(hits if hits else 'NONE -> fall back to 00->US + WCNSS keys for NO-IR')
