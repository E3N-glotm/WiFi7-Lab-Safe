#!/system/bin/sh
MODDIR=${0%/*}
CONF=/data/adb/wifi7_lab_safe.conf

usage() {
  cat <<EOF
Usage:
  $0 <profile> [CC]          Set country profile: SYSTEM|US|CA|CN|JP|00|CUSTOM [CC]
  $0 tx <auto|fixed <mbm>>   Set TX power mode (fixed takes millibel, 24000 = 24 dBm)
  $0 wcnss <file.ini>        Stage a WCNSS override file into $MODDIR/wcnss/
  $0 regdb <file.bin>        Stage a replacement regdb.bin into the module
  $0 toggle <0|1>            Enable/disable the post-deploy Wi-Fi reload
  $0 reset                   Revert TX power / WCNSS overrides / regdb mount
  $0 show                    Print active capability controls
EOF
  exit 2
}

[ -r "$CONF" ] || cp -f "$MODDIR/wifi7_lab_safe.conf" "$CONF"

set_conf() {
  key=$1
  val=$2
  if grep -q "^${key}=" "$CONF"; then
    sed -i "s/^${key}=.*/${key}=${val}/" "$CONF"
  else
    echo "${key}=${val}" >> "$CONF"
  fi
}

cmd=$1
shift 2>/dev/null

case "$cmd" in
  SYSTEM|US|CA|CN|JP|00|system|us|ca|cn|jp)
    p=$(echo "$cmd" | tr '[:lower:]' '[:upper:]')
    set_conf COUNTRY_PROFILE "$p"
    echo "Saved profile: $p"
    echo "Run $MODDIR/action.sh to apply and export diagnostics."
    ;;
  CUSTOM|custom)
    cc=$(echo "$1" | tr '[:lower:]' '[:upper:]')
    case "$cc" in [A-Z][A-Z]|00) ;; *) usage ;; esac
    set_conf COUNTRY_PROFILE CUSTOM
    set_conf COUNTRY_CODE "$cc"
    echo "Saved profile: CUSTOM ($cc)"
    echo "Run $MODDIR/action.sh to apply and export diagnostics."
    ;;
  tx)
    case "$1" in
      auto|AUTO)
        set_conf TX_POWER_MODE auto
        echo "Saved TX_POWER_MODE=auto (regulatory domain controls TX power)"
        ;;
      fixed|FIXED)
        case "$2" in
          ''|*[!0-9]) usage ;;
        esac
        set_conf TX_POWER_MODE fixed
        set_conf TX_POWER_MBM "$2"
        echo "Saved TX_POWER_MODE=fixed TX_POWER_MBM=$2"
        ;;
      *) usage ;;
    esac
    echo "Run $MODDIR/action.sh to apply and export diagnostics."
    ;;
  wcnss)
    [ -f "$1" ] || { echo "ERROR file not found: $1"; exit 64; }
    case "$1" in
      *.ini) ;;
      *) echo "ERROR only .ini files can be staged"; exit 64 ;;
    esac
    mkdir -p "$MODDIR/wcnss"
    cp -f "$1" "$MODDIR/wcnss/$(basename "$1")"
    set_conf WCNSS_INJECT 1
    echo "Staged WCNSS override: $MODDIR/wcnss/$(basename "$1")"
    echo "Run $MODDIR/action.sh to deploy (add FORCE_WIFI_TOGGLE=1 in the conf for a driver reload)."
    ;;
  regdb)
    [ -f "$1" ] || { echo "ERROR file not found: $1"; exit 64; }
    cp -f "$1" "$MODDIR/regdb.bin"
    set_conf REGDB_MOUNT 1
    echo "Staged regdb replacement: $MODDIR/regdb.bin"
    echo "Run $MODDIR/action.sh to bind-mount (add FORCE_WIFI_TOGGLE=1 in the conf for a driver reload)."
    ;;
  toggle)
    case "$1" in
      0|1) set_conf FORCE_WIFI_TOGGLE "$1"
           echo "Saved FORCE_WIFI_TOGGLE=$1" ;;
      *) usage ;;
    esac
    ;;
  reset)
    . "$MODDIR/common.sh"
    revert_capability_controls
    echo "Reverted TX power / WCNSS overrides / regdb mount. Wi-Fi reload is optional:"
    echo "  $MODDIR/profile.sh toggle 1  (then action.sh)"
    ;;
  show)
    . "$MODDIR/common.sh"
    dump_capability_controls
    ;;
  *)
    usage
    ;;
esac

# Reflect the new state in Magisk immediately, without re-applying anything.
. "$MODDIR/common.sh"
refresh_module_description || true
