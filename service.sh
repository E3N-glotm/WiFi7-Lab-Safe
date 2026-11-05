#!/system/bin/sh
MODDIR=${0%/*}
. "$MODDIR/common.sh"

until [ "$(getprop sys.boot_completed)" = "1" ]; do
  sleep 2
done

log "service start v1.5.0"
apply_capability_keepers
apply_country
apply_capability_controls
refresh_module_description || log "WARN cannot update Magisk module status"

if [ "$VERBOSE_LOG" = "1" ]; then
  log "EHT disable=$(getprop persist.vendor.wlan.disable.eht)"
  log "MLO disable=$(getprop persist.vendor.wlan.disable.mlo)"
  log "framework country=$(framework_country)"
  log "driver country=$(driver_country)"
  log "txpower readback=$(iface_txpower_dbm) dBm (mode=$TX_POWER_MODE)"
  dumpsys wifi 2>/dev/null |
    grep -m8 -E 'mTelephonyCountryCode:|mOverrideCountryCode:|mDriverCountryCode:|mFrameworkCountryCode:' >> "$LOG"
  dump_channel_summary >> "$LOG"
  dump_capability_controls >> "$LOG"
fi

# Refresh the readback only; NEVER reapply controls in this loop.
# The 5-minute default adds no high-frequency polling and only writes when
# the actual displayed state changes. Set 0 to disable periodic refresh.
case "$COUNTRY_STATUS_REFRESH_SEC" in
  ''|*[!0-9]*) COUNTRY_STATUS_REFRESH_SEC=300 ;;
esac
if [ "$COUNTRY_STATUS_REFRESH_SEC" -gt 0 ]; then
  [ "$COUNTRY_STATUS_REFRESH_SEC" -ge 60 ] || COUNTRY_STATUS_REFRESH_SEC=60
  while [ -e "$MODDIR/module.prop" ] && [ ! -e "$MODDIR/disable" ]; do
    sleep "$COUNTRY_STATUS_REFRESH_SEC"
    [ -e "$MODDIR/disable" ] && break
    refresh_module_description || log "WARN refresh country readback failed"
  done
fi
