- [ ] **D-INITEDGES — INITXT / INIT32 / DSPFNK / ERAFNK / FNKSB: THE KEY LINE'S ROW AND MARGINS, R0'S KEPT BITS, THE NAME TABLE'S TAIL, THE ODD WIDTHS**
      🏗️ **RULED (Joost, 2026-11-18): the key-row part (sub ROM page 0) is PARKED**; the C-BIOS parts stay autonomous.
      🎚️ TIER 6 — every edge (each needs a program that changes CRTCNT, garbles RG0SAV or sets LINL40 above 40;
      filed 2026-11-17).
      🤖 **AUTONOMOUS** — docs/bios/INITXT.md, round 2's separating setup, run 4
      ([`XINIT_run4.out`](scratchpad/XINIT_run4.out)):
      - **R-I-CRTCNT / R-I-KEYS / R-I-KEYPLACE / R-I-KEYOUT:** the VG-8020 leaves CRTCNT as found and draws the key line
        on row CRTCNT -- 13, 20, 24, and for 0 / 30 off the screen's rows
        ([`XINIT3_run1.out`](scratchpad/XINIT3_run1.out)) (13 in the
        setup); zerobas sets CRTCNT to 24 when the key line is on and draws it on row 24.
      - **R-I-R0:** the VG-8020 keeps only bit 0 of RG0SAV ($A5 gives 01); zerobas $A1.
      - **R-I-TAIL-TXT:** INITXT with a width above 40: zerobas also clears the 64 bytes after the 960 name cells; the
        VG-8020 leaves them.
      - **R-I-KEYEDGE:** key line on with width 0, 80 or 255: the reference's odd cells (its rule says which).
      - **docs/bios/TOTEXT.md R-T-OLDX / R-T-DISPATCH** ([`XTOT_run1.out`](scratchpad/XTOT_run1.out),
        [`XTOT2_run1.out`](scratchpad/XTOT2_run1.out)): TOTEXT from SCREEN 2 / 3 dispatches on OLDSCR -- 2 back to SCREEN
        2; 3, $5A, $7F, $80 SCREEN 3; $81, $FF SCREEN 0 (OLDSCR := 0) -- where zerobas sets up SCREEN 1 for every
        non-zero OLDSCR (and sets OLDSCR to 1).
      - **docs/bios/DSPFNK.md R-K-STATE / R-K-ERA** ([`XKEY_run1.out`](scratchpad/XKEY_run1.out)): DSPFNK / FNKSB
        likewise draw on row 24 and set CRTCNT := 24 on zerobas (the VG-8020: row CRTCNT, CRTCNT kept); and at a
        width below the screen's (37, 39, 29) the VG-8020 writes only the width's span of the key line's row,
        leaving the margin cells, where zerobas writes the whole row (DSPFNK and ERAFNK).
      🟡 **PART 1 LANDED 2026-11-18: R-I-R0 and R-I-TAIL-TXT** (cbios-repack/initedges.patch, 17 bytes differ, nothing
      moves). INITXT / INIT32 mask RG0SAV with $01 (C-BIOS $F1), and the text clear is 40 * 24 at any LINLEN (C-BIOS
      80 * 24 above 40). Witness: INITXT.md's rules on the fixed build ([`XINIT_fix1.out`](scratchpad/XINIT_fix1.out),
      [`XINIT3_fix1.out`](scratchpad/XINIT3_fix1.out), [`XINIT4_fix2.out`](scratchpad/XINIT4_fix2.out)): R-I-R0 120 -> 0
      cases failing, R-I-TAIL-TXT 8 -> 0 (and R-I-LT 128 -> 0 from D-LINTTBVAL's clear). **STILL OPEN:** the key line's
      row / CRTCNT and the margins (sub/keystr.asm `ks_geom` takes row 24 and the whole row; the sub ROM's page 0 has
      3 B free) and TOTEXT's OLDSCR dispatch.
      🟡 **PART 2 LANDED 2026-11-18: TOTEXT's OLDSCR dispatch** (cbios-repack/totext-dispatch.patch, 26 bytes differ, nothing
      else moves). TOTEXT runs CHGMOD's table: 0..3 that screen, 4..$80 SCREEN 3, $81..$FF SCREEN 0 (INITXT makes OLDSCR 0).
      It is 7 B longer, paid from POSIT's pad, and TOTEXT starts 7 B earlier ($00D2 follows the label). WITNESS: XTOT / XTOT2
      re-run ([`XTOT_fix2.out`](scratchpad/XTOT_fix2.out), [`XTOT2_fix1.out`](scratchpad/XTOT2_fix1.out)): R-T-OLDX,
      R-T-DISPATCH and R-T-REGS2 hold on zerobas, R-T-THRU 4 -> 2 cases failing, R-T-VRAM2 16 -> 11 (the ruled font, and the two
      CRTCNT 13 cases). **What is left of D-INITEDGES is the key row / CRTCNT and the margins: PARKED** (Joost, 2026-11-18).
