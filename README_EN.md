# WiFi7-Lab-Safe — Wi-Fi 7 Capability Diagnostics

**Language: [简体中文](README.md) | English (current)**

**Current version: v1.4.2.** Magisk displays country values read back from the self-managed PHY and Android Framework, distinguishing them from the requested profile. Vendor EHT/MLO properties are changed only when the current WLAN implementation exposes the corresponding setting. All wireless operations remain subject to the regulatory requirements of the operating location. Details below include v1.4.0 historical features.


A configurable Magisk module for Wi-Fi capability testing on **Xiaomi pudding / Qualcomm peach_v2**.

v1.4.0 keeps the device's native EHT/MLO capability switches available, audits 6 GHz / 320 MHz and related vendor features, applies a standard Android Wi-Fi country profile, and verifies both Android Framework and the Qualcomm self-managed PHY regulatory country before reporting success.

> **For learning, research, and laboratory reference only.**
>
> This project is provided solely for educational, research, interoperability, and controlled-laboratory testing. It is not advice or authorization to operate radio equipment outside the rules applicable to your location. Users are responsible for complying with local spectrum, DFS/AFC, channel, indoor/outdoor, and transmit-power requirements.


## Features

- EHT capability keeper
- MLO capability keeper
- Native 6 GHz capability diagnostics
- 320 MHz EHT capability diagnostics
- Android Framework + Qualcomm self-managed PHY country readback
- Country profiles: SYSTEM / US / CA / CN / JP / CUSTOM
- Retry handling for transient Wi-Fi Binder failures
- Vendor capability audit for:
  - Fast Roam
  - SU Beamforming
  - 6 GHz vendor capability
  - TWT / TWT responder
  - NAN / Wi-Fi Aware
  - TDLS
  - MLO link count
  - EHT/MLO crypto bitmap
- Per-band enabled/disabled/DFS channel summary
- Full PHY frequency table export
- Current link/interface diagnostics
- Magisk Action script for immediate apply + report export
- Read-only Magisk country-status refresh every 300 seconds (configurable; no periodic country reapplication)
- Clean uninstall of module-owned runtime config/log files

## Configuration

Runtime configuration:

```text
/data/adb/wifi7_lab_safe.conf
```

Repository default:

```ini
COUNTRY_PROFILE=SYSTEM
COUNTRY_CODE=CN

KEEP_EHT=1
KEEP_MLO=1
CHECK_6GHZ_VENDOR_CAPABILITY=1
VERIFY_DRIVER_COUNTRY=1

COUNTRY_APPLY_RETRIES=12
COUNTRY_RETRY_DELAY_SEC=2

ENABLE_DIAGNOSTICS=1
VERBOSE_LOG=1
EXPORT_CHANNEL_TABLE=1
COUNTRY_STATUS_REFRESH_SEC=300

REQUEST_UNRESTRICTED_REGDOMAIN=0
REQUEST_FULL_TX_POWER=0
REQUEST_DISABLE_DFS_AFC=0
```

### Profiles

Follow the normal system / telephony country policy:

```sh
sh /data/adb/modules/wifi7_lab_safe/profile.sh SYSTEM
```

Request one of the built-in profiles:

```sh
sh /data/adb/modules/wifi7_lab_safe/profile.sh US
sh /data/adb/modules/wifi7_lab_safe/profile.sh CA
sh /data/adb/modules/wifi7_lab_safe/profile.sh CN
sh /data/adb/modules/wifi7_lab_safe/profile.sh JP
```

Request another two-letter ISO country code through Android's built-in Wi-Fi framework:

```sh
sh /data/adb/modules/wifi7_lab_safe/profile.sh CUSTOM TW
```

Apply the selected profile and export diagnostics:

```sh
sh /data/adb/modules/wifi7_lab_safe/action.sh
```

The Magisk module **Action** button runs the same apply-and-diagnostics path.

### Live country readback in Magisk (v1.4.2)

The module description shows `Driver country:CN | Framework:CN | Requested:CN [consistent]` (labels are localized in Simplified Chinese). The driver value is taken from `iw reg get` for a self-managed PHY; a selected country profile is **never** substituted for an unknown driver. Differing country values, a requested country not taking effect, and unavailable readings are explicitly marked as such.

The description refreshes after boot, manual Action, and by default every 300 seconds without reapplying country settings or repeatedly writing unchanged module metadata. Set `COUNTRY_STATUS_REFRESH_SEC=0` in the runtime config to disable periodic refresh. Reopen the Magisk module list if the UI caches the previous description.

These are reported regulatory-country codes, **not** verification of allowed channels, transmit power, 6 GHz availability, or active 320 MHz operation. Consult exported PHY frequencies and applicable local spectrum regulations.

## v1.4.0

- Replaced the v1.3 `COUNTRY_MODE` interface with `COUNTRY_PROFILE`.
- Added SYSTEM / US / CA / CN / JP / CUSTOM profiles.
- Added driver-country parsing from `iw reg get`.
- A requested country is considered successful only after both Framework and Qualcomm PHY readback match when `VERIFY_DRIVER_COUNTRY=1`.
- Added detailed vendor capability audit.
- Added enabled/disabled/DFS channel counts for 2.4 / 5 / 6 GHz.
- Added full PHY frequency table export.
- Added `profile.sh` for profile switching.
- Preserved EHT/MLO capability keeper behavior.
- Retained v1.3 retry handling for transient Binder failures.

## Device validation

Validated on:

- Xiaomi device codename: `pudding`
- Android 16 / HyperOS
- Qualcomm WLAN: `qca_cld3_peach_v2`
- Driver family reports self-managed regulatory domains
- Native PHY reports EHT and `320MHz in 6GHz Supported`

Example verified v1.4.0 state on the validation device:

```text
Framework country: US
Driver country:    US
PHY:               US / DFS-FCC
EHT disable prop:  false
MLO disable prop:  false
6 GHz:             native capability present
320 MHz in 6 GHz:  supported
```

Exact channels and power ceilings remain dependent on the selected regulatory domain, device firmware, calibration, role, SAR/thermal controls, and access point.

## Migration from v1.3.0

v1.4.0 uses new runtime keys. Existing v1.3 runtime files should be migrated to the new format. A clean v1.4 configuration uses:

```ini
COUNTRY_PROFILE=SYSTEM
COUNTRY_CODE=CN
KEEP_EHT=1
KEEP_MLO=1
```

If you previously used `COUNTRY_MODE=request`, choose the equivalent profile or use `CUSTOM <CC>`.

## Scope

The module does **not**:

- patch Qualcomm `regdb.bin` / `regdb_xiaomi.bin`
- construct mixed/custom regulatory domains
- disable DFS/AFC enforcement
- force transmit power outside the selected regulatory domain

The legacy `REQUEST_*` keys remain inert and are logged only for backward-readable configuration.

## License / responsibility

Source code is published for learning and research reference. You are responsible for backups, device recovery, testing methodology, and compliance with the rules applicable to your hardware and location.
