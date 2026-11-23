#!/system/bin/sh
# WiFi7-Lab v1.5.0 common library
# Full-capability lab controls: country forcing, TX power, WCNSS override,
# regdb bind-mount. Every control is config-driven and reversible.
MODDIR=${0%/*}
CONF=${WIFI7_CONF:-/data/adb/wifi7_lab_safe.conf}
LOG=${WIFI7_LOG:-/data/adb/wifi7_lab_safe.log}
VENDOR_CFG=${VENDOR_CFG:-/vendor/etc/wifi/peach_v2/WCNSS_qcom_cfg.ini}
WCNSS_TARGET_DIR=${WCNSS_TARGET_DIR:-/data/vendor/wifi}
INJECT_DIR=${WCNSS_INJECT_DIR:-$MODDIR/wcnss}
REGDB_SRC=${REGDB_REPLACE:-$MODDIR/regdb.bin}
REGDB_MOUNT_FLAG=${REGDB_MOUNT_FLAG:-/data/adb/wifi7_lab_safe.regdb_mounted}
WCNSS_MANIFEST=$WCNSS_TARGET_DIR/.wifi7_lab_safe_manifest

if [ ! -e "$CONF" ] && [ -r "$MODDIR/wifi7_lab_safe.conf" ]; then
  cp -f "$MODDIR/wifi7_lab_safe.conf" "$CONF"
  chmod 0644 "$CONF"
fi

[ -r "$CONF" ] && . "$CONF"

: "${COUNTRY_PROFILE:=US}"
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
: "${COUNTRY_STATUS_REFRESH_SEC:=300}"
# v1.5 capability controls (all optional, all reversible):
# TX_POWER_MODE: auto = leave TX power to the regulatory domain/driver
#                fixed = force a fixed nl80211 TX power
# TX_POWER_MBM:  fixed power in millibel, 100 = 1 dB (24000 = 24 dBm)
: "${TX_POWER_MODE:=auto}"
: "${TX_POWER_MBM:=24000}"
# WCNSS_INJECT: 1 = deploy user-edited WCNSS_qcom_cfg.ini from $INJECT_DIR
# into /data/vendor/wifi/ (standard Qualcomm driver override path),
# merged on top of the vendor file so untouched keys keep working.
: "${WCNSS_INJECT:=1}"
# REGDB_MOUNT: 1 = bind-mount $REGDB_SRC over the detected vendor regdb.bin
: "${REGDB_MOUNT:=1}"
# FORCE_WIFI_TOGGLE: 1 = toggle Wi-Fi after WCNSS/regdb deployment so the
# driver re-reads configuration without a reboot.
: "${FORCE_WIFI_TOGGLE:=0}"
# Legacy v1.4 keys retained so old configs remain readable; when set they
# map onto the v1.5 controls below.
: "${REQUEST_UNRESTRICTED_REGDOMAIN:=0}"
: "${REQUEST_FULL_TX_POWER:=0}"
: "${REQUEST_DISABLE_DFS_AFC:=0}"

# Legacy intent mapping: the old "request" flags now mean real actions.
if [ "$REQUEST_UNRESTRICTED_REGDOMAIN" != "0" ]; then
  COUNTRY_PROFILE=00
fi
if [ "$REQUEST_FULL_TX_POWER" != "0" ]; then
  TX_POWER_MODE=fixed
fi

log() {
  echo "$(date '+%F %T') $*" >> "$LOG"
}

upper() {
  echo "$1" | tr '[:lower:]' '[:upper:]'
}

valid_cc() {
  case "$1" in
    [A-Z][A-Z]) return 0 ;;
    00) return 0 ;;
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

display_country() {
  cc=$(upper "$1")
  case "$cc" in
    [A-Z][A-Z]) printf '%s' "$cc" ;;
    00) printf '00(未指定)' ;;
    *) printf '未知' ;;
  esac
}

first_phy() {
  # iw phy prints "Wiphy phy<N>" on this device; older iw builds print
  # "phy#<N>". Accept both so TX control is not silently skipped.
  iw phy 2>/dev/null | awk '
    /^Wiphy phy[0-9]+/ { print $2; exit }
    /^phy#[0-9]+/ { sub(/^phy#/, "phy"); print $1; exit }
  '
}

iface_txpower_dbm() {
  iw dev wlan0 info 2>/dev/null | awk '/txpower/ {print $2; exit}'
}

tx_power_label() {
  v=$(iface_txpower_dbm)
  case "$v" in
    ''|*[!0-9.]*) printf 'N/A' ;;
    *) printf '%sdBm' "$v" ;;
  esac
}

apply_tx_power() {
  # TX power control is request-and-verify: the self-managed PHY may refuse
  # nl80211 txpower writes. The readback value is always reported as-is.
  case "$(upper "$TX_POWER_MODE")" in
    AUTO|'')
      # Actively restore driver-managed power when switching back from a
      # previously forced value. A refusal here usually means the PHY never
      # accepted a fixed override in the first place; log, do not fail.
      phy=$(first_phy)
      if [ -n "$phy" ]; then
        out=$(iw phy "$phy" set txpower auto 2>&1)
        rc=$?
        if [ "$rc" -ne 0 ]; then
          log "note txpower auto not re-applied on $phy (rc=$rc): $out"
        else
          log "SUCCESS txpower auto restored on $phy, readback=$(iface_txpower_dbm)"
        fi
      fi
      return 0
      ;;
    FIXED)
      case "$TX_POWER_MBM" in
        ''|*[!0-9]*)
          log "ERROR invalid TX_POWER_MBM=$TX_POWER_MBM (expect integer millibel, 24000 = 24 dBm)"
          return 64
          ;;
      esac
      phy=$(first_phy)
      [ -n "$phy" ] || { log "ERROR cannot detect phy index"; return 65; }
      out=$(iw phy "$phy" set txpower fixed "$TX_POWER_MBM" 2>&1)
      rc=$?
      [ -n "$out" ] && log "txpower command: $out"
      if [ "$rc" -ne 0 ]; then
        log "WARN txpower fixed $TX_POWER_MBM millibel rejected by nl80211 (rc=$rc), readback=$(iface_txpower_dbm)"
        return "$rc"
      fi
      sleep 1
      log "SUCCESS txpower fixed requested=$TX_POWER_MBM millibel readback=$(iface_txpower_dbm)"
      return 0
      ;;
    *)
      log "ERROR unknown TX_POWER_MODE=$TX_POWER_MODE (auto|fixed)"
      return 64
      ;;
  esac
}

reset_tx_power() {
  phy=$(first_phy)
  if [ -n "$phy" ]; then
    out=$(iw phy "$phy" set txpower auto 2>&1)
    rc=$?
    if [ "$rc" -eq 0 ]; then
      log "reset txpower to auto on $phy"
    else
      log "reset txpower auto refused on $phy (rc=$rc): $out"
    fi
  fi
  return 0
}

# Deploy user-edited WCNSS keys. The qcacld driver reads
# /data/vendor/wifi/WCNSS_qcom_cfg.ini ahead of the read-only vendor path,
# so this shadows vendor configuration without touching any partition.
# The vendor ini ends with an END marker and the qcacld parser ignores
# anything after it, so user keys are inserted immediately BEFORE END
# (or appended when the vendor file has no END marker).

dfs_afc_active() {
  case "$(upper "$REQUEST_DISABLE_DFS_AFC")" in
    1|TRUE|YES) return 0 ;;
    *) return 1 ;;
  esac
}

# DFS/AFC request keys. Every key below was verified to exist in this
# device's vendor WCNSS cfg and the values follow the vendor-file comments.
# The driver keeps final discretion over actual DFS/AFC enforcement.
dfs_afc_keys() {
  printf '# WiFi7-Lab DFS/AFC request (driver decides final enforcement)\n'
  printf 'gEnableDFSMasterCap=0\n'
  printf 'discardDFSchannelforMode=0\n'
  printf 'gSkipDfsChannelInP2pSearch=0\n'
  printf 'gAllowDFSChannelRoam=1\n'
}

merge_wcnss_target() {
  base=$1
  override=$2
  tmp="$WCNSS_TARGET_DIR/.$base.merge.$$"
  if [ -r "$VENDOR_CFG" ]; then
    if ! awk -v USER_INI="$override" '
      BEGIN { inserted = 0 }
      /^[[:space:]]*END[[:space:]]*$/ && !inserted {
        print "# --- WiFi7-Lab overrides (inserted before END) ---"
        while ((getline line < USER_INI) > 0) print line
        close(USER_INI)
        inserted = 1
      }
      { print }
      END {
        if (!inserted) {
          print "# --- WiFi7-Lab overrides ---"
          while ((getline line < USER_INI) > 0) print line
          close(USER_INI)
        }
      }
    ' "$VENDOR_CFG" > "$tmp"; then
      rm -f "$tmp"
      log "ERROR WCNSS merge failed for $base"
      return 1
    fi
    mv -f "$tmp" "$WCNSS_TARGET_DIR/$base"
  else
    cp -f "$override" "$WCNSS_TARGET_DIR/$base" \
      || { log "WARN failed to deploy $base"; return 1; }
  fi
  chmod 0644 "$WCNSS_TARGET_DIR/$base"
  if ! grep -qx "$base" "$WCNSS_MANIFEST" 2>/dev/null; then
    echo "$base" >> "$WCNSS_MANIFEST"
  fi
  log "deployed WCNSS override: $base -> $WCNSS_TARGET_DIR/"
  return 0
}

deploy_wcnss() {
  if [ "$WCNSS_INJECT" != "1" ]; then
    dfs_afc_active && log "note: REQUEST_DISABLE_DFS_AFC requires WCNSS_INJECT=1"
    log "WCNSS inject disabled by config"
    return 0
  fi
  mkdir -p "$WCNSS_TARGET_DIR"
  found=0
  if [ -d "$INJECT_DIR" ]; then
    for f in "$INJECT_DIR"/*.ini; do
      [ -f "$f" ] || continue
      case "$(basename "$f")" in
        *.example) continue ;;
      esac
      found=1
      base=$(basename "$f")
      combined="$WCNSS_TARGET_DIR/.$base.combined.$$"
      cat "$f" > "$combined"
      if dfs_afc_active && [ "$base" = "WCNSS_qcom_cfg.ini" ]; then
        dfs_afc_keys >> "$combined"
      fi
      merge_wcnss_target "$base" "$combined" || { rm -f "$combined"; continue; }
      rm -f "$combined"
    done
  fi
  # DFS/AFC requested but no user file carried the keys: deploy them alone.
  if dfs_afc_active && [ ! -e "$WCNSS_TARGET_DIR/WCNSS_qcom_cfg.ini" ]; then
    keys="$WCNSS_TARGET_DIR/.dfs_keys.$$"
    dfs_afc_keys > "$keys"
    if merge_wcnss_target "WCNSS_qcom_cfg.ini" "$keys"; then
      found=1
      log "SUCCESS DFS/AFC keys deployed (REQUEST_DISABLE_DFS_AFC)"
    fi
    rm -f "$keys"
  fi
  [ "$found" = "1" ] || log "WCNSS inject enabled but no overrides to deploy"
  return 0
}

cleanup_wcnss() {
  [ -f "$WCNSS_MANIFEST" ] || return 0
  while IFS= read -r f; do
    [ -n "$f" ] && rm -f "$WCNSS_TARGET_DIR/$f"
  done < "$WCNSS_MANIFEST"
  rm -f "$WCNSS_MANIFEST"
  log "removed deployed WCNSS overrides"
  return 0
}

detect_regdb_path() {
  # The bind target MUST be the exact file the WLAN firmware downloads, not
  # just any regdb.bin. Live proof on this board (peach_v2):
  #   cnss: Downloading REGDB: peach/regdb_xiaomi.bin, size: 24278
  # Xiaomi boards ship a second regdb_<vendor>.bin that the driver prefers;
  # binding only regdb.bin left every earlier regdb swap a no-op. So vendor-
  # suffixed names are searched BEFORE the plain regdb.bin, and REGDB_TARGET
  # lets an operator pin the exact path. Non-Xiaomi boards simply have no
  # regdb_xiaomi.bin, so the [ -f ] test falls through to regdb.bin.
  # REGDB_SEARCH_GLOBS overrides the list (used by regression tests).
  if [ -n "$REGDB_TARGET" ] && [ -f "$REGDB_TARGET" ]; then
    echo "$REGDB_TARGET"
    return 0
  fi
  globs=${REGDB_SEARCH_GLOBS:-"/vendor/firmware_mnt/image/*/regdb_xiaomi.bin /vendor/firmware_mnt/image/*/regdb*.bin /vendor/firmware/wlan/*/regdb.bin /vendor/firmware/regdb.bin /vendor/lib64/regdb.bin /vendor/etc/wifi/regdb.bin /vendor/firmware_mnt/image/regdb.bin"}
  for p in $globs; do
    if [ -f "$p" ]; then
      echo "$p"
      return 0
    fi
  done
  return 1
}

mount_regdb() {
  [ "$REGDB_MOUNT" = "1" ] || { log "regdb replace disabled by config"; return 0; }
  if [ ! -s "$REGDB_SRC" ]; then
    log "regdb replace skipped: $REGDB_SRC not present"
    return 0
  fi
  target=$(detect_regdb_path) || {
    log "WARN regdb target not found under known vendor paths; skipping"
    return 0
  }
  if grep -q " $target " /proc/mounts; then
    return 0
  fi
  if ! mount -o bind "$REGDB_SRC" "$target"; then
    log "ERROR regdb bind mount failed: $REGDB_SRC -> $target"
    return 1
  fi
  echo "$target" > "$REGDB_MOUNT_FLAG"
  log "SUCCESS regdb bind mount: $REGDB_SRC -> $target"
  return 0
}

unmount_regdb() {
  [ -f "$REGDB_MOUNT_FLAG" ] || return 0
  target=$(cat "$REGDB_MOUNT_FLAG")
  if grep -q " $target " /proc/mounts; then
    umount "$target" && log "unmounted regdb: $target"
  fi
  rm -f "$REGDB_MOUNT_FLAG"
  return 0
}

toggle_wifi() {
  # Driver-level reload without a reboot. Wi-Fi goes down/up briefly;
  # cellular/ethernet paths are unaffected.
  log "toggling Wi-Fi to reload driver configuration (no reboot)"
  svc wifi disable >/dev/null 2>&1
  sleep 3
  svc wifi enable >/dev/null 2>&1
  wait_wifi_ready
}

country_status_description() {
  fw_raw=$(framework_country)
  drv_raw=$(driver_country)
  fw=$(display_country "$fw_raw")
  drv=$(display_country "$drv_raw")
  profile=$(upper "$COUNTRY_PROFILE")
  request=$(requested_country)
  tx=$(tx_power_label)
  if [ "$profile" = "SYSTEM" ]; then
    request='系统自动'
  elif [ -z "$request" ]; then
    request='无效配置'
  fi

  if valid_cc "$(upper "$drv_raw")" && valid_cc "$(upper "$fw_raw")"; then
    if [ "$(upper "$drv_raw")" != "$(upper "$fw_raw")" ]; then
      consistency='不一致'
    elif [ "$profile" != "SYSTEM" ] && [ "$(upper "$drv_raw")" != "$request" ]; then
      consistency='请求未生效'
    else
      consistency='一致'
    fi
  else
    consistency='未验证'
  fi
  # Every field is a live readback: driver country from the self-managed
  # PHY, TX power from nl80211, never a value copied from the config file.
  printf '驱动:%s | 系统:%s | 请求:%s | TX:%s [%s]' \
    "$drv" "$fw" "$request" "$tx" "$consistency"
}

refresh_module_description() {
  prop="$MODDIR/module.prop"
  [ -f "$prop" ] || return 1
  desc=$(country_status_description)
  current=$(sed -n 's/^description=//p' "$prop" | head -1)
  [ "$current" = "$desc" ] && return 0

  # Atomic update: Magisk should never read a truncated module.prop.
  tmp="$MODDIR/.module.prop.$$"
  if ! awk -v line="description=$desc" '
    BEGIN { found=0 }
    /^description=/ { if (!found) print line; found=1; next }
    { print }
    END { if (!found) print line }
  ' "$prop" > "$tmp"; then
    rm -f "$tmp"
    return 1
  fi
  chmod 0644 "$tmp" || { rm -f "$tmp"; return 1; }
  mv -f "$tmp" "$prop" || { rm -f "$tmp"; return 1; }
  log "Magisk status: $desc"
  return 0
}

requested_country() {
  p=$(upper "$COUNTRY_PROFILE")
  case "$p" in
    SYSTEM) echo "" ;;
    US|CA|CN|JP|00) echo "$p" ;;
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
  # Preserve cross-ROM behavior: a property must be exposed by the installed
  # WLAN stack. 'resetprop -n' used to invent properties on unrelated versions.
  if [ "$KEEP_EHT" = "1" ]; then
    if [ -n "$(getprop persist.vendor.wlan.disable.eht)" ]; then
      resetprop -n persist.vendor.wlan.disable.eht false
      log "EHT switch interface detected: $(getprop persist.vendor.wlan.disable.eht)"
    else
      log "EHT property absent: leave vendor WLAN stack unchanged"
    fi
  fi
  if [ "$KEEP_MLO" = "1" ]; then
    if [ -n "$(getprop persist.vendor.wlan.disable.mlo)" ]; then
      resetprop -n persist.vendor.wlan.disable.mlo false
      log "MLO switch interface detected: $(getprop persist.vendor.wlan.disable.mlo)"
    else
      log "MLO property absent: leave vendor WLAN stack unchanged"
    fi
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
}

country_matches() {
  want="$1"
  fw=$(upper "$(framework_country)")
  drv=$(upper "$(driver_country)")
  if [ "$want" = "00" ]; then
    case "$fw" in
      00|WORLD) : ;;
      *) return 1 ;;
    esac
  else
    [ "$fw" = "$want" ] || return 1
  fi
  if [ "$VERIFY_DRIVER_COUNTRY" = "1" ]; then
    case "$want" in
      00)
        case "$drv" in
          00|WORLD) : ;;
          *) return 1 ;;
        esac
        ;;
      *) [ "$drv" = "$want" ] || return 1 ;;
    esac
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
    apply_country_once
    rc=$?
    if [ "$rc" -eq 0 ]; then
      fw=$(framework_country)
      drv=$(driver_country)
      log "SUCCESS country profile=$COUNTRY_PROFILE framework=${fw:-unknown} driver=${drv:-unknown} attempt=$i/$max"
      return 0
    fi

    fw=$(framework_country)
    drv=$(driver_country)
    log "RETRY country profile=$COUNTRY_PROFILE code=$COUNTRY_CODE framework=${fw:-unknown} driver=${drv:-unknown} rc=$rc attempt=$i/$max"
    i=$((i+1))
    [ "$i" -le "$max" ] && sleep "$COUNTRY_RETRY_DELAY_SEC"
  done

  return 1
}

# Apply the full v1.5 capability set in dependency order. Idempotent:
# WCNSS deployment and regdb mount detect their own done-state.
apply_capability_controls() {
  rc_all=0

  apply_tx_power
  rc=$?
  [ "$rc" -eq 0 ] || rc_all="$rc"

  deploy_wcnss
  rc=$?
  [ "$rc" -eq 0 ] || rc_all="$rc"

  mount_regdb
  rc=$?
  [ "$rc" -eq 0 ] || rc_all="$rc"

  # WCNSS/regdb changes need a driver reload to take effect. Opt-in because
  # it briefly drops Wi-Fi (never other data paths, never a reboot).
  if [ "$FORCE_WIFI_TOGGLE" = "1" ]; then
    toggle_wifi
    sleep 2
    # Country/profile state is re-established after the reload.
    apply_country
    rc=$?
    [ "$rc" -eq 0 ] || rc_all="$rc"
    apply_tx_power
    rc=$?
    [ "$rc" -eq 0 ] || rc_all="$rc"
  fi

  return "$rc_all"
}

# Full revert used by profile.sh reset and uninstall.sh.
revert_capability_controls() {
  reset_tx_power
  cleanup_wcnss
  unmount_regdb
  return 0
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
    /^[[:space:]]*\* [0-9][0-9.]* MHz/ {
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

# Per-band power ceiling + restriction flags read from the regulatory table
# (iw reg get). Values are regulatory ceilings, not measured TX power.
dump_regulatory_power() {
  iw reg get 2>/dev/null | awk '
    /^country / { country=$2; gsub(/:/,"",country); print "country " country }
    /\([0-9]+ - [0-9]+ @ [0-9]+\)/ {
      # toybox awk has no 3-arg match(); extract the freq window with RSTART.
      if (match($0, /[0-9]+ - [0-9]+ @ [0-9]+/)) {
        w = substr($0, RSTART, RLENGTH)
        split(w, a, / - | @ /)
        s=a[1]+0; e=a[2]+0; bw=a[3]+0
      } else { next }
      # classify by frequency, not by leading digits (5925/5945 are 6 GHz)
      band=""
      if (s >= 2400 && s < 2500) band="2.4GHz"
      else if (s >= 4900 && s < 5925) band="5GHz"
      else if (s >= 5925 && s < 7200) band="6GHz"
      maxp=0
      np=split($0, f, ",")
      for (i=1; i<=np; i++) {
        gsub(/[ ()]/, "", f[i])
        if (f[i] ~ /^[0-9]+$/ && f[i]+0 >= 1 && f[i]+0 <= 60 && f[i]+0 > maxp) maxp=f[i]+0
      }
      flags=""
      if ($0 ~ /DFS/) flags=flags" DFS"
      if ($0 ~ /NO-IR|no IR/) flags=flags" NO-IR"
      if ($0 ~ /NO-OUTDOOR|no outdoor/) flags=flags" NO-OUTDOOR"
      if ($0 ~ /PASSIVE-SCAN|passive scan|no IR/) flags=flags" PASSIVE"
      if (band!="") {
        printf "%-7s %6d-%-6d @%-4d max=%-3d%s\n", band, s, e, bw, maxp, flags
      }
    }
  '
}

dump_capability_controls() {
  echo "TX_POWER_MODE=$TX_POWER_MODE"
  echo "TX_POWER_MBM=$TX_POWER_MBM"
  echo "interface readback: $(iface_txpower_dbm) dBm"
  echo "WCNSS_INJECT=$WCNSS_INJECT (source: $INJECT_DIR, target: $WCNSS_TARGET_DIR)"
  if [ -f "$WCNSS_MANIFEST" ]; then
    sed 's/^/deployed: /' "$WCNSS_MANIFEST"
  else
    echo "deployed: none"
  fi
  echo "REGDB_MOUNT=$REGDB_MOUNT (source: $REGDB_SRC)"
  if [ -f "$REGDB_MOUNT_FLAG" ]; then
    echo "mounted: $(cat "$REGDB_MOUNT_FLAG")"
  else
    echo "mounted: none"
  fi
  echo "FORCE_WIFI_TOGGLE=$FORCE_WIFI_TOGGLE"
  echo "REQUEST_DISABLE_DFS_AFC=$REQUEST_DISABLE_DFS_AFC"
  if grep -q 'WiFi7-Lab DFS/AFC request' "$WCNSS_TARGET_DIR/WCNSS_qcom_cfg.ini" 2>/dev/null; then
    echo "DFS/AFC keys deployed: yes"
  else
    echo "DFS/AFC keys deployed: no"
  fi
}
