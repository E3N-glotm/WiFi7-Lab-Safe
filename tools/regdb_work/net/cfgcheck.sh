#!/bin/sh
# Confirm the module can actually reach the measured-best country code.
#
# AR is the code the live tests selected (DFS=0, NO-IR=0, 5 GHz upper band at
# 36 dBm, 58 of 60 6 GHz channels), and the module must express it without
# being hard-coded: COUNTRY_PROFILE=CUSTOM plus COUNTRY_CODE=AR is the path.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT HUP INT TERM
printf 'COUNTRY_PROFILE=CUSTOM\nCOUNTRY_CODE=AR\n' > "$T/conf"

out=$(WIFI7_CONF="$T/conf" WIFI7_LOG="$T/log" sh -c '
  . "'"$ROOT"'/common.sh"
  printf "%s|%s\n" "$(requested_country)" "$(valid_cc "$(requested_country)" && echo accepted || echo rejected)"
')
echo "requested|validity = $out"
[ "$out" = "AR|accepted" ] || { echo "FAIL: CUSTOM/AR did not resolve"; exit 1; }

# A code the firmware has no built-in table for must still be accepted by the
# validator (the driver decides), while a malformed one must be rejected.
for cc in US CN 00; do
  printf 'COUNTRY_PROFILE=CUSTOM\nCOUNTRY_CODE=%s\n' "$cc" > "$T/conf"
  r=$(WIFI7_CONF="$T/conf" WIFI7_LOG="$T/log" sh -c '
    . "'"$ROOT"'/common.sh"; requested_country')
  [ "$r" = "$cc" ] || { echo "FAIL: $cc resolved to '$r'"; exit 1; }
done
printf 'COUNTRY_PROFILE=CUSTOM\nCOUNTRY_CODE=X1\n' > "$T/conf"
if WIFI7_CONF="$T/conf" WIFI7_LOG="$T/log" sh -c '
    . "'"$ROOT"'/common.sh"; requested_country' | grep -q .; then
  echo "FAIL: malformed code X1 was accepted"; exit 1
fi
echo "PASS: country code stays a configuration value (AR/US/CN/00 resolve, X1 rejected)"
