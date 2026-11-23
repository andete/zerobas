- [ ] **D-PHYDIOB0 — PHYDIO WITH B 0 TRANSFERS NOTHING ON ZEROBAS; THE REFERENCE READS 256 SECTORS**
      🎚️ TIER 6 — every edge (filed 2026-11-20).
      🤖 **AUTONOMOUS** — docs/bios/PHYDIO.md (XDSK1_run2.out, XDSK2_run1.out, row D: the VG-8020 + NMS 1200 against
      zerobas's disk build). zerobas's H.PHYD ($FFA7) goes to its own DSKIO ($4010, disk/init.asm installs the hook), so
      the fix is DSKIO's -- the next region of the disk BIOS. ⚠️ ROOM: disk.rom's interior holes read 0 B free on
      2026-11-20 (`make basic-reloc`, tools/check_disk_walls.py): a carve first. Priced when picked up.
      R-PD-PAST, case D04 (from sector 1439: the reference reads one sector, then error 2 with B $FF left; from
      sector 0, run 1, it read on over the probe and never returned). zerobas returns A 0, B 0, nothing read.
