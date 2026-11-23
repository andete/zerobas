- [ ] **D-CONCOL — THE BDOS CONSOLE'S LOGICAL COLUMN AFTER A CONTROL CODE: TAB LANDS WRONG AFTER FF / BS / BEL / ESC**
      🎚️ TIER 6 — every edge (a TAB on the same line right after a control code; filed 2026-11-17).
      🤖 **AUTONOMOUS** — BDOSXC's measurement rows ([`XC3_stock.out`](../../scratchpad/XC3_stock.out), [`XC3_ours.out`](../../scratchpad/XC3_ours.out)): the CF-3300's column ($F237) rule is
      printable +1; CR and FF -> 0; BS -1; every other control code (LF, BEL, ESC ...) unchanged. Ours (conout_emit_e,
      disk/runtime.asm): CR -> 0, LF unchanged, EVERYTHING else +1 -- so `XYZ` FF `A` TAB puts B at 4 not 8, BS / BEL
      before a TAB jump to 16, ESC Y counts the ESC. ~+11 B, and conout_emit_e's pinned tail ($7FD1..) has 2 B free:
      a carve first (the disk ROM stays in its allotted space).
