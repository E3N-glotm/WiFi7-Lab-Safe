#!/system/bin/sh
MODDIR=${0%/*}
. "$MODDIR/common.sh"
log "post-fs-data v1.5.1"
# Deploy file-level overrides before the WLAN driver starts so the first
# boot after install/update already sees them without any Wi-Fi reload:
#  - WCNSS_qcom_cfg.ini user override into /data/vendor/wifi/
#  - regdb.bin bind mount
# Country profile and TX power are applied in service.sh after boot
# completion, when the framework and nl80211 stack are up.
apply_capability_keepers
deploy_wcnss
mount_regdb
