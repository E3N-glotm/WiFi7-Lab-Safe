#!/system/bin/sh
MODDIR=${0%/*}
. "$MODDIR/common.sh"

apply_caps
apply_country
APPLY_RC=$?
sleep 1

OUT=/storage/emulated/0/Download/WiFi7_Lab_Safe_status_$(date '+%Y%m%d_%H%M%S').txt
{
  echo 'WiFi 7 Lab Capability Keeper v1.3.0'
  echo "Time: $(date '+%F %T %z')"
  echo "Device: $(getprop ro.product.device)"
  echo "Apply result: $([ "$APPLY_RC" -eq 0 ] && echo SUCCESS || echo FAILED) (rc=$APPLY_RC)"
  echo

  echo '=== Active config ==='
  cat /data/adb/wifi7_lab_safe.conf 2>/dev/null
  echo

  echo '=== Framework country code ==='
  cmd wifi get-country-code 2>/dev/null
  dumpsys wifi 2>/dev/null | grep -m8 -E 'mTelephonyCountryCode:|mOverrideCountryCode:|mDriverCountryCode:|mFrameworkCountryCode:'
  echo

  echo '=== Capability state ==='
  echo "persist.vendor.wlan.disable.eht=$(getprop persist.vendor.wlan.disable.eht)"
  echo "persist.vendor.wlan.disable.mlo=$(getprop persist.vendor.wlan.disable.mlo)"
  grep -n -E '^(oem_6g_support_disable|mlo_support_link_num|gCountryCodePriority)=' /vendor/etc/wifi/peach_v2/WCNSS_qcom_cfg.ini 2>/dev/null
  echo

  echo '=== Regulatory state ==='
  iw reg get 2>/dev/null
  echo

  echo '=== 6 GHz / EHT capability ==='
  iw phy 2>/dev/null | grep -E 'Band [0-9]+:|320MHz in 6GHz|59[0-9][0-9] MHz|6[0-9]{3} MHz|EHT Iftypes|MLO|MLD' | head -260
  echo

  echo '=== Current link ==='
  iw dev wlan0 link 2>/dev/null
} > "$OUT" 2>&1

chmod 0644 "$OUT"
echo "Saved: $OUT"
exit "$APPLY_RC"
