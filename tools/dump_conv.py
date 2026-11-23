# -*- coding: utf-8 -*-
import json, io, sys

OUT = io.open(r'E:\dev\WiFi7-Lab-Safe\tools\conv_dump.txt', 'w', encoding='utf-8')
def emit(*a):
    OUT.write(' '.join(str(x) for x in a) + '\n')

P = r'E:\Users\Alcatraz\Desktop\杂物\对话历史记录\检查WiFi频段差异_741a5ef12e94.json'
d = json.load(io.open(P, encoding='utf-8'))
emit('TITLE:', d.get('title'))
emit('CREATED:', d.get('create_time'), 'UPDATED:', d.get('update_time'))
mapping = d.get('mapping') or {}
cur = d.get('current_node')

# walk from current node up to root, collecting path
path = []
seen = set()
node = cur
while node is not None and node in mapping and node not in seen:
    seen.add(node)
    path.append(node)
    node = mapping[node].get('parent')
path.reverse()

def gettext(msg):
    if not msg: return ''
    c = msg.get('content') or {}
    parts = c.get('parts') or []
    out = []
    for p in parts:
        if isinstance(p, str):
            out.append(p)
        elif isinstance(p, dict):
            t = p.get('text') or p.get('content') or ''
            if t: out.append(str(t))
            else:
                # code execution / tool results
                rr = p.get('results')
                if isinstance(rr, list):
                    for r in rr:
                        if isinstance(r, dict):
                            out.append('[TOOLRESULT] ' + str(r.get('content') or r)[:2000])
    return '\n'.join(out)

for nid in path:
    n = mapping.get(nid) or {}
    msg = n.get('message')
    if not msg: continue
    role = msg.get('author', {}).get('role', '?')
    meta = msg.get('metadata') or {}
    kind = ''
    if role == 'assistant':
        k = (meta or {}).get('citations_metadata', {})
        kind = msg.get('author', {}).get('metadata', {})
    txt = gettext(msg)
    if not txt.strip():
        # maybe tool call
        c = (msg.get('content') or {})
        if c.get('tool_calls'):
            txt = '[TOOL CALLS] ' + json.dumps([tc.get('id') for tc in c['tool_calls']], ensure_ascii=False)
        elif c.get('model_slug'):
            continue
        else:
            continue
    emit('\n' + '='*90)
    emit('[%s] len=%d' % (role, len(txt)))
    emit(txt)
    OUT.flush()
emit('\n=== path nodes: %d of %d' % (len(path), len(mapping)))
OUT.close()
print('WROTE conv_dump.txt')
