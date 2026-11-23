"""Parse the Qualcomm host built-in regulatory tables (reg_db.c/.h) so we can
render, offline, exactly which channel/power/flag profile a given reg_dmn_pair
id produces. This is what live `iw reg get` shows for a self-managed PHY.

Sources on disk: net/mi_reg_db.c, net/mi_reg_db.h  (same tree family as the
peach host driver, "database version 41").
"""
import re
import json
import os

C = open('net/mi_reg_db.c', encoding='utf-8', errors='replace').read()
H = open('net/mi_reg_db.h', encoding='utf-8', errors='replace').read()


def enum_values(text, name):
    """Parse `enum name { A = 0x10, B, C = 5, ... };` into ordered {sym: value}."""
    m = re.search(r'enum\s+' + name + r'\s*\{(.*?)\n\};', text, re.S)
    if not m:
        return {}
    body = m.group(1)
    out, nxt = {}, 0
    for item in body.split(','):
        item = item.strip()
        if not item or item.startswith('/*') or item.startswith('//'):
            continue
        if '=' in item:
            sym, val = item.split('=', 1)
            sym = sym.strip()
            try:
                v = int(val.strip().rstrip(','), 0)
            except ValueError:
                continue
            out[sym] = v
            nxt = v + 1
        else:
            if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', item):
                out[item] = nxt
                nxt += 1
    return out


def ordered_table(text, array_name, value_parser):
    """Parse `const struct X name[] = { [SYM] = {...}, ... };` into {SYM: parsed}."""
    # Anchor on the *array definition* (`name[] = {`); the same identifier also
    # appears as `enum name {`, which must not win the leftmost match.
    m = re.search(r'\b' + array_name + r'\b\s*(?:\[[^\]]*\])?\s*=\s*\{(.*?)\n\};',
                  text, re.S)
    if not m:
        return {}
    body = m.group(1)
    out = {}
    for dm in re.finditer(r'\[([A-Za-z0-9_]+)\]\s*=\s*\{', body):
        name = dm.group(1)
        i = dm.end() - 1
        depth = 0
        while i < len(body):
            if body[i] == '{':
                depth += 1
            elif body[i] == '}':
                depth -= 1
                if depth == 0:
                    break
            i += 1
        out[name] = value_parser(body[dm.end() - 1: i + 1])
    if not out:
        # designator-less rows, e.g. g_reg_dmn_pairs uses plain `{A, B, C},`
        for dm in re.finditer(r'\{([^{}]*)\}', body):
            toks = [x.strip() for x in dm.group(1).split(',')]
            if len(toks) < 2:
                continue
            v = value_parser('{%s}' % dm.group(1))
            if v:
                out[toks[0]] = v
    return out


def split_items(blob):
    """Top-level comma split inside one {...}."""
    inner = blob.strip()
    if inner.startswith('{'):
        inner = inner[1:-1]
    out, depth, cur = [], 0, ''
    for ch in inner:
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
        if ch == ',' and depth == 0:
            out.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


RULES = {}
for band, arr in (('2g', 'reg_rules_2g'), ('5g', 'reg_rules_5g')):
    def vp(b, band=band):
        it = split_items(b)
        if len(it) < 5:
            return None
        return dict(start=int(it[0]), end=int(it[1]), bw=int(it[2]),
                    pwr=int(it[3]), flags=it[4])
    t = ordered_table(C, arr, vp)
    for k, v in t.items():
        if v:
            RULES[k] = dict(v, band=band)

DOMAINS = {}
for band, arr in (('2g', 'regdomains_2g'), ('5g', 'regdomains_5g')):
    def vp(b, band=band):
        it = split_items(b)
        if len(it) < 6:
            return None
        # the rule list is the brace group; field count varies across driver
        # revisions, so locate it structurally instead of by index
        rl = next((x for x in it if x.startswith('{')), '')
        names = re.findall(r'[A-Za-z0-9_]+', rl)
        return dict(ctl=it[0], dfs=it[1], rules=names, fields=len(it))
    t = ordered_table(C, arr, vp)
    for k, v in t.items():
        if v:
            DOMAINS[k] = dict(v, band=band)

PAIRS = {}
def pair_vp(b):
    it = split_items(b)
    if len(it) < 3:
        return None
    return dict(pair_sym=it[0], dmn5=it[1], dmn2=it[2])
t = ordered_table(C, 'g_reg_dmn_pairs', pair_vp)
PAIRS.update(t)

PAIR_IDS = enum_values(H, 'reg_domain')
DMN5_ORDER = list(enum_values(H, 'reg_domains_5g'))
DMN2_ORDER = list(enum_values(H, 'reg_domains_2g'))

if __name__ == '__main__':
    print('rules', len(RULES), 'domains', len(DOMAINS), 'pair rows', len(PAIRS))
    print('pair id enums', len(PAIR_IDS), '5g dmn', len(DMN5_ORDER), '2g dmn', len(DMN2_ORDER))
    hits = [(s, v) for s, v in PAIR_IDS.items() if s in PAIRS]
    print('pairs with ids resolved', len(hits))
    for want in ('FCC15_FCCA', 'APL14_CHNA', 'APL9_MKKC', 'ETSI1_WORLD', 'WORC_WORLD'):
        p = PAIRS.get(want)
        print('  ', want, '-> id', PAIR_IDS.get(want), p,
              'render rules', (DOMAINS.get(p['dmn2'], {}).get('rules') if p else None),
              (DOMAINS.get(p['dmn5'], {}).get('rules') if p else None))
    unknown = [s for s in PAIRS if s not in PAIR_IDS]
    print('pair rows lacking id:', unknown[:10])
