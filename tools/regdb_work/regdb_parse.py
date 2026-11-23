import struct, re, json

r1 = open('r1.bin','rb').read()
r2 = open('r2.bin','rb').read()

# ---- index ----
# entry: [+0 u16 f01][+2 b2][+3 cc][+4 cc][+5 cc][+6 cc][+7 u16?][+9 u16 tag][+11 u16?][+13 u16 bandptr][+15 u8 flags]
# from US entry: 00 48 03 ea 00 21 55 53 00 55 53 00 28 03 05 00
# 48 00 = 0x48 = 72 ??? not offset. bandptr@13 = 05 00 -> 5? no.
# Re-derive: US entry bytes 00 48 03 ea 00 21 55 53 00 55 53 00 28 03 05 00
# cc at +6? earlier find: 'US\0US\0' at 3543; 3543-6=3537 entry. bytes[3:5]? no.
# Let's just use: entry start = token-6 ; cc1@+6 cc2@+10 ; tag@+12 = 28 03 ; f01@+0 = 00 48 (u16=72); b2@+2=03; @+4=ea; @+8=00; @+11=21
# The 2.4G band block for the FIRST country (AF) starts at 0x2030.
# Hypothesis: band block offset = fixed per country order: block_i at 0x2030 + i*BLOCK
# US is the 242nd ISO code in the list; AF is 1st.
iso = ["AF","AX","AL","DZ","AS","AD","AO","AI","AQ","AG","AR","AM","AW","AU","AT","AZ",
"BS","BH","BD","BB","BY","BE","BZ","BJ","BM","BT","BO","BA","BW","BR","IO","BN","BG",
"BF","BI","CV","KH","CM","CA","KY","CF","TD","CL","CN","CX","CC","CO","KM","CD","CG",
"CK","CI","HR","CU","CY","CZ","DK","DJ","DM","DO","EC","EG","SV","GQ","ER","EE","SZ",
"ET","FK","FO","FJ","FI","FR","GF","PF","TF","GA","GM","GE","DE","GH","GI","GR","GL",
"GD","GU","GT","GG","GN","GW","GY","HT","HM","VA","HU","IS","IN","ID","IR","IQ","IE",
"IM","IL","IT","JM","JP","JO","KZ","KP","KR","KW","KG","LA","LV","LB","LS","LR","LY",
"LI","LT","LU","MO","MK","MG","MW","MY","MV","ML","MT","MH","MR","MU","YT","MX","FM",
"MD","MC","MN","ME","MS","MA","MZ","MM","NA","NR","NP","NL","NZ","NI","NE","NG","NU",
"NF","MP","NO","OM","PK","PW","PA","PG","PY","PE","PH","PN","PL","PT","PR","QA","RE",
"RO","RU","RW","BL","SH","KN","LC","MF","VC","ST","SM","SA","SN","RS","SC","SL","SG",
"SK","SI","SB","SO","ZA","GS","ES","LK","SD","SR","SJ","SE","CH","SY","TW","TJ","TZ",
"TH","TL","TG","TK","TO","TT","TN","TR","TM","TC","TV","UG","UA","GB","US","UM","UY",
"UZ","VU","VE","VN","VG","VI","WF","EH","YE","ZM","ZW"]
# US position
us_i = iso.index("US")
af_i = iso.index("AF")
print('iso len', len(iso), 'US idx', us_i)

# scan index tokens in file to build real order (file order may differ from list)
toks = []
for mm in re.finditer(rb'([A-Z]{2})\x00\1\x00', r1[:len(iso)*16+64]):
    toks.append((mm.start(), mm.group(1).decode()))
print('tokens found:', len(toks))
# stride
strides = [toks[i+1][0]-toks[i][0] for i in range(len(toks)-1)]
from collections import Counter
print('stride histogram:', Counter(strides))
order = [t[1] for t in toks]
us_pos = order.index('US') if 'US' in order else -1
print('US file-order pos:', us_pos, 'first12:', order[:12])

# band block pointer: check entry@13 field
def entry_field(tstart, code, off):
    e = tstart - 3  # cc1 at e+3
    return r1[e+off:e+off+2]

# For US token: dump raw 20 bytes
t = [x for x in toks if x[1]=='US'][0]
e = t[0]-3
print('US raw entry 20B:', r1[e:e+20].hex())

# The 2.4G block for AF is at 0x2030. If blocks are laid out sequentially per
# file order with a fixed stride S, then US block = 0x2030 + us_pos*S.
# We know US 2.4G data (2402...) is at 0x2032 per find. So US block start ~ 0x2030??
# That would mean AF and US share 0x2030 - i.e. blocks are NOT per-country;
# the band data is SHARED and entries just carry band-range indexes.
# Verify: does AF point to same 2.4G? find 2402 occurrences: only 0x2032-0x2086 (8 hits,
# all inside 0x2032-0x209a). So there is ONE shared 2.4G table. The per-country
# entries must carry an index into shared band tables.
print('CONCLUSION: shared band tables; index entries carry pointers into them')
