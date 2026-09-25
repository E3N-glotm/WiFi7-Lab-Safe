#!/system/bin/sh
MODDIR=${0%/*}
. "$MODDIR/common.sh"

apply_capability_keepers
apply_country
APPLY_RC=$?
sleep 1

OUT=/storage/emulated/0/Download/WiFi7_Capability_status_$(date '+%Y%m%d_%H%M%S').txt

{
  echo 'WiFi 7 Capability Keeper v1.4.0'
  echo "Time: $(date '+%F %T %z')"
  echo "Device: $(getprop ro.product.device)"
  echo "Apply result: $([ "$APPLY_RC" -eq 0 ] && echo SUCCESS || echo FAILED) (rc=$APPLY_RC)"
  echo

  echo '=== Active config ==='
  cat "$CONF" 2>/dev/null
  echo

  echo '=== Country state ==='
  echo "Framework=$(framework_country)"
  echo "Driver=$(driver_country)"
  dumpsys wifi 2>/dev/null |
    grep -m8 -E 'mTelephonyCountryCode:|mOverrideCountryCode:|mDriverCountryCode:|mFrameworkCountryCode:'
  echo

  echo '=== Capability keepers ==='
  echo "persist.vendor.wlan.disable.eht=$(getprop persist.vendor.wlan.disable.eht)"
  echo "persist.vendor.wlan.disable.mlo=$(getprop persist.vendor.wlan.disable.mlo)"
  echo

  echo '=== Vendor capabilities ==='
  dump_vendor_caps
  echo

  echo '=== Channel summary ==='
  dump_channel_summary
  echo

  if [ "$EXPORT_CHANNEL_TABLE" = "1" ]; then
    echo '=== Regulatory state ==='
    iw reg get 2>/dev/null
    echo
    echo '=== PHY frequencies ==='
    iw phy 2>/dev/null |
      awk '
        /Band [0-9]+:/ {print; inband=1}
        inband && /Frequencies:/ {print; infreq=1; next}
        infreq && /^[[:space:]]*\*/ {print}
        infreq && $0 !~ /^[[:space:]]*\*/ && $0 ~ /^[[:space:]]*[A-Za-z]/ {infreq=0}
      '
    echo
  fi

  echo '=== Wi-Fi 7 markers ==='
  dump_wifi7_markers
  echo

  echo '=== Current link ==='
  iw dev wlan0 link 2>/dev/null
  echo
  echo '=== Interfaces ==='
  iw dev 2>/dev/null | grep -E 'Interface|type|txpower'
} > "$OUT" 2>&1

chmod 0644 "$OUT"
echo "Saved: $OUT"
exit "$APPLY_RC"
