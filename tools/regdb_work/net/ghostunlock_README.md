# 6 GHz unlock — Xperia 1 VIII (XQ-GE74)

Live-verified procedure for enabling the full 6 GHz band (channels 1–93 PSC
set, 5925–7125 MHz) on a stock, bootloader-locked Xperia 1 VIII running
firmware `73.0.A.2.53`, using temporary GhostUnlock root and a KernelSU
module. **No partition is modified; the stock vendor image stays intact.**

## TL;DR

Two independent gates block 6 GHz on the US/SEA Xperia 1 VIII. Both must be
cleared:

1. **`/vendor/etc/wifi/regdb.bin`** — the shipped Qualcomm regulatory database
   has the US country record's **6 GHz superdomain byte zeroed** (`0x00`).
   Country codes like TW, DE, GB, HK, SG carry `0x03` instead. The 6 GHz rule
   tables physically exist in the binary; the US record just points at
   nothing. Framework-side forcing (`cmd wifi force-country-code enabled US`)
   changes framework + driver country but **cannot** fix this — verified.
2. **`ro.vendor.sony.wlan.6e_cc_list`** — Sony's vendor country allowlist.
   `11be_cc_list` includes `US`; `6e_cc_list` does **not**. The vendor HAL
   consults this at country-change time and returns an empty 6 GHz channel
   list for unlisted countries. Fix: `resetprop` (KernelSU) appending `US`.

## regdb.bin format (reverse-engineered)

See `scripts/analyze_regdb.py` for a working parser. Summary:

| Section | Offset | Layout |
|---|---|---|
| Country table | `0x0000` | 239 × 16 B: `[0:2] pad, [2:4] ctry u16, [4:6] regpair u16, [6] 6G superdomain, [7:10] alpha2, [10:13] alpha2 dup, [13:16] tail` |
| Regpair table | `0x1b7c` | ~119 × 4 B: `(u8, u8, u16 pair_id)` — US = `(6, 5, 145)` |
| 2G/5G/6G rules | `0x2030` | 12 B records: `(pad, start_khz, end_khz, max_bw, flags, max_power)` — 6 GHz rules **do exist** at `0x2588+` and `0x2cd8+` |
| 5G regdomains | `0x3dc8` | 16 B records (ctl `0x10/0x30/0x40/0xff` = FCC/ETSI/MKK/NONE) |
| 6G subdomains | `0x4a48` | 16 B records |
| Superdomain map | `0x53a6` | 12 B records: `(u16 super_id, …subdomain pairs…)` |

Verified against the qcacld-3.0 sources (`reg_db.c`, `reg_db.h`,
`WLAN.LA.2.0.r3` from Codelinaro); the shipped binary matches the
`CONFIG_REG_CLIENT` + 6 GHz variant of the schema, with per-country edits.

**US record, stock:** `0xdd0: 00 00 48 03 91 00 00 55 53 00 55 53 00 14 03 03`
— note byte 6 = `00`. Patched (working) value: `03`.

## Superdomain value — read this before choosing

- `0x18` (mainline `FCC1_6G_18`, "US VLP") **broke Wi-Fi on this device**:
  `wlanfw` never started, Wi-Fi was dead from boot until the module was
  removed. Do not use.
- `0x03` is Sony's own value in this same binary for TW/DE/GB/HK/SG/FR/IT/ES
  and maps to subdomains that the driver accepts. **Live-verified working**:
  channels 1–93 appear at boot, driver stable, normal MLO association.

Caveat: `0x03` is ETSI-family (23 dBm LPI-style power limits), not full FCC
SP. If you need exact FCC power tables you would have to map region C/D
subdomains to FCC-ctl entries and craft a custom superdomain — untested.

## The country allowlist prop

```
ro.vendor.sony.wlan.6e_cc_list   # no US   <- gate
ro.vendor.sony.wlan.11be_cc_list # has US
```

Patch at boot via the module's `post-fs-data.sh`:

```sh
resetprop ro.vendor.sony.wlan.6e_cc_list "$(getprop ro.vendor.sony.wlan.6e_cc_list),US"
```

KernelSU ships `resetprop` at `/data/adb/ksu/bin/resetprop`.

## Procedure (end to end)

1. **Root** — run the GhostUnlock exploit (`prebuilt/ghostlock`), one attempt
   per boot. Root is an in-kernel LKM: it disappears on reboot; re-run after.
2. **Patch regdb offline:**
   ```sh
   adb pull /vendor/etc/wifi/regdb.bin          # via root, or /vendor/etc/wifi is world-readable
   python3 scripts/patch_regdb_us.py regdb.bin regdb_us03.bin --super6g 0x03
   ```
3. **Build + install the module:**
   ```sh
   bash scripts/build_us6g_module.sh regdb_us03.bin xperia_us6g.zip
   adb push xperia_us6g.zip /data/local/tmp/
   adb shell su -c 'ksud module install /data/local/tmp/xperia_us6g.zip'
   ```
4. **Reboot.** On boot the module bind-mounts the patched regdb over
   `/vendor/etc/wifi/regdb.bin` (stock partition untouched) and appends `US`
   to the allowlist prop.
5. **Verify:**
   ```sh
   adb shell su -c 'md5sum /vendor/etc/wifi/regdb.bin'          # != stock d54533a6...
   adb shell su -c 'getprop ro.vendor.sony.wlan.6e_cc_list'      # ends in ,US
   adb shell su -c 'dumpsys wifi' | grep SupportedChannelListIn6g
   ```
   Expected: `SupportedChannelListIn6g[1, 5, 9, ..., 93]`.

> **KSU late-load caveat:** GhostUnlock's KernelSU is late-loaded *after* boot,
> so the module's `post-fs-data.sh` does **not** run in the same boot the
> exploit runs in. The bind-mount + resetprop must be applied manually for
> immediate testing, or the module only becomes effective after a reboot
> (which kills root — re-run the exploit after). Sequence that works:
> reboot → run exploit → `su -c` manual bind-mount + resetprop → force a
> country change (`cmd wifi force-country-code disabled` then `enabled US`).

## Recovery

If Wi-Fi breaks after installing the module:

```sh
adb shell su -c '
  ksud module disable xperia_us6g
  rm -rf /data/adb/modules/xperia_us6g /data/adb/modules_update/xperia_us6g
  umount /vendor/etc/wifi/regdb.bin
  reboot'
```

If Wi-Fi is already dead (no wireless adb): reboot — a disabled module does
not re-mount, and the stock config returns. Worst case, re-run GhostUnlock
over USB and remove the module directory.

## Operational warnings

- Wi-Fi service restarts (`stop wlanfw` / `svc wifi disable`) on this build
  take wireless-adbd down with the interface and the phone does **not**
  self-reassociate; you lose all remote access. Never restart the wlan stack
  over wireless ADB — use boot-persistent changes and reboots instead.
- One exploit attempt per boot (kernel race; see main README warnings).
- The empty-vs-populated `SupportedChannelListIn6g` history in `dumpsys wifi`
  is the authoritative evidence of whether a given country/prop combination
  unlocked the band.
