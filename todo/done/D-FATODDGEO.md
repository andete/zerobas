- [x] 🐛 **FAT_MOUNT HUNG ON A DISK WHOSE DATA SECTORS ARE NOT A MULTIPLE OF ITS SECTORS PER CLUSTER (D-FATODDGEO, found 2026-11-26
      by reading -- the queue's "fat_mount odd-geometry check").**
      🎚️ TIER 3 — common errors: a mount that never returns, on any BPB-geometry disk with such a count.
      🤖 **AUTONOMOUS** — fixed the day it was found.
      basic/fat-prim-body.inc fm_div counted clusters by subtracting SPC until the remainder was EXACTLY 0: a count
      that is not a multiple wrapped ($0001 - 2 = $FFFF) and, with an even SPC, never reached 0. Standard formats
      are exact multiples (720 KB: 1426 / 2), and a media ID in the FAT fixes a standard format (D-MEDIAID), so only
      a disk with no media ID -- whose BPB zerobas then reads, its own choice; the references reject such a disk --
      could reach it.
      ✅ **FIXED 2026-11-26:** floor(data / SPC) + 2, as the FAT specification counts clusters (`or a`, then `sbc hl,bc
      / jr c / inc de`), 3 B shorter. New tests/test_fat_oddgeo.py: SPC 2 / 4 / 8 with remainders 0..3 -- all PASS;
      on the old loop the five remainder rows never return ([AE_oddgeo_utknife.out](../../scratchpad/AE_oddgeo_utknife.out)).
