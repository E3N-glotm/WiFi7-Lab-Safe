#!/system/bin/sh
MODDIR=${0%/*}
CONF=/data/adb/wifi7_lab_safe.conf
LOG=/data/adb/wifi7_lab_safe.log
VENDOR_CFG=/vendor/etc/wifi/peach_v2/WCNSS_qcom_cfg.ini

if [ ! -e "$CONF" ] && [ -r "$MODDIR/wifi7_lab_safe.conf" ]; then
  cp -f "$MODDIR/wifi7_lab_safe.conf" "$CONF"
  chmod 0644 "$CONF"
fi

[ -r "$CONF" ] && . "$CONF"

: "${COUNTRY_PROFILE:=SYSTEM}"
: "${COUNTRY_CODE:=CN}"
: "${KEEP_EHT:=1}"
: "${KEEP_MLO:=1}"
: "${CHECK_6GHZ_VENDOR_CAPABILITY:=1}"
: "${VERIFY_DRIVER_COUNTRY:=1}"
: "${COUNTRY_APPLY_RETRIES:=12}"
: "${COUNTRY_RETRY_DELAY_SEC:=2}"
: "${ENABLE_DIAGNOSTICS:=1}"
: "${VERBOSE_LOG:=1}"
: "${EXPORT_CHANNEL_TABLE:=1}"
: "${REQUEST_UNRESTRICTED_REGDOMAIN:=0}"
: "${REQUEST_FULL_TX_POWER:=0}"
: "${REQUEST_DISABLE_DFS_AFC:=0}"

log() {
  echo "$(date '+%F %T') $*" >> "$LOG"
}

upper() {
  echo "$1" | tr '[:lower:]' '[:upper:]'
}

valid_cc() {
  case "$1" in
    [A-Z][A-Z]) return 0 ;;
    *) return 1 ;;
  esac
}

framework_country() {
  cmd wifi get-country-code 2>/dev/null |
    sed -n 's/^Wifi Country Code = //p' |
    tail -1
}

driver_country() {
  iw reg get 2>/dev/null |
    awk '
      /phy#[0-9]+ \(self-managed\)/ { inphy=1; next }
      inphy && /^country [A-Z0-9][A-Z0-9]:/ {
        gsub(":", "", $2); print $2; exit
      }
    '
}

requested_country() {
  p=$(upper "$COUNTRY_PROFILE")
  case "$p" in
    SYSTEM) echo "" ;;
    US|CA|CN|JP) echo "$p" ;;
    CUSTOM)
      cc=$(upper "$COUNTRY_CODE")
      valid_cc "$cc" && echo "$cc"
      ;;
    *)
      cc=$(upper "$COUNTRY_CODE")
      valid_cc "$cc" && echo "$cc"
      ;;
  esac
}

wifi_service_ready() {
  service check wifi 2>/dev/null | grep -q 'found' || return 1
  cmd wifi get-country-code >/dev/null 2>&1 || return 1
  return 0
}

wait_wifi_ready() {
  n=0
  while [ "$n" -lt 30 ]; do
    wifi_service_ready && return 0
    n=$((n+1))
    sleep 1
  done
  return 1
}

apply_capability_keepers() {
  if [ "$KEEP_EHT" = "1" ]; then
    resetprop -n persist.vendor.wlan.disable.eht false
  fi
  if [ "$KEEP_MLO" = "1" ]; then
    resetprop -n persist.vendor.wlan.disable.mlo false
  fi

  if [ "$CHECK_6GHZ_VENDOR_CAPABILITY" = "1" ] && [ -r "$VENDOR_CFG" ]; then
    six=$(grep '^oem_6g_support_disable=' "$VENDOR_CFG" | tail -1 | cut -d= -f2)
    mlo=$(grep '^mlo_support_link_num=' "$VENDOR_CFG" | tail -1 | cut -d= -f2)
    twt=$(grep '^enable_twt=' "$VENDOR_CFG" | tail -1 | cut -d= -f2)
    nan=$(grep '^nan_feature_config=' "$VENDOR_CFG" | tail -1 | cut -d= -f2)
    tdls=$(grep '^gEnableTDLSSupport=' "$VENDOR_CFG" | tail -1 | cut -d= -f2)
    bf=$(grep '^gEnableTxSUBeamformer=' "$VENDOR_CFG" | tail -1 | cut -d= -f2)
    roam=$(grep '^FastRoamEnabled=' "$VENDOR_CFG" | tail -1 | cut -d= -f2)
    log "vendor caps: 6g_disable=${six:-unknown} mlo_links=${mlo:-unknown} twt=${twt:-unknown} nan=${nan:-unknown} tdls=${tdls:-unknown} su_bf=${bf:-unknown} fast_roam=${roam:-unknown}"
  fi

  [ "$REQUEST_UNRESTRICTED_REGDOMAIN" = "0" ] ||
    log "ignored legacy request: unrestricted regdomain"
  [ "$REQUEST_FULL_TX_POWER" = "0" ] ||
    log "ignored legacy request: full TX power"
  [ "$REQUEST_DISABLE_DFS_AFC" = "0" ] ||
    log "ignored legacy request: disable DFS/AFC"
}

country_matches() {
  want="$1"
  fw=$(upper "$(framework_country)")
  drv=$(upper "$(driver_country)")
  [ "$fw" = "$want" ] || return 1
  if [ "$VERIFY_DRIVER_COUNTRY" = "1" ]; then
    [ "$drv" = "$want" ] || return 1
  fi
  return 0
}

apply_country_once() {
  profile=$(upper "$COUNTRY_PROFILE")

  if [ "$profile" = "SYSTEM" ]; then
    out=$(cmd wifi force-country-code disabled 2>&1)
    rc=$?
    [ -n "$out" ] && log "country command: $out"
    return "$rc"
  fi

  want=$(requested_country)
  valid_cc "$want" || {
    log "ERROR invalid COUNTRY_PROFILE=$COUNTRY_PROFILE COUNTRY_CODE=$COUNTRY_CODE"
    return 64
  }

  out=$(cmd wifi force-country-code enabled "$want" 2>&1)
  rc=$?
  [ -n "$out" ] && log "country command: $out"
  [ "$rc" -eq 0 ] || return "$rc"

  sleep 1
  country_matches "$want" || return 65
  return 0
}

apply_country() {
  wait_wifi_ready || {
    log "ERROR Wi-Fi service not ready"
    return 70
  }

  i=1
  max="$COUNTRY_APPLY_RETRIES"
  [ "$max" -ge 1 ] 2>/dev/null || max=12

  while [ "$i" -le "$max" ]; do
    if apply_country_once; then
      fw=$(framework_country)
      drv=$(driver_country)
      log "SUCCESS country profile=$COUNTRY_PROFILE framework=${fw:-unknown} driver=${drv:-unknown} attempt=$i/$max"
      return 0
    fi

    rc=$?
    fw=$(framework_country)
    drv=$(driver_country)
    log "RETRY country profile=$COUNTRY_PROFILE code=$COUNTRY_CODE framework=${fw:-unknown} driver=${drv:-unknown} rc=$rc attempt=$i/$max"
    i=$((i+1))
    [ "$i" -le "$max" ] && sleep "$COUNTRY_RETRY_DELAY_SEC"
  done

  return 1
}

dump_vendor_caps() {
  [ -r "$VENDOR_CFG" ] || return 0
  echo "FastRoamEnabled=$(grep '^FastRoamEnabled=' "$VENDOR_CFG" | tail -1 | cut -d= -f2)"
  echo "SU_Beamformer=$(grep '^gEnableTxSUBeamformer=' "$VENDOR_CFG" | tail -1 | cut -d= -f2)"
  echo "6GHz_vendor_disable=$(grep '^oem_6g_support_disable=' "$VENDOR_CFG" | tail -1 | cut -d= -f2)"
  echo "TWT=$(grep '^enable_twt=' "$VENDOR_CFG" | tail -1 | cut -d= -f2)"
  echo "TWT_responder=$(grep '^twt_responder=' "$VENDOR_CFG" | tail -1 | cut -d= -f2)"
  echo "NAN=$(grep '^nan_feature_config=' "$VENDOR_CFG" | tail -1 | cut -d= -f2)"
  echo "TDLS=$(grep '^gEnableTDLSSupport=' "$VENDOR_CFG" | tail -1 | cut -d= -f2)"
  echo "MLO_links=$(grep '^mlo_support_link_num=' "$VENDOR_CFG" | tail -1 | cut -d= -f2)"
  echo "EHT_MLO_crypto=$(grep '^oem_eht_mlo_crypto_bitmap=' "$VENDOR_CFG" | tail -1 | cut -d= -f2)"
}

dump_channel_summary() {
  iw phy 2>/dev/null | awk '
    /Band 1:/ {band="2.4GHz"}
    /Band 2:/ {band="5GHz"}
    /Band 4:/ {band="6GHz"}
    /^[[:space:]]*\* [0-9]+ MHz/ {
      total[band]++
      if ($0 ~ /disabled/) disabled[band]++
      else enabled[band]++
      if ($0 ~ /radar detection/) dfs[band]++
    }
    END {
      for (i=1;i<=3;i++) {
        b=(i==1?"2.4GHz":(i==2?"5GHz":"6GHz"))
        printf "%s enabled=%d disabled=%d dfs=%d total=%d\n",
          b, enabled[b]+0, disabled[b]+0, dfs[b]+0, total[b]+0
      }
    }
  '
}

dump_wifi7_markers() {
  iw phy 2>/dev/null |
    grep -E 'EHT Iftypes|320MHz in 6GHz|HE160|MLO|MLD' |
    head -120
}
