#!/system/bin/sh
MODDIR=${0%/*}
CONF=/data/adb/wifi7_lab_safe.conf

usage() {
  echo "Usage: $0 SYSTEM|US|CA|CN|JP|CUSTOM [CC]"
  exit 2
}

[ -r "$CONF" ] || cp -f "$MODDIR/wifi7_lab_safe.conf" "$CONF"

p=$(echo "$1" | tr '[:lower:]' '[:upper:]')
case "$p" in
  SYSTEM|US|CA|CN|JP) ;;
  CUSTOM)
    cc=$(echo "$2" | tr '[:lower:]' '[:upper:]')
    case "$cc" in [A-Z][A-Z]) ;; *) usage ;; esac
    ;;
  *) usage ;;
esac

if grep -q '^COUNTRY_PROFILE=' "$CONF"; then
  sed -i "s/^COUNTRY_PROFILE=.*/COUNTRY_PROFILE=$p/" "$CONF"
else
  echo "COUNTRY_PROFILE=$p" >> "$CONF"
fi

if [ "$p" = "CUSTOM" ]; then
  if grep -q '^COUNTRY_CODE=' "$CONF"; then
    sed -i "s/^COUNTRY_CODE=.*/COUNTRY_CODE=$cc/" "$CONF"
  else
    echo "COUNTRY_CODE=$cc" >> "$CONF"
  fi
fi

chmod 0644 "$CONF"
echo "Saved profile: $p"
echo "Run $MODDIR/action.sh to apply and export diagnostics."
