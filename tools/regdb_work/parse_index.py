import struct

data = open('r1.bin','rb').read()
assert len(data) == 24278, len(data)

# Known ISO country code list (the index is in ISO order per the dump)
ccs = ["AF","AX","AL","DZ","AS","AD","AO","AI","AQ","AG","AR","AM","AW","AU","AT","AZ",
"BS","BH","BD","BB","BY","BE","BZ","BJ","BM","BT","BO","BA","BW","BR","IO","BN","BG",
"BF","BI","CV","KH","CM","CA","KY","CF","TD","CL","CN","CX","CC","CO","KM","CD","CG",
"CK","CI","HR","CU","CY","CZ","DK","DJ","DM","DO","EC","EG","SV","GQ","ER","EE","SZ",
"ET","FK","FO","FJ","FI","FR","GF","PF","TF","GA","GM","GE","DE","GH","GI","GR","GL",
"GD","GU","GT","GG","GN","GW","GY","HT","HM","VA","HU","IS","IN","ID","IR","IQ","IE",
"IM","IL","IT","JM","JP","JE","JM2","JO","KZ","KH2","KP","KR","KW","KG","LA","LV","LB",
"LS","LR","LY","LI","LT","LU","MO","MK","MG","MW","MY","MV","ML","MT","MH","MR","MU",
"YT","MX","FM","MD","MC","MN","ME","MS","MA","MZ","MM","NA","NR","NP","NL","NZ","NI",
"NE","NG","NU","NF","MP","NO","OM","PK","PW","PA","PG","PY","PE","PH","PN","PL","PT",
"PR","QA","RE","RO","RU","RW","BL","SH","KN","LC","MF","VC","ST","SM","SA","SN","RS",
"SC","SL","SG","SK","SI","SB","SO","ZA","GS","ES","LK","SD","SR","SJ","SE","CH","SY",
"TW","TJ","TZ","TH","TL","TG","TK","TO","TT","TN","TR","TM","TC","TV","UG","UA","GB",
"US","UM","UY","UZ","VU","VE","VN","VG","VI","WF","EH","YE","YU","ZM","ZW","JE2"]

# We only need to find the index entries by scanning for the repeating
# country-code bytes and inferring the stride. Find "US" which we know.
import re
# Index entry layout (from od): at each stride N, bytes are:
#   +0..+3  checksum-like field
#   +4..+5  field (00 0d / 00 01 / 00 00 ...)
#   +6..+8  country code (2 ascii + NUL)
#   +9..+11 country code repeated (2 ascii + NUL)
#   +12..   '28 03' style tag ...
# Find NUL-terminated 2-letter codes that appear twice in a row.
idx = []
for mm in re.finditer(rb'([A-Z]{2})\x00\1\x00', data[:8192]):
    idx.append((mm.start(), mm.group(1).decode()))
print('found %d code tokens in first 8KB' % len(idx))
# show offsets + deltas to learn the true stride
prev = None
for off, code in idx:
    delta = '' if prev is None else ' d=%d' % (off-prev)
    print('%5d  %s%s' % (off, code, delta))
    prev = off
