"""Parse every conditional g_all_countries[] table and pick the one matching
the device.

reg_db.c carries several country tables under #if blocks (database revisions),
so the first match is not necessarily the one compiled into this firmware.
The live readback decides: on this device `force-country-code AR` renders
APL17_ETSIC (36 dBm upper 5 GHz), while the first table in the file maps AR to
APL16_ETSIC. Enumerate each table and keep the one consistent with measurement;
that table is then the authoritative alpha2 -> pair map, which is the only
knob that actually changes the regulatory table here.
"""
import re
import sys
import hosttables as H

C = open('net/mi_reg_db.c', encoding='utf-8', errors='replace').read()


def all_tables():
    """Yield (start_offset, {alpha2: (pair_sym, super6g_sym)}) per table."""
    for m in re.finditer(r'g_all_countries\[\] = \{(.*?)\n\};', C, re.S):
        out = {}
        for row in re.finditer(r'CE\(([^)]*)\)', m.group(1)):
            toks = [t.strip() for t in row.group(1).split(',')]
            if len(toks) < 4:
                continue
            name, pair_sym, sup, alpha = toks[0], toks[1], toks[2], toks[3]
            out[alpha] = (pair_sym, sup, name)
        yield m.start(), out


def score(tbl, label):
    """Compare a table's implied rows to the measured live tables."""
    # measured on this device: AR has 36 dBm above 5735 and DFS-UNSET;
    # US has 24 dBm on 5170-5250 with DFS; CN has 5735-5835 at 33 dBm.
    want = {'AR': ('APL17_ETSIC',), 'US': ('FCC15_FCCA',), 'CN': ('APL14_CHNA',)}
    ok = 0
    for alpha, syms in want.items():
        got = tbl.get(alpha)
        if got and got[0] in syms:
            ok += 1
    return ok, label


tables = list(all_tables())
print('g_all_countries tables found:', len(tables))
best = None
for off, t in tables:
    ok, _ = score(t, off)
    ar = t.get('AR')
    print('  @%-7d entries=%-4d AR->%-14s match-with-live=%d/3' %
          (off, len(t), ar[0] if ar else '?', ok))
    if best is None or ok > best[0]:
        best = (ok, t, off)

ok, tbl, off = best
print('\nusing table @%d (live match %d/3)' % (off, ok))
if '--rank' in sys.argv:
    import chancov
    rows_best = []
    for alpha, (pair_sym, sup, name) in sorted(tbl.items()):
        if pair_sym not in H.PAIRS:
            continue
        rules = chancov.rows_of(pair_sym)
        if not rules:
            continue
        cov, _ = chancov.enabled_channels(rules)
        p24 = max((r['pwr'] for r in rules if 2400 <= r['start'] < 2500), default=0)
        p5 = max((r['pwr'] for r in rules if 4900 <= r['start'] < 5925), default=0)
        dfs = any('RADAR' in r['flags'] for r in rules)
        nir = any('NO_IR' in r['flags'] or 'NO-IR' in r['flags'] for r in rules)
        has6 = pair_sym in H.PAIRS and cov['6'] > 0 or sup not in ('0', '')
        rows_best.append((p24 + p5, alpha, pair_sym, cov, p24, p5, dfs, nir, sup))
    rows_best.sort(reverse=True)
    print('alpha2   pair           2.4/5/6 enabled      p24 p5  DFS NO-IR super6g')
    for _, alpha, sym, cov, p24, p5, dfs, nir, sup in rows_best[:20]:
        print('%-8s %-14s %2d/%2d/%2d        %-4d %-4d %-3s %-4s %s' %
              (alpha, sym, cov['2.4'], cov['5'], cov['6'], p24, p5,
               'yes' if dfs else 'no', 'yes' if nir else 'no', sup))
