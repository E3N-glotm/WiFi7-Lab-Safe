# WiFi7-Lab-Safe

A configurable Magisk module for Wi-Fi capability testing on **Xiaomi pudding / Qualcomm peach_v2**.

It keeps vendor EHT/MLO capability switches enabled, reports native 6 GHz / 320 MHz capabilities, and can request a two-letter Wi-Fi country code through Android's built-in `cmd wifi force-country-code` interface with retry and readback verification.

> **For learning, research, and laboratory reference only.**
>
> This project is provided solely for educational, research, interoperability, and controlled-laboratory testing. It is **not** advice or authorization to operate radio equipment outside the rules applicable to your location. Users are responsible for complying with local spectrum, DFS/AFC, channel, indoor/outdoor, and transmit-power requirements.

## 中文说明

这是一个面向 **Xiaomi pudding / Qualcomm peach_v2** 的可配置 Magisk Wi-Fi 能力测试模块。

主要用于保持 EHT / MLO 厂商能力开关、查看原生 6 GHz / 320 MHz 能力，并通过 Android 自带的 `cmd wifi force-country-code` 接口请求两位国家码。v1.3.0 增加了 Wi-Fi Binder 就绪等待、失败重试和实际读回校验。

> **仅供学习、研究与实验室测试参考使用。**
>
> 本项目不构成绕过或违反所在地无线电监管要求的建议或授权。使用者应自行确认并遵守所在地关于频谱、DFS/AFC、信道、室内/室外使用及发射功率等规定。

## Features

- EHT capability keeper
- MLO capability keeper
- Native 6 GHz capability diagnostics
- 320 MHz EHT capability diagnostics
- Android framework country-code request
- Boot-time retry when Wi-Fi Binder is not ready
- Readback verification before logging success
- Magisk Action script for immediate apply + diagnostics
- Clean uninstall of module-owned config/log files

## Configuration

Runtime configuration:

```text
/data/adb/wifi7_lab_safe.conf
```

Default:

```ini
ENABLE_EHT=1
ENABLE_MLO=1
ENABLE_6GHZ_VENDOR_CAPABILITY=1
ENABLE_DIAGNOSTICS=1
VERBOSE_LOG=1

COUNTRY_MODE=system
COUNTRY_CODE=CN
COUNTRY_APPLY_RETRIES=12
COUNTRY_RETRY_DELAY_SEC=2

REQUEST_UNRESTRICTED_REGDOMAIN=0
REQUEST_FULL_TX_POWER=0
REQUEST_DISABLE_DFS_AFC=0
```

### Country-code modes

Follow the normal system / telephony country:

```ini
COUNTRY_MODE=system
```

Request a two-letter code through Android's Wi-Fi framework:

```ini
COUNTRY_MODE=request
COUNTRY_CODE=US
```

After editing the config, use the module's **Action** button in Magisk to apply it immediately and write a diagnostic report to `Download`.

## v1.3.0

- Wait for the Wi-Fi Binder service to become callable after boot.
- Retry transient `Failed transaction` errors.
- Read the country code back after applying.
- Log `SUCCESS` only when the requested code is actually active.
- Preserve an existing runtime config during upgrades.
- Create a default runtime config on a clean installation.

## Device validation

Validated on:

- Xiaomi device codename: `pudding`
- Android 16 / HyperOS
- Qualcomm WLAN: `qca_cld3_peach_v2`
- Native PHY reports EHT and `320MHz in 6GHz Supported`

Other devices may use different vendor properties, paths, HAL behavior, or country-code handling.

## Scope

The module does **not** patch Qualcomm regulatory databases and does not implement DFS/AFC or transmit-power bypass logic. The `REQUEST_*` keys are retained as unsupported diagnostic flags and do not activate those behaviors.

## License / responsibility

Source code is published for learning and research reference. You are responsible for testing, backups, device recovery, and compliance with all rules applicable to your hardware and location.
