- [ ] **D-PHYDIOREGS — PHYDIO / DSKIO RETURN OTHER F, C, DE AND HL ON ZEROBAS**
      🎚️ TIER 6 — every edge (a machine-code caller reading PHYDIO's registers; filed 2026-11-20).
      🤖 **AUTONOMOUS** — docs/bios/PHYDIO.md (XDSK1_run2.out, XDSK2_run1.out, row D: the VG-8020 + NMS 1200 against
      zerobas's disk build). zerobas's H.PHYD ($FFA7) goes to its own DSKIO ($4010, disk/init.asm installs the hook), so
      the fix is DSKIO's -- the next region of the disk BIOS. ⚠️ ROOM: disk.rom's interior holes read 0 B free on
      2026-11-20 (`make basic-reloc`, tools/check_disk_walls.py): a carve first. Priced when picked up.
      The reference: a good transfer A 0, F $42, B 0, C $32, D / E = the entry A / F, HL as entered; a failure the
      same D / E / HL and C 0 (R-PD-READ, R-PD-WRITE, R-PD-FFFF, R-PD-PAST, R-PD-WPAST). zerobas: F $44, C and DE / HL
      working values (e.g. case D00: C $01, DE $0000, HL $0001; D02: DE $4F00, HL $05A0).
