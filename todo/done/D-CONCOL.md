- [x] **D-CONCOL — THE BDOS CONSOLE'S LOGICAL COLUMN AFTER A CONTROL CODE: TAB LANDS WRONG AFTER FF / BS / BEL / ESC**
      🎚️ TIER 6 — every edge (a TAB on the same line right after a control code; filed 2026-11-17).
      🤖 **AUTONOMOUS** — BDOSXC's measurement rows ([`XC3_stock.out`](../../scratchpad/XC3_stock.out), [`XC3_ours.out`](../../scratchpad/XC3_ours.out)): the CF-3300's column ($F237) rule is
      printable +1; CR and FF -> 0; BS -1; every other control code (LF, BEL, ESC ...) unchanged. Ours (conout_emit_e,
      disk/runtime.asm): CR -> 0, LF unchanged, EVERYTHING else +1 -- so `XYZ` FF `A` TAB puts B at 4 not 8, BS / BEL
      before a TAB jump to 16, ESC Y counts the ESC. ~+11 B, and conout_emit_e's pinned tail ($7FD1..) has 2 B free:
      a carve first (the disk ROM stays in its allotted space).
      ✅ **FIXED 2026-11-26.** BDOSXL (probes/disk/bdosxl.asm, now GATED in bdos-acceptance) read on both machines: the
      rule above plus HOME ($0B) -> 0, cursor-left ($1D) and DEL ($7F) -1 like BS ($FF at 0), and DIRIO's output does
      not touch the count at all nor expand TAB (`XYZ` leaves 0, from 2 it stays 2, a TAB at 36 stays 36) -- 92 bytes
      apart before ([AE_concol1.out](../../scratchpad/AE_concol1.out)), 19 after the first rule ([AE_concol_cap.out](../../scratchpad/AE_concol_cap.out)), 0 after (ce_col +
      conout_dirio_out, disk/runtime.asm; [AE_concol_cap2.out](../../scratchpad/AE_concol_cap2.out)). The gated run needs MODE 32 first, as BDOSXC: a C-BIOS host
      starts at another width ([AE_concol_bdos.out](../../scratchpad/AE_concol_bdos.out) -> [AE_concol4.out](../../scratchpad/AE_concol4.out)). conout_emit_e's tail SHRANK (the rule
      lives in front of $7F7C). Not measured: whether DIRIO-out skips Ctrl-P's printer echo on the CF-3300 (it does
      now, CP/M's direct-I/O convention).
