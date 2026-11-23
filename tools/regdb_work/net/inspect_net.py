import hashlib, struct, sys, os

def info(path):
    d = open(path, 'rb').read()
    out = {
        'file': os.path.basename(path),
        'len': len(d),
        'sha256': hashlib.sha256(d).hexdigest(),
        'cksum_le16': struct.unpack('<H', d[:2])[0] if len(d) >= 2 else None,
        'ver': d[2:4].hex() if len(d) >= 4 else None,
        'head48': d[:48].hex() if len(d) >= 48 else d.hex(),
    }
    # check for 0x0328 tag pattern at stride 16 from 0x10 (like our reverse-engineered layout)
    if len(d) >= 0x10 + 16:
        tags = 0
        n = 0
        off = 0x10
        while off + 16 <= min(len(d), 0x1000):
            if d[off+6:off+8] == b'\x28\x03':
                tags += 1
            n += 1
            off += 16
        out['tag0328_hits'] = tags
        out['idx_slots_scanned'] = n
    return out

if __name__ == '__main__':
    for p in sys.argv[1:]:
        print(info(p))
