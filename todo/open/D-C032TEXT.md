- [ ] **D-C032TEXT — TEXT-REGION FACTS TO CHECK: FSTPOS ON SCROLL, BUFMIN, LINL40 / LINL32 AT START, CLS SIZES**
      🎚️ TIER 6 — every edge (filed 2026-11-21).
      🤖 **AUTONOMOUS** — From the C-BIOS 0.32 port's measurements (Joost, 2026-11-21; headless openMSX, BIOS calls made directly, VG-8020 = NMS 8250 unless noted). Check zerobas against them first.
      (1) CHPUT's scroll (LF or a wrap on the bottom row) and ESC M move FSTPOS's row ($FBCA) up by one (16 -> 15, 0 -> $FF);
      a plain LF without scroll does not. (2) BUFMIN ($F55D) holds ',' ($2C) from boot on. (3) At cartridge start LINL40
      is 37 and LINL32 29 (C-BIOS had 39). (4) CLS SCREEN 0 clears 960 bytes at any LINLEN on the VG-8020; SCREEN 3 clears
      $600 bytes.
