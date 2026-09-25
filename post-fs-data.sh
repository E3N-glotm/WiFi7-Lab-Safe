#!/system/bin/sh
MODDIR=${0%/*}
. "$MODDIR/common.sh"
log "post-fs-data start"
apply_caps
