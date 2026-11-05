# WiFi7-Lab — Wi-Fi 7 Full-Capability Lab Module

**Language: [简体中文](README.md) | English (current)**

**Current version: v1.5.0.** Magisk module for **Xiaomi pudding / Qualcomm peach_v2** that went from read-only diagnostics (v1.4) to a full-capability laboratory: regulatory domain (any ISO country / 00 world), transmit power (auto / fixed), WCNSS driver-config override, and regdb regulatory-database replacement are all configurable, modifiable, and reversible. Nothing is locked to a single parameter or power level.

> **For learning, research, and laboratory reference only.**
>
> This project is provided solely for educational, research, interoperability, and controlled-laboratory testing. It is not advice or authorization to operate radio equipment outside the rules applicable to your location. Users are responsible for complying with local spectrum, DFS/AFC, channel, indoor/outdoor, and transmit-power requirements.

## v1.5 capability layer (all configurable, all reversible)

| Control | Config key | Notes |
| --- | --- | --- |
| Regulatory domain / country | `COUNTRY_PROFILE` | `SYSTEM` / `US` / `CA` / `CN` / `JP` / `00` (world) / `CUSTOM` + `COUNTRY_CODE`. The channel/power table for the selected country comes from the regulatory database (see regdb below) |
| TX power | `TX_POWER_MODE` / `TX_POWER_MBM` | `auto` = regulatory domain controls power; `fixed` = force nl80211 power (millibel, 100 = 1 dB, 24000 = 24 dBm). Self-managed PHY may clamp or refuse; live readback is always reported |
| WCNSS driver config | `WCNSS_INJECT` | Merges `$MODDIR/wcnss/*.ini` on top of the vendor config into `/data/vendor/wifi/` (read by qcacld ahead of the vendor path). Override individual keys without rebuilding the whole file |
| regdb replacement | `REGDB_MOUNT` + `$MODDIR/regdb.bin` | Bind-mounts a custom regdb.bin over the detected vendor path — the direct way to change the regulatory channel/power table itself. The vendor partition is never modified |
| Driver reload without reboot | `FORCE_WIFI_TOGGLE` | Toggles Wi-Fi off/on after deployment so the driver re-reads its config (brief Wi-Fi drop only; no reboot, no cellular/ethernet impact) |
| EHT / MLO / 6 GHz vendor flags | `KEEP_EHT` / `KEEP_MLO` | Applied only when the ROM exposes the property; never invented |

The default configuration is the most-open reasonable baseline (`COUNTRY_PROFILE=US` keeps 6 GHz / 320 MHz inside the regulatory domain; `TX_POWER_MODE=auto`, `FORCE_WIFI_TOGGLE=0`). Edit `/data/adb/wifi7_lab_safe.conf` or use `profile.sh`, then run `action.sh`.

## Features (v1.4 and earlier, retained)

- EHT (802.11be) capability keeper — property is touched only if the ROM exposes it
- MLO capability keeper
- 6 GHz / 320 MHz / TWT / NAN / Wi-Fi Aware / TDLS / Fast Roam / SU Beamforming / MLO link-count audit
- Android Framework + Qualcomm self-managed PHY country readback with retry handling
- 2.4 / 5 / 6 GHz enabled / disabled / DFS channel summaries and full PHY frequency-table export
- Magisk module description shows live driver country, framework country, requested profile, TX power readback, and consistency state; read-only refresh every 300 s (configurable to off)

## Usage

```sh
# country / regulatory domain
sh /data/adb/modules/wifi7_lab_safe/profile.sh US
sh /data/adb/modules/wifi7_lab_safe/profile.sh 00
sh /data/adb/modules/wifi7_lab_safe/profile.sh CUSTOM US

# TX power
sh /data/adb/modules/wifi7_lab_safe/profile.sh tx auto
sh /data/adb/modules/wifi7_lab_safe/profile.sh tx fixed 27000    # 27 dBm

# WCNSS override / regdb replacement
sh /data/adb/modules/wifi7_lab_safe/profile.sh wcnss /sdcard/Download/my_keys.ini
sh /data/adb/modules/wifi7_lab_safe/profile.sh regdb /sdcard/Download/regdb.bin

# driver reload switch
sh /data/adb/modules/wifi7_lab_safe/profile.sh toggle 1

# revert TX power / WCNSS / regdb
sh /data/adb/modules/wifi7_lab_safe/profile.sh reset

# show active capability controls
sh /data/adb/modules/wifi7_lab_safe/profile.sh show

# apply and export diagnostics
sh /data/adb/modules/wifi7_lab_safe/action.sh
```

## Limits and rollback

v1.5 hands over full control of the parameters above; every control is reversible:

- `profile.sh reset` reverts TX power / WCNSS overrides / regdb mount
- `uninstall.sh` (runs on module removal) reverts all controls and clears the country override
- vendor partition files (WCNSS, regdb.bin) are never written directly; overrides go through `/data/vendor/wifi/` and bind mounts, and disappear on uninstall

A displayed country is not a channel/power authorization: verify the exported PHY frequency table and local regulations before relying on any band.
