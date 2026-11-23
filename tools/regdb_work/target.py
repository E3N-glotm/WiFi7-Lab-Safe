"""Which file does the driver actually load, and where are the bytes to edit?

Live proof on this board: /vendor/lib/modules/{icnss2,cnss2}.ko contain the
literal string "regdb_xiaomi.bin" and contain no "regdb.bin" at all, so the
firmware REGDB download is regdb_xiaomi.bin (= r2.bin, head 69e9). Every
earlier bind-mount experiment bound regdb.bin (= r1.bin, head a2ce), i.e. a
file the driver never reads -- which explains why content edits appeared to
be "ignored" while a header edit appeared to "break" things only when the
wrong file happened to be the mount target.

Prints, for each candidate file, the record offset of US/CN/00 and the exact
byte offset of the reg_dmn_pair_id field, so device-side patches use offsets
computed from the real loaded file rather than assumed ones.
"""
import struct

for name in ('r1.bin', 'r2.bin'):
    d = open(name, 'rb').read()
    print('===', name, 'len', len(d), 'head', d[0:2].hex(),
          'md5-source-of-truth')
    for cc in (b'US', b'CN', b'00', b'XA'):
        tok = -1
        for i in range(0, 0x1000, 16):
            if d[i + 7:i + 9] == cc and d[i + 10:i + 12] == cc:
                tok = i
                break
        if tok < 0:
            print('   %-3s not present' % cc.decode())
            continue
        # `i` is already the 16-byte record start (alpha2 lives at rec+7);
        # an earlier revision subtracted 7 again and reported shifted fields.
        rec = tok
        pair = struct.unpack_from('<H', d, rec + 4)[0]
        print('   %-3s rec=0x%03x pair=%-4d super6g=0x%02x '
              'pair_bytes=%d-%d raw=%s' %
              (cc.decode(), rec, pair, d[rec + 6], rec + 4, rec + 5,
               d[rec:rec + 16].hex(' ')))
    free = None
    for i in range(0, 0x1000, 16):
        if d[i:i + 16] == b'\x00' * 16:
            free = i
            break
    print('   first free slot: %s' % (hex(free) if free else 'none'))
