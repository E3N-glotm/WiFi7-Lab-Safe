#!/system/bin/sh
MODDIR=${0%/*}
. "$MODDIR/common.sh"

until [ "$(getprop sys.boot_completed)" = "1" ]; do
  sleep 2
done

log "service start v1.4.0"
apply_capability_keepers
apply_country

if [ "$VERBOSE_LOG" = "1" ]; then
  log "EHT disable=$(getprop persist.vendor.wlan.disable.eht)"
  log "MLO disable=$(getprop persist.vendor.wlan.disable.mlo)"
  log "framework country=$(framework_country)"
  log "driver country=$(driver_country)"
  dumpsys wifi 2>/dev/null |
    grep -m8 -E 'mTelephonyCountryCode:|mOverrideCountryCode:|mDriverCountryCode:|mFrameworkCountryCode:' >> "$LOG"
  dump_channel_summary >> "$LOG"
fi
