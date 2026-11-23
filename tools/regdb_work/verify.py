import base64, gzip
for name, want_head in [('r1.gz.b64', 'a2ce0400'), ('r2.gz.b64', '69e90400')]:
    with open(name, 'r') as f:
        b64 = f.read().strip()
    raw = base64.b64decode(b64)
    data = gzip.decompress(raw)
    ok = 'OK' if (len(data) == 24278 and data[:4].hex() == want_head) else 'MISMATCH'
    print('%s b64=%d gz=%d raw=%d head=%s %s' % (name, len(b64), len(raw), len(data), data[:4].hex(), ok))
    if len(data) == 24278:
        with open(name.replace('.gz.b64', '.bin'), 'wb') as o:
            o.write(data)
