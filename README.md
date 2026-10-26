# WiFi7-Lab-Safe · Wi-Fi 7 能力与监管域诊断

**语言：简体中文（当前） | [English](README_EN.md)**

面向 Xiaomi `pudding`、Qualcomm `peach_v2` 的 Magisk 无线功能研究模块。用于观察 EHT、MLO、6 GHz、320 MHz 相关能力，以及 Android Framework 与高通驱动对国家码的实际反馈。

**当前版本：v1.4.2** · [下载 Release](https://github.com/E3N-glotm/WiFi7-Lab-Safe/releases)

> [!CAUTION]
> **仅用于学习、研究及合规实验。** 使用无线频谱应遵守当地 DFS、AFC、信道、室内/室外及发射功率规定。仓库不提供绕过监管发射功率、禁用 DFS/AFC 或修改高通监管数据库的功能。

## 主要功能

- 检测已存在的 EHT（802.11be）/MLO 厂商属性，**只有接口存在才应用对应配置**，不凭空创建其他 ROM 没有的属性。
- 核查 6 GHz、320 MHz、TWT、NAN / Wi-Fi Aware、TDLS、漫游、波束成形和 MLO 等能力。
- 读取 Android Framework 与驱动/PHY 报告的国家码；输出信道、DFS 和 PHY 频率表。
- 支持 `SYSTEM`、`US`、`CA`、`CN`、`JP` 和自定义国家码请求，所有结果以设备驱动实际接受的状态为准。
- Wi-Fi Binder 短时故障会有限次数重试；不会保证不被无线固件拒绝。
- **Magisk 模块列表直接显示驱动上报国家码、系统国家码、请求配置及一致性状态**；启动和点击操作按钮后刷新，默认每 300 秒进行一次只读刷新。只有值发生变化时才更新显示。

## 配置与用法

运行时配置：`/data/adb/wifi7_lab_safe.conf`。默认仓库配置为：

```ini
COUNTRY_PROFILE=SYSTEM
COUNTRY_CODE=CN
KEEP_EHT=1
KEEP_MLO=1
VERIFY_DRIVER_COUNTRY=1
ENABLE_DIAGNOSTICS=1
COUNTRY_STATUS_REFRESH_SEC=300
REQUEST_UNRESTRICTED_REGDOMAIN=0
REQUEST_FULL_TX_POWER=0
REQUEST_DISABLE_DFS_AFC=0
```

Root 终端使用实际支持的配置文件与脚本：

```sh
sh /data/adb/modules/wifi7_lab_safe/profile.sh SYSTEM
sh /data/adb/modules/wifi7_lab_safe/profile.sh CN
sh /data/adb/modules/wifi7_lab_safe/action.sh
```

其他 `profile.sh` 国家参数仅在符合所在地要求时使用。检查诊断报告时，优先确认 Framework 与驱动是否一致；**界面显示 US 不等于 PHY 实际启用了 6 GHz 或 320 MHz**。

### Magisk 界面直接查看国家码（v1.4.2）

安装并重启后，进入 Magisk → 模块，模块说明会显示类似：

```text
驱动国家码:CN | 系统:CN | 请求:CN [一致]
```

- **驱动国家码**来自 `iw reg get` 中的 self-managed PHY 读取结果，不直接复制配置文件中的 `COUNTRY_CODE`。
- **系统**是 `cmd wifi get-country-code` 的返回值；**请求**表示模块的目标配置，`SYSTEM` 显示“系统自动”。
- 如果驱动和系统不同、请求尚未落实、或无法读取驱动，会分别显示“不一致”“请求未生效”“未验证”，不会把请求值假装成生效值。
- 默认 300 秒只读检查一次，不会定时重新应用国家码；可在 `/data/adb/wifi7_lab_safe.conf` 中设为 `COUNTRY_STATUS_REFRESH_SEC=0` 禁用轮询。修改国家配置后运行 `action.sh` 即可尝试应用并立即刷新。
- 若 Magisk 页面已打开，返回模块列表或重新进入以加载最新说明；**驱动上报国家码不等于实际可用信道、发射功率或 320 MHz 已获授权**，具体仍以操作按钮导出的 PHY 信道表和当地法规为准。

## 限制与回退

本模块不替换 `regdb.bin`、不合成监管域、不关闭 DFS/AFC、不强制超范围发射功率。启用能力开关不代表路由器、天线校准或监管域支持。禁用/卸载 Magisk 模块并重启可停止模块的后续配置行为。详细兼容性与迁移说明见 [英文文档](README_EN.md)。
