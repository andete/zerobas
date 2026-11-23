- [ ] **D-MSX2SPEC — ELEPHANT / GOLDFISH SPEC PAGES FOR THE MSX2 AND MSX2+ BIOS CALLS (THE SUB-ROM AND THE NEW MAIN-ROM ENTRIES)**
      🎚️ TIER 1 — Joost 2026-11-23, second of "3, 2, 1"; feeds C-BIOS's next step ("fix all msx2 and msx2+ bios
      calls").
      🤖 **AUTONOMOUS** — References: Sony HB-F900 (msx2, JP), Philips NMS 8250 (msx2_eu), Panasonic FS-A1WSX (msx2plus)
      -- openMSX's generic machines, Joost's ruling 2026-11-23. The HB-F900 needs its Kanji ROM (Joost is getting it).
      The subject is C-BIOS's MSX2 / MSX2+ builds (zerobas is MSX1): pages per call, docs/spec-method.md's cycle.
      PROGRESS 2026-11-23: docs/msx2/ drafted (104-call inventory, ~80 pages, one goldfish round folded in, commit
      4fbe92687). MEASURED: main/'s shared VRAM address matrix (NSETRD / NSETWR / NRDVRM / NWRVRM) -- probes/bios/spec/
      xva.asm, biosl_run's new @vdpfull (R#0-63, S#0-15, the VRAM pointer, the palette) and @portlog (port writes):
      identical on all three references; a carry-losing page rule in SCREEN 5 / 6, and in SCREEN 0-4 with ACPAGE != 0
      the address is ACPAGE x $100 + E (HL unused) -- C-BIOS addresses HL there, its one difference. BIGFIL MEASURED too
      (xbf.asm: the same rule; BC 0 = 64 KB; returns BC 0 and interrupts ON); the PALETTE calls too (xplt.asm: the table is 16 x 2
      bytes in the VDP's layout, GETPLT reads it, INIPLT and SETPLT write it; same power-on palette on all three); the sub-ROM NRDVRM / NWRVRM (xva2.asm: the main rule
      in SCREEN 5-8, but (HL + ACPAGE x $4000 / $1000) AND $FFFF in SCREEN 0-4); WRTVDP / VDPSTA (xwv.asm: direct writes, copies
      $F3DF / $FFE7 / $FFFA, R#0 also writes R#9); the sprite calls (xspr2.asm); REDCLK / WRTCLK (xclk.asm: C-BIOS's REDCLK does not
      select the block reliably); the screen-mode calls (xmode.asm: CHGMOD, INIT*, SET*, SETPAG,
      CHGMDP; CHGMOD 10-12 are invalid even on the MSX2+); CHGCLR / CLS (xsubcls.asm: CLS's fill byte
      unmasked, per-mode); the graphics-cursor core (xsubgc.asm: MAPXYC / SETC / READC /
      SETATR / SCALXY; SCREEN 2 behaves as MULTICOLOUR in the sub-ROM); the cursor moves (xsubmv.asm: the plain moves
      use multicolour cell steps even in SCREEN 5-8; C-BIOS's TRIGHT / TLEFTC do nothing); the boxes and the line (xsubbox.asm: ATRBYT is $F3F2;
      C-BIOS's NVBXLN draws a wrong figure and its DOGRPH nothing); GRPPRT (xsubgpp.asm: FORCLR / BAKCLR
      cell, CR and the X wrap; C-BIOS has neither); BLTVV / BLTVM / BLTMV (xsubblt.asm: C-BIOS's BLTMV
      drops the last dot); DSPFNK (xsubfnk.asm: label width / 5 - 1; C-BIOS's is a no-op); SCANR / SCANL (xsubscan.asm: callable, SCANR needs DE 1; C-BIOS's are no-ops).
      C-BIOS findings
      sent (inbox 2026-11-23-zerobas-msx2-subrom-findings.md). NEXT: the disk BLT calls, VA-13
      / VA-14 / VA-16, then the sub-ROM pages region by region.
