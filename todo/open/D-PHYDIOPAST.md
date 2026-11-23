- [ ] **D-PHYDIOPAST — A READ PAST THE DISK'S LAST SECTOR RETURNS ERROR 8 ON ZEROBAS, 2 ON THE REFERENCE**
      🎚️ TIER 6 — every error (filed 2026-11-20).
      🤖 **AUTONOMOUS** — docs/bios/PHYDIO.md (XDSK1_run2.out, XDSK2_run1.out, row D: the VG-8020 + NMS 1200 against
      zerobas's disk build). zerobas's H.PHYD ($FFA7) goes to its own DSKIO ($4010, disk/init.asm installs the hook), so
      the fix is DSKIO's -- the next region of the disk BIOS. ⚠️ ROOM: disk.rom's interior holes read 0 B free on
      2026-11-20 (`make basic-reloc`, tools/check_disk_walls.py): a carve first. Priced when picked up.
      R-PD-PAST (cases D03, D10, D14, D15): the reference reads the sectors before 1440, then A 2 ("not ready"), F
      $41, B the sectors not read. zerobas the same sectors and B, but A 8, F $09. A WRITE past the end is 8 on both
      (R-PD-WPAST).
