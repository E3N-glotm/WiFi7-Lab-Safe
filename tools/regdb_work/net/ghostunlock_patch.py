#!/usr/bin/env python3
"""Patch a peach-family regdb.bin to grant a country a 6GHz superdomain.

Sony ships the Xperia 1 VIII (XQ-GE74) regdb with the US country record's
6GHz superdomain byte zeroed. This tool rewrites that single byte.

Choose the superdomain value carefully:
  0x18 = mainline FCC1_6G_18 (US VLP)  -- CAUTION: crashed wlanfw on XQ-GE74
         (wifi failed to start at boot; needed module removal + reboot)
  0x03 = Sony-native value used by TW/DE/GB/HK/SG/FR/IT/ES records in the SAME
         shipped binary. LIVE-VERIFIED on XQ-GE74: 6GHz channels 1..93 (PSC set)
         appear at boot, driver stable, wifi associates normally.

The vendor country allowlist prop must ALSO include the country or the HAL
returns an empty channel list at country-change time:
  resetprop ro.vendor.sony.wlan.6e_cc_list "<orig>,US"

Usage: patch_regdb_us.py <regdb.bin> <out.bin> [--super6g 0x03]
"""
import struct, sys, hashlib

def main():
    src, dst = sys.argv[1], sys.argv[2]
    super6g = 0x03
    if "--super6g" in sys.argv:
        super6g = int(sys.argv[sys.argv.index("--super6g") + 1], 0)
    data = bytearray(open(src, "rb").read())
    for off in range(0, 0xEF0, 16):
        if struct.unpack_from("<H", data, off + 2)[0] == 840:  # CTRY_UNITED_STATES
            print(f"US record @0x{off:04x}: {bytes(data[off:off+16]).hex()}")
            data[off + 6] = super6g
            print(f"patched: super6g=0x{super6g:02X} -> {bytes(data[off:off+16]).hex()}")
            open(dst, "wb").write(bytes(data))
            print(f"wrote {dst}  md5={hashlib.md5(bytes(data)).hexdigest()}")
            return
    raise SystemExit("US country record not found - not a peach regdb.bin?")

if __name__ == "__main__":
    main()
