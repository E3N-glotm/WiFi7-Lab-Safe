#!/system/bin/sh
MODDIR=${0%/*}
. "$MODDIR/common.sh"
log "post-fs-data v1.4.2"
apply_capability_keepers
