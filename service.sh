#!/system/bin/sh
MODDIR=${0%/*}
. "$MODDIR/common.sh"
until [ "$(getprop sys.boot_completed)" = "1" ]; do sleep 2; done
log "service start v1.3.0"
apply_caps
apply_country
if [ "$VERBOSE_LOG" = "1" ]; then
  log "EHT disable=$(getprop persist.vendor.wlan.disable.eht)"
  log "MLO disable=$(getprop persist.vendor.wlan.disable.mlo)"
  log "country readback=$(wifi_country)"
  dumpsys wifi 2>/dev/null | grep -m4 -E 'mTelephonyCountryCode:|mOverrideCountryCode:|mDriverCountryCode:|mFrameworkCountryCode:' >> "$LOG"
  iw reg get 2>/dev/null | head -36 >> "$LOG"
fi
