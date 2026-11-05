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
    fi
    ;;
  'dev wlan0')
    # match real iw layout: txpower is a standalone indented line
    printf 'Interface wlan0\n\ttxpower %s dBm\n' "${MOCK_TXPOWER:-30}"
    ;;
  'phy phy0')
    # set txpower is accepted by the mock; real self-managed PHYs may refuse
    exit 0
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
  grep -q '^version=v1.5.0$' "$TESTROOT/mod/module.prop"
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

# WCNSS override deployment: user keys must be appended to a copy of the
# vendor config under the (mocked) /data target, and listed in the manifest.
mkdir -p "$TESTROOT/vendor" "$TESTROOT/wcnss" "$TESTROOT/datavendor"
printf 'oem_6g_support_disable=0\nmlo_support_link_num=1\n' > "$TESTROOT/vendor/WCNSS_qcom_cfg.ini"
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
  cleanup_wcnss
  [ ! -e "$WCNSS_TARGET_DIR/WCNSS_qcom_cfg.ini" ] || exit 6
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

echo 'PASS: Magisk status displays real PHY/txpower readbacks, not forged values'
echo 'PASS: v1.5 capability layer (00 profile, legacy mapping, WCNSS deploy, regdb guard)'
