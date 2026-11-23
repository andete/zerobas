- [ ] **D-C032GFX — GRAPHICS FACTS TO CHECK: SETC SCREEN 3 WITH ANY CMASK, CLRSPR IN SCREEN 0, INIT32'S ORDER**
      🎚️ TIER 6 — every edge (filed 2026-11-21).
      🤖 **AUTONOMOUS** — From the C-BIOS 0.32 port's measurements (Joost, 2026-11-21; headless openMSX, BIOS calls made directly, VG-8020 = NMS 8250 unless noted). Check zerobas against them first.
      (1) SETC in SCREEN 3 with any CMASK: (byte AND NOT CMASK) OR ATRBYT, shifted to the upper nibble when CMASK bit 7 is
      set (96 cases; docs/bios/SETC.md covers only $F0 / $0F). (2) CLRSPR also clears the sprites in SCREEN 0, writes
      RG1SAV to VDP R1, and clears the patterns before the attributes. (3) INIT32: the VG-8020 clears the name table, then
      sets up the sprites (the NMS 8250 the other way round).
