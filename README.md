# WiFi7-Lab · Wi-Fi 7 全能力实验室模块

**语言：简体中文（当前） | [English](README_EN.md)**

面向 Xiaomi `pudding`、Qualcomm `peach_v2` 的 Magisk 无线功能实验室模块。v1.5 起从"只读诊断"升级为**全能力开放 + 全参数可调**：监管域（任意 ISO 国家码 / 00 世界域）、发射功率（自动 / 固定 dBm）、WCNSS 驱动配置覆盖、regdb 监管数据库替换，全部做成可配置项，随时修改、随时回滚，**不锁死在任何参数上**。

**当前版本：v1.5.0** · [下载 Release](https://github.com/E3N-glotm/WiFi7-Lab-Safe/releases)

> [!CAUTION]
> **仅用于学习、研究及合规实验。** 开放所有能力后，使用无线频谱应自行遵守当地 DFS、AFC、信道、室内/室外及发射功率规定。模块只负责把能力和参数交到你的手里，最终生效以驱动实际接受的状态为准——诊断导出里的每个数值都是**实时回读**，不是配置文件的回显。

## v1.5 能力层（全部可配置、可回滚）

| 控制项 | 配置键 | 说明 |
| --- | --- | --- |
| 监管域 / 国家码 | `COUNTRY_PROFILE` | `SYSTEM` / `US` / `CA` / `CN` / `JP` / `00`（世界域）/ `CUSTOM` + `COUNTRY_CODE`。哪些 6 GHz / 320 MHz / DFS 信道存在，由所选国家的监管数据库决定 |
| 发射功率 | `TX_POWER_MODE` / `TX_POWER_MBM` | `auto` = 交给监管域/驱动；`fixed` = 用 nl80211 强制固定功率（millibel，100 = 1 dB，24000 = 24 dBm）。自管理 PHY 可能拒绝/钳位，一切以回读为准 |
| WCNSS 驱动配置 | `WCNSS_INJECT` | 把 `$MODDIR/wcnss/*.ini` 合并到 `/data/vendor/wifi/`（qcacld 驱动优先读取的路径），覆盖单个键而不重建整个文件；用户键追加在 vendor 文件之后（后者生效） |
| regdb 监管数据库 | `REGDB_MOUNT` + `$MODDIR/regdb.bin` | 将自定义 `regdb.bin` bind-mount 到检测到的 vendor 路径之上——**直接改监管信道/功率表的底层方式**。vendor 分区原文件永不修改，卸载即还原 |
| 驱动重载（免重启） | `FORCE_WIFI_TOGGLE` | WCNSS/regdb 改动后 Wi-Fi 开关一次让驱动重读配置（只断 Wi-Fi，不断蜂窝/以太网，不重启）；留 0 则下次开机生效 |
| EHT / MLO / 6 GHz 厂商开关 | `KEEP_EHT` / `KEEP_MLO` | 仅当 ROM 暴露对应属性时才应用，不凭空创建 |

默认配置给**最开放的合理基线**（`COUNTRY_PROFILE=US` 保证 6 GHz / 320 MHz 在监管域内），其余能力开关默认打开但保持安全（`TX_POWER_MODE=auto`、`FORCE_WIFI_TOGGLE=0`）。想怎么调就改 `/data/adb/wifi7_lab_safe.conf` 或用 `profile.sh`，然后 `action.sh` 立即生效并导出诊断。

## 主要功能

- 检测已存在的 EHT（802.11be）/MLO 厂商属性，**只有接口存在才应用对应配置**，不凭空创建其他 ROM 没有的属性。
- 核查 6 GHz、320 MHz、TWT、NAN / Wi-Fi Aware、TDLS、漫游、波束成形和 MLO 等能力。
- 读取 Android Framework 与驱动/PHY 报告的国家码；输出信道、DFS 和 PHY 频率表。
- 支持 `SYSTEM`、`US`、`CA`、`CN`、`JP`、`00`（世界域）和自定义国家码请求，所有结果以设备驱动实际接受的状态为准。
- **Magisk 模块列表直接显示驱动国家码、系统国家码、请求配置、TX 功率回读及一致性状态**；启动和点击操作按钮后刷新，默认每 300 秒进行一次只读刷新。只有值发生变化时才更新显示。

## 配置与用法

运行时配置：`/data/adb/wifi7_lab_safe.conf`。默认仓库配置为：

```ini
COUNTRY_PROFILE=US
COUNTRY_CODE=CN
KEEP_EHT=1
KEEP_MLO=1
VERIFY_DRIVER_COUNTRY=1
ENABLE_DIAGNOSTICS=1
COUNTRY_STATUS_REFRESH_SEC=300
TX_POWER_MODE=auto
TX_POWER_MBM=24000
WCNSS_INJECT=1
REGDB_MOUNT=1
FORCE_WIFI_TOGGLE=0
REQUEST_UNRESTRICTED_REGDOMAIN=0
REQUEST_FULL_TX_POWER=0
REQUEST_DISABLE_DFS_AFC=0
```

Root 终端使用实际支持的配置文件与脚本：

```sh
# 国家 / 监管域
sh /data/adb/modules/wifi7_lab_safe/profile.sh US
sh /data/adb/modules/wifi7_lab_safe/profile.sh 00
sh /data/adb/modules/wifi7_lab_safe/profile.sh CUSTOM US

# 发射功率
sh /data/adb/modules/wifi7_lab_safe/profile.sh tx auto
sh /data/adb/modules/wifi7_lab_safe/profile.sh tx fixed 27000    # 27 dBm

# WCNSS 覆盖 / regdb 替换
sh /data/adb/modules/wifi7_lab_safe/profile.sh wcnss /sdcard/Download/my_keys.ini
sh /data/adb/modules/wifi7_lab_safe/profile.sh regdb /sdcard/Download/regdb.bin

# 驱动重载开关
sh /data/adb/modules/wifi7_lab_safe/profile.sh toggle 1

# 回滚（TX 功率 / WCNSS / regdb 全部还原）
sh /data/adb/modules/wifi7_lab_safe/profile.sh reset

# 查看当前能力控制状态
sh /data/adb/modules/wifi7_lab_safe/profile.sh show

# 应用并导出诊断
sh /data/adb/modules/wifi7_lab_safe/action.sh
```

检查诊断报告时，优先确认 Framework 与驱动是否一致；**界面显示 US 不等于 PHY 实际启用了 6 GHz 或 320 MHz，TX 回读也不等于监管域允许的最大功率**——具体以导出的 PHY 信道表和当地法规为准。

### Magisk 界面直接查看（v1.5）

安装并重启后，进入 Magisk → 模块，模块说明会显示类似：

```text
驱动:US | 系统:US | 请求:US | TX:30dBm [一致]
```

- **驱动**来自 `iw reg get` 中的 self-managed PHY 读取结果，不直接复制配置文件。
- **系统**是 `cmd wifi get-country-code` 的返回值；**请求**表示模块的目标配置，`SYSTEM` 显示"系统自动"，`00` 显示"00(未指定)"。
- **TX** 是 nl80211 接口实时回读的发射功率（dBm）。
- 如果驱动和系统不同、请求尚未落实、或无法读取驱动，会分别显示"不一致""请求未生效""未验证"，不会把请求值假装成生效值。
- 默认 300 秒只读检查一次，不会定时重新应用配置；可设为 `COUNTRY_STATUS_REFRESH_SEC=0` 禁用轮询。

## 限制与回退

v1.5 提供的是**能力与参数的完整控制权**：可请求世界域（00）、可强制固定发射功率、可用 WCNSS 覆盖和 regdb bind-mount 改变驱动看到的监管表。这些操作都是可逆的：

- `profile.sh reset` 还原 TX 功率 / WCNSS 覆盖 / regdb 挂载。
- `uninstall.sh`（随卸载自动执行）完整回滚上述全部控制并清除国家码 override。
- vendor 分区文件（WCNSS、regdb.bin）从不被直接写入，覆盖走 `/data/vendor/wifi/` 与 bind-mount，卸载即还原。

启用能力开关不代表路由器、天线校准或监管域支持；**超范围发射、禁用 DFS/AFC 的后果由使用者承担**。详细兼容性与迁移说明见 [英文文档](README_EN.md)。
