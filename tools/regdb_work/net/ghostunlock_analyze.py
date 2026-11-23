#!/usr/bin/env python3
"""Analyze a Qualcomm/Sony peach-family regdb.bin (qca_cld3, Xperia 1 VIII XQ-GE74).

Layout (reverse-engineered 2026-09, verified against qcacld reg_db.c / reg_db.h,
Codelinaro WLAN.LA.2.0):

  1. Country table  @0x0000, 239 records x 16 bytes:
       [0:2]  pad (0)
       [2:4]  country code u16 LE  (840=US, 158=TW, 392=JP, ...)
       [4:6]  regdmn pair id u16   (US=145/FCC8_FCCA, TW=146, DE/GB=38, ...)
       [6]    6GHz superdomain id  <-- THE 6GHz GATE (0 = no 6GHz for that country)
       [7:10] alpha2 "US\0"       (duplicated at [10:13])
       [13:16] tail (bw/ctl fields)
  2. Regdomain-pair table @0x1b7c, ~119 x 4 bytes (u8, u8, u16 pair_id)
  3. Rule tables @0x2030..0x2fa8, 12-byte records:
       (u16 pad=0, u16 start_khz, u16 end_khz, u16 max_bw, u16 flags, u16 max_power)
       6GHz rules (5925-7125) live at 0x2588+ and 0x2cd8+
  4. Region B @0x3dc8  = 5G regdomains (ctl 0x10/0x30/0x40/0xff = FCC/ETSI/MKK/NONE)
  5. Region C @0x4a48  = 6GHz subdomain table
  6. Regions D/E       = superdomain -> subdomain mappings

Usage: analyze_regdb.py <regdb.bin>
"""
import struct, sys

def main(path):
    data = open(path, "rb").read()
    print(f"file: {path}  size: {len(data)}")

    print("\n== country table (records with alpha2 == alpha2d) ==")
    for off in range(0, 0xEF0, 16):
        ctry = struct.unpack_from("<H", data, off + 2)[0]
        pair = struct.unpack_from("<H", data, off + 4)[0]
        super6 = data[off + 6]
        a1 = data[off + 7:off + 9]
        a2 = data[off + 10:off + 12]
        if a1 != a2 or not all(65 <= b <= 90 for b in a1):
            continue
        cc = a1.decode()
        mark = "  <-- 6G ENABLED" if super6 else ""
        focus = "  <--" if cc in ("US", "TW", "JP", "DE", "GB") else ""
        print(f"  {cc}  ctry={ctry:<4d} pair={pair:<4d} super6g=0x{super6:02X}{mark}{focus}")

    n6 = 0
    for off in range(0x2030, 0x2FA8, 12):
        pad, s, e, bw, fl, pw = struct.unpack_from("<6H", data, off)
        if 5900 <= s <= 7125 and e > s:
            n6 += 1
    print(f"\n6GHz rule records present in binary: {n6}")
    print("note: country super6g=0x00 means the driver will list NO 6GHz channels")
    print("      for that country regardless of framework country code or force-country-code.")

if __name__ == "__main__":
    main(sys.argv[1])
