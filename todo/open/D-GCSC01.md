- [ ] **D-GCSC01 — IN SCREEN 0 / 1 THE GRAPHICS-CURSOR CALLS WORK AS IN SCREEN 3 ON THE VG-8020**
      🎚️ TIER 6 — every edge (filed 2026-11-21).
      🤖 **AUTONOMOUS** — From the C-BIOS 0.32 port's measurements (Joost, 2026-11-21; headless openMSX, BIOS calls made directly, VG-8020 = NMS 8250 unless noted). Check zerobas against them first.
      19 cases in SCREEN 1, 19 in SCREEN 0, registers included: MAPXYC, RIGHTC, LEFTC, UPC, DOWNC, TUPC, TDOWNC, SETC, READC
      and NSETCX behave exactly as in SCREEN 3 (CMASK $F0 / $0F, blocks, TDOWNC stopping at block row 47, CLOC $05x7, SETC a
      nibble into the pattern byte and no colour byte, NSETCX block by block). So GRPPRT in SCREEN 0 / 1 writes what SCREEN
      3 drawing writes. C-BIOS's SETC / RIGHTC / TDOWNC treat only SCRMOD 3 as blocks. (The NMS 8250 differs here.)
