r1 = open('r1.bin','rb').read()
r2 = open('r2.bin','rb').read()

# locate the US index entry (country code appears twice, NUL padded)
needle = b'US\x00US\x00'
pos = r1.find(needle)
print('US code token at offset', pos)

# The index entry is 16 bytes; the country code sits at entry+6 and entry+10.
# So entry start = pos-6.
entry = pos-6
print('US index entry start =', entry)
# dump 16 bytes of the entry
seg = r1[entry:entry+16]
print('entry hex:', seg.hex())
# bytes +4,+5 of entry = band data pointer (u16 LE)
import struct
ptr = struct.unpack('<H', seg[4:6])[0]
print('band-data pointer (u16@+4) =', ptr)

# dump the band data region starting at that pointer, 480 bytes, aligned
bd = r1[ptr:ptr+480]
print('band data @', ptr, 'len', len(bd))
# print as hex rows with offset
for i in range(0, len(bd), 16):
    print('%5d  %s' % (ptr+i, bd[i:i+16].hex(' ')))

# Compare to xiaomi at same pointer
ptr2 = struct.unpack('<H', r2[entry:entry+16][4:6])[0]
print()
print('XIAOMI US band-data pointer =', ptr2)
bd2 = r2[ptr2:ptr2+480]
print('XIAOMI band data @', ptr2)
for i in range(0, len(bd2), 16):
    print('%5d  %s' % (ptr2+i, bd2[i:i+16].hex(' ')))
