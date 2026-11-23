#!/system/bin/sh
# Live test: does the loaded regdb_xiaomi.bin drive the iw table through the
# record pair selector? Patch ONLY the US record's low pair byte 234 -> 231
# (APL17_ETSIC: 2.4G 30 dBm to ch14, 5G-high 36 dBm, no DFS/NO-IR) at offset
# 3540, bind over regdb_xiaomi.bin (the file the ko strings prove is loaded),
# reload, and read back. All output is captured to /data/local/tmp/rB.txt.
X=/vendor/firmware_mnt/image/peach/regdb_xiaomi.bin
T=/data/local/tmp/t231.bin
R=/data/local/tmp/rB.txt
cp /data/local/tmp/xiaomi_live_backup.bin $T
printf '\347' | dd of=$T bs=1 seek=3540 count=1 conv=notrunc 2>/dev/null
{ echo "=== START $(date) ==="
  echo "record 0xdd0 patched (ea->e7 = pair 234->231):"
  od -An -tx1 -j 3536 -N 16 $T
  echo "t231 md5:"; md5sum $T; } > $R
logcat -c
mount -o bind $T $X && echo "BIND-OK" >> $R || echo "BIND-FAIL" >> $R
svc wifi disable; sleep 3; svc wifi enable; sleep 45
{ echo "=== TEST: loaded regdb_xiaomi.bin US pair 234->231 ==="
  echo "--- iw reg get (self-managed) ---"
  iw reg get 2>/dev/null | sed -n '/self-managed/,$p' | head -24
  echo -n "PHY_MHZ_ROWS="; iw phy 2>/dev/null | grep -cF 'MHz ['
  echo -n "ROW_36dBm="; iw phy 2>/dev/null | grep -cF '36.0 dBm'
  echo -n "ROW_2482="; iw phy 2>/dev/null | grep -cF '2482'
  echo -n "ROW_5650="; iw phy 2>/dev/null | grep -cF '5650'
  echo -n "RADAR_ROWS="; iw phy 2>/dev/null | grep -cF 'radar'
  echo -n "HAS6G="; iw phy 2>/dev/null | grep -cE '\* 59[0-9]{2}\.[0-9]|\* 71[0-9]{2}\.[0-9]'
  echo "--- regdb log ---"; logcat -d 2>/dev/null | grep -iF regdb | head -5
  echo "--- mounts ---"; grep regdb /proc/mounts
} >> $R 2>&1
umount $X
{ echo "=== END $(date) ==="; echo "vendor md5 AFTER:"; md5sum $X
  echo -n "MOUNTS="; grep -cF regdb /proc/mounts; echo ALLDONE; } >> $R 2>&1
