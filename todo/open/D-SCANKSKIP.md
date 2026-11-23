- [ ] **D-SCANKSKIP — A SCANR THAT ENDS IN ITS SKIP KEEPS K; ZEROBAS STORES THE SKIP'S HL 0**
      🎚️ TIER 6 — every edge (filed 2026-11-21).
      🤖 **AUTONOMOUS** — From the C-BIOS 0.32 port's measurements (Joost, 2026-11-21; headless openMSX, BIOS calls made directly, VG-8020 = NMS 8250 unless noted). Check zerobas against them first.
      docs/bios/SCANR.md / SCANL.md (34 cases, registers included). (1) A SCANR ending in its skip (DE runs out, HL 0) KEEPS
      K at FILNAM+1: K 6 from an earlier SCANR stays after a DE 1 / DE 2 skip, a preset K 7 after a skip to the row's end.
      zerobas's scan_k (basic/main.asm, D-SCANLPAINT) stores HL on EVERY SCREEN 2 SCANR exit -- a skip stores 0. (2) A skip
      that reaches the row's last pixel still on the border ends there: CLOC on X 255, HL 0, DE 0 (not the counted-down
      value), nothing painted, CSAVEA / CSAVEM and K kept (SCANR.md lists it open). (3) SCANL in SCREEN 2 with HL + K = 0
      still runs NSETCX with 0: the first byte's colour changes (the cell's foreground becomes ATRBYT); zerobas paints
      nothing (pb_paint and scan_kl both return on 0). In SCREEN 3, HL 0 paints nothing on the references too.
