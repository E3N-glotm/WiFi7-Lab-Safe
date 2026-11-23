#!/system/bin/sh
# Decide where the 6GHz rows come from. The AR record's pair (231) has no
# built-in 6GHz rules, yet the live AR table shows 58 enabled 6GHz channels,
# so those rows must originate from the record's super6g byte. Overwrite AR's
# super6g (file offset 166) 0x05 -> 0x21 (the value the US record carries and
# which GhostUnlock reports as live-safe) and read back whether the 6GHz rows
# change. If they do, super6g is taken from the file, which is what makes a
# custom "00" record feasible at all.
X=/vendor/firmware_mnt/image/peach/regdb_xiaomi.bin
T=/data/local/tmp/t6.bin
R=/data/local/tmp/rC.txt
cp /data/local/tmp/xiaomi_live_backup.bin $T
printf '\041' | dd of=$T bs=1 seek=166 count=1 conv=notrunc 2>/dev/null
{ echo "=== START $(date) ==="
  echo "AR record 0x0a0 after super6g 05->21:"
  od -An -tx1 -j 160 -N 16 $T
  echo "t6 md5:"; md5sum $T; } > $R
logcat -c
mount -o bind $T $X && echo BIND-OK >> $R || echo BIND-FAIL >> $R
cmd wifi force-country-code enabled AR >/dev/null 2>&1
svc wifi disable; sleep 3; svc wifi enable; sleep 45
{ echo "=== TEST: country AR, super6g 0x05 -> 0x21 ==="
  echo "--- iw reg get self-managed ---"
  iw reg get 2>/dev/null | sed -n '/self-managed/,$p' | head -18
  echo -n "REG_6G_LINES="; iw reg get 2>/dev/null | grep -cE '\(59[0-9]{2} - |\((6[0-9]{3}|7[0-9]{3}) - '
  echo -n "PHY_6G_ROWS="; iw phy 2>/dev/null | awk '/Band 4:/{b=1;next}/Band [0-9]/{b=0} b&&/MHz \[/{c++} END{print c+0}'
  echo -n "PHY_6G_EN="; iw phy 2>/dev/null | awk '/Band 4:/{b=1;next}/Band [0-9]/{b=0} b&&/MHz \[/&&!/disabled/{c++} END{print c+0}'
  echo -n "ROW_7125="; iw reg get 2>/dev/null | grep -cF '7125'
  echo -n "ROW_7105="; iw reg get 2>/dev/null | grep -cF '7105'
  echo -n "REG_21dBm="; iw reg get 2>/dev/null | grep -cF ', 21)'
  echo -n "REG_36dBm="; iw reg get 2>/dev/null | grep -cF ', 36)'
  echo "--- regdb log ---"; logcat -d 2>/dev/null | grep -iF regdb | head -4
} >> $R 2>&1
umount $X
{ echo "=== END $(date) ==="; md5sum $X; echo -n "MOUNTS="; grep -cF regdb /proc/mounts; echo ALLDONE; } >> $R 2>&1
