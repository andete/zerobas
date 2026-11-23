- [ ] **D-PHYDIOMEDIA — ZEROBAS TAKES MEDIA BYTES THE REFERENCE REFUSES ($00, $32: ERROR 12)**
      🎚️ TIER 6 — every error (filed 2026-11-20).
      🤖 **AUTONOMOUS** — docs/bios/PHYDIO.md (XDSK1_run2.out, XDSK2_run1.out, row D: the VG-8020 + NMS 1200 against
      zerobas's disk build). zerobas's H.PHYD ($FFA7) goes to its own DSKIO ($4010, disk/init.asm installs the hook), so
      the fix is DSKIO's -- the next region of the disk BIOS. ⚠️ ROOM: disk.rom's interior holes read 0 B free on
      2026-11-20 (`make basic-reloc`, tools/check_disk_walls.py): a carve first. Priced when picked up.
      R-PD-MEDIA (cases D11 C $00, D19 C $32): the reference refuses before any transfer -- A 12, F $89, B as
      entered, C 0, the buffer untouched; $F8, $F9 and $FF are taken. zerobas reads the sector. Which media bytes
      the reference takes besides those three is open (PHYDIO.md).
      Round 3 (2026-11-22, XDSK3_run2.out D20-D36): $80, $F0, $F7 refused too, $FA taken; the media check comes BEFORE
      the sector check ($00 with sector 1440: 12); and the media byte sizes the disk on both machines ($F8: 720
      sectors, $FF / $FA: 640 -- zerobas does that already). zerobas takes all five refused bytes and reads sector 0.
