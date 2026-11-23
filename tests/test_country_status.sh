#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TESTROOT=$(mktemp -d)
export TESTROOT
trap 'rm -rf "$TESTROOT"' EXIT HUP INT TERM
mkdir -p "$TESTROOT/mod" "$TESTROOT/bin"
cp "$ROOT/common.sh" "$ROOT/module.prop" "$TESTROOT/mod/"
printf 'COUNTRY_PROFILE=SYSTEM\nCOUNTRY_CODE=CN\n' > "$TESTROOT/config"

cat > "$TESTROOT/mod/probe.sh" <<'EOF'
#!/bin/sh
MODDIR=${0%/*}
. "$MODDIR/common.sh"
refresh_module_description
EOF

cat > "$TESTROOT/bin/cmd" <<'EOF'
#!/bin/sh
if [ "$1 $2" = 'wifi get-country-code' ]; then
  printf 'Wifi Country Code = %s\n' "${MOCK_FRAMEWORK:-CN}"
else
  exit 2
fi
EOF

cat > "$TESTROOT/bin/iw" <<'EOF'
#!/bin/sh
case "$1 $2" in
  'reg get')
    printf 'global\ncountry 00: DFS-UNSET\n'
    if [ "${MOCK_DRIVER:-CN}" != "NONE" ]; then
      printf 'phy#0 (self-managed)\ncountry %s: DFS-FCC\n' "$MOCK_DRIVER"
      if [ "$MOCK_DRIVER" = "US" ]; then
        # real US table shape including the 6 GHz ranges (regdb-derived)
        printf '\t(2402 - 2472 @ 40), (6, 30), (N/A), AUTO-BW\n'
        printf '\t(5170 - 5250 @ 80), (N/A, 24), (N/A), AUTO-BW\n'
        printf '\t(5490 - 5730 @ 160), (N/A, 24), (0 ms), DFS, AUTO-BW\n'
        printf '\t(5945 - 7105 @ 160), (N/A, 24), (N/A), AUTO-BW\n'
        printf '\t(5925 - 7105 @ 320), (N/A, 24), (N/A), NO-OUTDOOR, AUTO-BW\n'
      fi
    fi
    ;;
  'dev wlan0')
    # match real iw layout: txpower is a standalone indented line
    printf 'Interface wlan0\n\ttxpower %s dBm\n' "${MOCK_TXPOWER:-30}"
    ;;
  'phy phy0')
    # real self-managed qca_cld3 refuses with I/O error; MOCK_TXPOWER_SET=ok
    # simulates an nl80211-compliant PHY that accepts the write.
    if [ "${MOCK_TXPOWER_SET:-refuse}" = "refuse" ]; then
      printf 'command failed: I/O error (-5)\n' >&2
      exit 251
    fi
    exit 0
    ;;
  'phy ')
    # This device reports "Wiphy phy0" (NOT "phy#0") for bare `iw phy`,
    # with decimal MHz values in the band dump.
    printf 'Wiphy phy0\n\twiphy index: 0\n'
    printf '\tBand 1:\n\t\tFrequencies:\n'
    printf '\t\t\t* 2412.0 MHz [1] (30.0 dBm)\n'
    printf '\t\t\t* 2467.0 MHz [12] (disabled)\n'
    printf '\tBand 2:\n\t\tFrequencies:\n'
    printf '\t\t\t* 5180.0 MHz [36] (24.0 dBm)\n'
    printf '\t\t\t* 5620.0 MHz [124] (24.0 dBm) (radar detection)\n'
    printf '\tBand 4:\n\t\tFrequencies:\n'
    printf '\t\t\t* 5955.0 MHz [3] (24.0 dBm)\n'
    printf '\t\t\t* 7115.0 MHz [233] (disabled)\n'
    ;;
  *)
    exit 2
    ;;
esac
EOF
chmod +x "$TESTROOT/bin/cmd" "$TESTROOT/bin/iw" "$TESTROOT/mod/probe.sh"
export PATH="$TESTROOT/bin:$PATH"
export WIFI7_CONF="$TESTROOT/config"
export WIFI7_LOG="$TESTROOT/log"

check_description() {
  expected=$1
  sh "$TESTROOT/mod/probe.sh"
  actual=$(sed -n 's/^description=//p' "$TESTROOT/mod/module.prop")
  if [ "$actual" != "$expected" ]; then
    printf 'Expected: %s\nActual:   %s\n' "$expected" "$actual" >&2
    exit 1
  fi
  [ "$(grep -c '^description=' "$TESTROOT/mod/module.prop")" -eq 1 ]
  grep -q '^version=v1.5.1$' "$TESTROOT/mod/module.prop"
  grep -q '^id=wifi7_lab_safe$' "$TESTROOT/mod/module.prop"
}

export MOCK_FRAMEWORK=CN MOCK_DRIVER=CN
check_description '驱动:CN | 系统:CN | 请求:系统自动 | TX:30dBm [一致]'

# Same state must not modify module.prop or generate additional log records.
before=$(wc -l < "$TESTROOT/log")
sh "$TESTROOT/mod/probe.sh"
after=$(wc -l < "$TESTROOT/log")
[ "$before" -eq "$after" ]

MOCK_FRAMEWORK=US
export MOCK_FRAMEWORK
check_description '驱动:CN | 系统:US | 请求:系统自动 | TX:30dBm [不一致]'

MOCK_DRIVER=NONE
export MOCK_DRIVER
check_description '驱动:未知 | 系统:US | 请求:系统自动 | TX:30dBm [未验证]'

MOCK_DRIVER=US
export MOCK_DRIVER
printf 'COUNTRY_PROFILE=CN\nCOUNTRY_CODE=CN\n' > "$TESTROOT/config"
check_description '驱动:US | 系统:US | 请求:CN | TX:30dBm [请求未生效]'

printf 'COUNTRY_PROFILE=US\nCOUNTRY_CODE=CN\n' > "$TESTROOT/config"
check_description '驱动:US | 系统:US | 请求:US | TX:30dBm [一致]'

MOCK_DRIVER=00
export MOCK_DRIVER
# Driver readback 00 vs framework US: both valid, they disagree -> 不一致.
check_description '驱动:00(未指定) | 系统:US | 请求:US | TX:30dBm [不一致]'

# --- v1.5 capability-layer tests ---

# 00 (world) profile: requested_country must emit 00 and country_matches
# must accept a 00 driver readback.
printf 'COUNTRY_PROFILE=00\nCOUNTRY_CODE=CN\n' > "$TESTROOT/config"
REQ=$(sh -c '. "$TESTROOT/mod/common.sh"; requested_country')
[ "$REQ" = "00" ] || { echo "FAIL: requested_country for 00 profile returned '$REQ'"; exit 1; }

# Legacy v1.4 REQUEST_FULL_TX_POWER=1 must map to TX_POWER_MODE=fixed.
printf 'COUNTRY_PROFILE=US\nCOUNTRY_CODE=CN\nREQUEST_FULL_TX_POWER=1\n' > "$TESTROOT/config"
MODE=$(sh -c '. "$TESTROOT/mod/common.sh"; printf %s "$TX_POWER_MODE"')
[ "$MODE" = "fixed" ] || { echo "FAIL: legacy REQUEST_FULL_TX_POWER did not map to fixed, got '$MODE'"; exit 1; }

# Legacy REQUEST_UNRESTRICTED_REGDOMAIN=1 must map to COUNTRY_PROFILE=00.
printf 'COUNTRY_PROFILE=US\nCOUNTRY_CODE=CN\nREQUEST_UNRESTRICTED_REGDOMAIN=1\n' > "$TESTROOT/config"
REQ=$(sh -c '. "$TESTROOT/mod/common.sh"; requested_country')
[ "$REQ" = "00" ] || { echo "FAIL: legacy unrestricted regdomain did not map to 00, got '$REQ'"; exit 1; }

# WCNSS override deployment: user keys must be inserted BEFORE the vendor
# END marker (the qcacld parser ignores everything after END), under the
# mocked /data target, and listed in the manifest.
mkdir -p "$TESTROOT/vendor" "$TESTROOT/wcnss" "$TESTROOT/datavendor"
printf 'oem_6g_support_disable=0\nmlo_support_link_num=1\nEND\n' > "$TESTROOT/vendor/WCNSS_qcom_cfg.ini"
printf 'oem_6g_support_disable=1\ncustom_lab_key=42\n' > "$TESTROOT/wcnss/WCNSS_qcom_cfg.ini"
sh -c '
  WIFI7_CONF="$TESTROOT/config"
  WIFI7_LOG="$TESTROOT/log"
  export WCNSS_INJECT_DIR="$TESTROOT/wcnss"
  export WCNSS_TARGET_DIR="$TESTROOT/datavendor"
  . "$TESTROOT/mod/common.sh"
  VENDOR_CFG="$TESTROOT/vendor/WCNSS_qcom_cfg.ini"
  deploy_wcnss
  rc=$?
  [ "$rc" -eq 0 ] || exit 1
  grep -q "^custom_lab_key=42$" "$WCNSS_TARGET_DIR/WCNSS_qcom_cfg.ini" || exit 2
  last=$(grep "^oem_6g_support_disable=" "$WCNSS_TARGET_DIR/WCNSS_qcom_cfg.ini" | tail -1)
  [ "$last" = "oem_6g_support_disable=1" ] || exit 3
  grep -q "oem_6g_support_disable=0" "$WCNSS_TARGET_DIR/WCNSS_qcom_cfg.ini" || exit 4
  grep -qx "WCNSS_qcom_cfg.ini" "$WCNSS_TARGET_DIR/.wifi7_lab_safe_manifest" || exit 5
  # every user key must precede the END marker, or qcacld ignores it
  end_line=$(grep -n "^END$" "$WCNSS_TARGET_DIR/WCNSS_qcom_cfg.ini" | head -1 | cut -d: -f1)
  [ -n "$end_line" ] || exit 7
  key_line=$(grep -n "^custom_lab_key=42$" "$WCNSS_TARGET_DIR/WCNSS_qcom_cfg.ini" | head -1 | cut -d: -f1)
  [ "$key_line" -lt "$end_line" ] || exit 8
  cleanup_wcnss
  [ ! -e "$WCNSS_TARGET_DIR/WCNSS_qcom_cfg.ini" ] || exit 6
'

# DFS/AFC request: with REQUEST_DISABLE_DFS_AFC=1 and no user ini, the
# verified vendor DFS keys must still be deployed (before END).
mkdir -p "$TESTROOT/wcnss_empty" "$TESTROOT/datavendor2"
printf 'COUNTRY_PROFILE=US\nCOUNTRY_CODE=CN\nREQUEST_DISABLE_DFS_AFC=1\n' > "$TESTROOT/config"
sh -c '
  WIFI7_CONF="$TESTROOT/config"
  WIFI7_LOG="$TESTROOT/log"
  export WCNSS_INJECT=1
  export WCNSS_INJECT_DIR="$TESTROOT/wcnss_empty"
  export WCNSS_TARGET_DIR="$TESTROOT/datavendor2"
  . "$TESTROOT/mod/common.sh"
  VENDOR_CFG="$TESTROOT/vendor/WCNSS_qcom_cfg.ini"
  deploy_wcnss
  grep -q "^gEnableDFSMasterCap=0$" "$WCNSS_TARGET_DIR/WCNSS_qcom_cfg.ini" || exit 1
  end_line=$(grep -n "^END$" "$WCNSS_TARGET_DIR/WCNSS_qcom_cfg.ini" | head -1 | cut -d: -f1)
  dfs_line=$(grep -n "^gEnableDFSMasterCap=0$" "$WCNSS_TARGET_DIR/WCNSS_qcom_cfg.ini" | head -1 | cut -d: -f1)
  [ "$dfs_line" -lt "$end_line" ] || exit 2
'

# regdb bind mount is skipped cleanly when no replacement file is staged.
sh -c '
  WIFI7_CONF="$TESTROOT/config"
  WIFI7_LOG="$TESTROOT/log"
  export REGDB_SRC="$TESTROOT/missing-regdb.bin"
  export REGDB_MOUNT_FLAG="$TESTROOT/regdb_flag"
  . "$TESTROOT/mod/common.sh"
  mount_regdb
  rc=$?
  [ "$rc" -eq 0 ] || exit 1
  [ ! -e "$REGDB_MOUNT_FLAG" ] || exit 2
'

# regdb target detection must find the board-directory layout used by this
# device (/vendor/firmware_mnt/image/<board>/regdb.bin), not just generic paths.
mkdir -p "$TESTROOT/fw_mnt/peach"
: > "$TESTROOT/fw_mnt/peach/regdb.bin"
FOUND=$(sh -c '
  WIFI7_CONF="$TESTROOT/config"
  WIFI7_LOG="$TESTROOT/log"
  export REGDB_SEARCH_GLOBS="$TESTROOT/fw_mnt/*/regdb.bin"
  . "$TESTROOT/mod/common.sh"
  detect_regdb_path
')
case "$FOUND" in
  */peach/regdb.bin) : ;;
  *) echo "FAIL: detect_regdb_path missed board dir layout, got '$FOUND'"; exit 1 ;;
esac

# first_phy must accept this device's "Wiphy phy0" spelling (TX control was
# silently skipped while only phy#0 was recognized).
PHY=$(sh -c '. "$TESTROOT/mod/common.sh"; first_phy')
[ "$PHY" = "phy0" ] || { echo "FAIL: first_phy returned '$PHY' for Wiphy phy0 output"; exit 1; }

# TX fixed power: the refusal from the self-managed PHY is logged, not hidden,
# and apply_tx_power must actually reach the iw call (phy detected).
printf 'COUNTRY_PROFILE=US\nCOUNTRY_CODE=CN\nTX_POWER_MODE=fixed\nTX_POWER_MBM=27000\n' > "$TESTROOT/config"
sh -c '
  WIFI7_CONF="$TESTROOT/config"
  WIFI7_LOG="$TESTROOT/txlog"
  . "$TESTROOT/mod/common.sh"
  apply_tx_power
  rc=$?
  [ "$rc" -ne 0 ] || exit 1
  grep -q "txpower fixed 27000 millibel rejected" "$TESTROOT/txlog" || exit 2
  ! grep -q "cannot detect phy index" "$TESTROOT/txlog" || exit 3
'

# channel summary must count the real decimal-MHz dump ("* 2412.0 MHz").
SUMMARY=$(sh -c '. "$TESTROOT/mod/common.sh"; dump_channel_summary')
echo "$SUMMARY" | grep -q "2.4GHz enabled=1 disabled=1 dfs=0 total=2" || {
  echo "FAIL: channel summary wrong for decimal MHz lines:"; echo "$SUMMARY"; exit 1; }
echo "$SUMMARY" | grep -q "5GHz enabled=2 disabled=0 dfs=1 total=2" || {
  echo "FAIL: 5GHz DFS line wrong:"; echo "$SUMMARY"; exit 1; }

# regulatory power ceiling report: 5945-7105 is 6 GHz, not 5 GHz.
POWER=$(sh -c '. "$TESTROOT/mod/common.sh"; MOCK_DRIVER=US dump_regulatory_power')
echo "$POWER" | grep -q "6GHz" || { echo "FAIL: 6GHz rows missing"; echo "$POWER"; exit 1; }
echo "$POWER" | grep "5945" | grep -q "6GHz" || { echo "FAIL: 5945 misclassified"; echo "$POWER"; exit 1; }

echo 'PASS: Magisk status displays real PHY/txpower readbacks, not forged values'
echo 'PASS: v1.5 capability layer (00 profile, legacy mapping, WCNSS deploy, regdb guard)'
echo 'PASS: v1.5.1 fixes (END-marker injection, DFS keys, board regdb path, Wiphy phy0, decimal MHz stats, 6GHz power rows)'
