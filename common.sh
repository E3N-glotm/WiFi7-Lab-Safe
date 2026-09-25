#!/system/bin/sh
CONF=/data/adb/wifi7_lab_safe.conf
LOG=/data/adb/wifi7_lab_safe.log
MODDIR=${0%/*}
if [ ! -e "$CONF" ] && [ -r "$MODDIR/wifi7_lab_safe.conf" ]; then
  cp -f "$MODDIR/wifi7_lab_safe.conf" "$CONF"
  chmod 0644 "$CONF"
fi
[ -r "$CONF" ] && . "$CONF"

: "${ENABLE_EHT:=1}"
: "${ENABLE_MLO:=1}"
: "${ENABLE_6GHZ_VENDOR_CAPABILITY:=1}"
: "${ENABLE_DIAGNOSTICS:=1}"
: "${VERBOSE_LOG:=1}"
: "${COUNTRY_MODE:=system}"
: "${COUNTRY_CODE:=CN}"
: "${COUNTRY_APPLY_RETRIES:=12}"
: "${COUNTRY_RETRY_DELAY_SEC:=2}"
: "${REQUEST_UNRESTRICTED_REGDOMAIN:=0}"
: "${REQUEST_FULL_TX_POWER:=0}"
: "${REQUEST_DISABLE_DFS_AFC:=0}"

log(){ echo "$(date '+%F %T') $*" >> "$LOG"; }

wifi_country(){
  cmd wifi get-country-code 2>/dev/null | sed -n 's/^Wifi Country Code = //p' | tail -1
}

wifi_service_ready(){
  service check wifi 2>/dev/null | grep -q 'found' || return 1
  cmd wifi get-country-code >/dev/null 2>&1 || return 1
  return 0
}

wait_wifi_ready(){
  n=0
  while [ "$n" -lt 30 ]; do
    wifi_service_ready && return 0
    n=$((n+1))
    sleep 1
  done
  return 1
}

apply_country_once(){
  mode="$COUNTRY_MODE"
  case "$mode" in
    system)
      out=$(cmd wifi force-country-code disabled 2>&1); rc=$?
      [ -n "$out" ] && log "country command output: $out"
      [ "$rc" -eq 0 ] || return "$rc"
      return 0
      ;;
    request)
      CC=$(echo "$COUNTRY_CODE" | tr '[:lower:]' '[:upper:]')
      case "$CC" in
        [A-Z][A-Z]) ;;
        *) log "ERROR invalid COUNTRY_CODE='$COUNTRY_CODE'"; return 64 ;;
      esac
      out=$(cmd wifi force-country-code enabled "$CC" 2>&1); rc=$?
      [ -n "$out" ] && log "country command output: $out"
      [ "$rc" -eq 0 ] || return "$rc"
      sleep 1
      actual=$(wifi_country)
      [ "$actual" = "$CC" ] || return 65
      return 0
      ;;
    *) log "ERROR invalid COUNTRY_MODE='$COUNTRY_MODE'"; return 64 ;;
  esac
}

apply_country(){
  wait_wifi_ready || { log "ERROR Wi-Fi service not ready after timeout"; return 70; }
  i=1
  max="$COUNTRY_APPLY_RETRIES"
  [ "$max" -ge 1 ] 2>/dev/null || max=12
  while [ "$i" -le "$max" ]; do
    if apply_country_once; then
      actual=$(wifi_country)
      if [ "$COUNTRY_MODE" = "request" ]; then
        want=$(echo "$COUNTRY_CODE" | tr '[:lower:]' '[:upper:]')
        log "SUCCESS country request=$want actual=${actual:-unknown} attempt=$i/$max"
      else
        log "SUCCESS country override cleared actual=${actual:-unknown} attempt=$i/$max"
      fi
      return 0
    fi
    rc=$?
    actual=$(wifi_country)
    log "RETRY country mode=$COUNTRY_MODE requested=${COUNTRY_CODE:-none} actual=${actual:-unknown} rc=$rc attempt=$i/$max"
    i=$((i+1))
    [ "$i" -le "$max" ] && sleep "$COUNTRY_RETRY_DELAY_SEC"
  done
  actual=$(wifi_country)
  log "ERROR country apply failed requested=${COUNTRY_CODE:-none} actual=${actual:-unknown} attempts=$max"
  return 1
}

apply_caps(){
  [ "$ENABLE_EHT" = "1" ] && resetprop -n persist.vendor.wlan.disable.eht false
  [ "$ENABLE_MLO" = "1" ] && resetprop -n persist.vendor.wlan.disable.mlo false

  if [ "$ENABLE_6GHZ_VENDOR_CAPABILITY" = "1" ]; then
    CFG=/vendor/etc/wifi/peach_v2/WCNSS_qcom_cfg.ini
    if [ -r "$CFG" ]; then
      val=$(grep -m1 '^oem_6g_support_disable=' "$CFG" | cut -d= -f2)
      log "6GHz vendor capability value=${val:-unknown}; vendor file left unchanged"
    fi
  fi

  [ "$REQUEST_UNRESTRICTED_REGDOMAIN" = "0" ] || log "unsupported: unrestricted regulatory-domain bypass requested"
  [ "$REQUEST_FULL_TX_POWER" = "0" ] || log "unsupported: full TX-power bypass requested"
  [ "$REQUEST_DISABLE_DFS_AFC" = "0" ] || log "unsupported: DFS/AFC bypass requested"
}
