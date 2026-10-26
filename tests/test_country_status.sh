#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TESTROOT=$(mktemp -d)
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
[ "$1 $2" = 'reg get' ] || exit 2
printf 'global\ncountry 00: DFS-UNSET\n'
if [ "${MOCK_DRIVER:-CN}" != "NONE" ]; then
  printf 'phy#0 (self-managed)\ncountry %s: DFS-FCC\n' "$MOCK_DRIVER"
fi
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
  grep -q '^version=v1.4.2$' "$TESTROOT/mod/module.prop"
  grep -q '^id=wifi7_lab_safe$' "$TESTROOT/mod/module.prop"
}

export MOCK_FRAMEWORK=CN MOCK_DRIVER=CN
check_description '驱动国家码:CN | 系统:CN | 请求:系统自动 [一致]'

# Same state must not modify module.prop or generate additional log records.
before=$(wc -l < "$TESTROOT/log")
sh "$TESTROOT/mod/probe.sh"
after=$(wc -l < "$TESTROOT/log")
[ "$before" -eq "$after" ]

MOCK_FRAMEWORK=US; MOCK_DRIVER=CN
export MOCK_FRAMEWORK MOCK_DRIVER
check_description '驱动国家码:CN | 系统:US | 请求:系统自动 [不一致]'

MOCK_DRIVER=NONE
export MOCK_DRIVER
check_description '驱动国家码:未知 | 系统:US | 请求:系统自动 [未验证]'

MOCK_DRIVER=US
export MOCK_DRIVER
printf 'COUNTRY_PROFILE=CN\nCOUNTRY_CODE=CN\n' > "$TESTROOT/config"
check_description '驱动国家码:US | 系统:US | 请求:CN [请求未生效]'

printf 'COUNTRY_PROFILE=US\nCOUNTRY_CODE=CN\n' > "$TESTROOT/config"
check_description '驱动国家码:US | 系统:US | 请求:US [一致]'

MOCK_DRIVER=00
export MOCK_DRIVER
check_description '驱动国家码:00(未指定) | 系统:US | 请求:US [未验证]'

echo 'PASS: Magisk status displays real PHY readback, not a forged configured country'
