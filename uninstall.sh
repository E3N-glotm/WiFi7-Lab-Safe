#!/system/bin/sh
MODDIR=${0%/*}
# Full revert of every v1.5 control before Magisk removes the module:
#  - TX power back to auto (regulatory domain controls power again)
#  - remove deployed WCNSS_qcom_cfg.ini overrides from /data/vendor/wifi/
#  - unmount any regdb.bin bind mount
# The user's country override is also cleared so the device returns to
# system-controlled country on next boot.
. "$MODDIR/common.sh" 2>/dev/null

revert_capability_controls 2>/dev/null

cmd wifi force-country-code disabled >/dev/null 2>&1

rm -f /data/adb/wifi7_lab_safe.conf
rm -f /data/adb/wifi7_lab_safe.log
rm -f /data/adb/wifi7_lab_safe.regdb_mounted
