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
      sent (inbox 2026-11-23-zerobas-msx2-subrom-findings.md). Since 11-23 the remaining pages are measured by PARALLEL
      agents, each in its own isolated instance (tools/agent_wt.py, --fresh clock-chip state): the disk BLT calls
      BLTVD / BLTDV / BLTMD / BLTDM (xsubbltd.asm; raw files, BLTDV obeys ARG; C-BIOS has no disk -- stubs); BEEP
      (xsubbeep.asm: reads clock block 2 every call; C-BIOS's is a no-op), NEWPAD (xsubpad*.asm), KNJPRT (xsubknj.asm:
      the NMS 8250, no kanji ROM, draws a solid block); SDFSCR / SETSCR / PROMPT / CLRTXT (xsubscr / xsubset / xsubpmt /
      xsubctx.asm: block 2 / block 3 of the clock chip; C-BIOS's are no-ops); EXTROM / SUBROM (xextrom*.asm: IY and the
      alternates preserved; side finding: GETPLT returns D = the palette number, C-BIOS leaves DE), CHKSLZ (xchkslzd.asm:
      NOT a callable service -- the three references disagree and none returns normally), CHKNEW (flags of CP 5 on
      SCRMOD), EOL, RDRES / WRRES (port $F4, complemented). Every MSX2 / MSX2+ page that exists is now DRAFT 1.
      The five entries that had NO PAGE (found 11-23 by a link scan) are written and measured: DELLNO / INSLNO
      (xsubdln*.asm: rows L..last move; the FS-A1WSX leaves interrupts off where the other two turn them on), PUTVRM
      (xsubpvr*.asm: byte C at NAMBAS + row / column + LINLEN's margin), KYKLOK (xsubkyk*.asm: the two JP machines toggle
      KANAST and PSG R15 bit 7; the NMS 8250 does nothing), PUTCHR (xsubpch*.asm: NOT a draw -- A into the key buffer on
      the two JP machines; the NMS 8250 does nothing). C-BIOS: RET at all five. docs/msx2/ has no broken link left.
      VA-13 / VA-14 / VA-16 measured (xva13 / xva14 / xva16.asm): SCRMOD 10 takes 32 KB pages (C-BIOS 64 KB); an
      interrupt never lands between a call's four port $99 writes; 64 KB VRAM masks nothing (FS-A1WSX boots MODE 10,
      the other two 01) -- the shared matrix is complete. GOLDFISH PASS 1 (test writer, one fresh reviewer per group)
      over the 23 pages written 11-23, every finding acted on by an isolated agent: almost all measured, the rest moved
      to open rows; notable corrections -- CLRTXT's HB-F900 interrupt state, SETSCR draws the key line BEFORE the
      banner, WRRES's port write was never shown (now is), BLTVD drops the dots past the right edge itself, all four
      disk BLTs write $F571-$F572. One DECISION is open on CHKSLZ: what the subject's acceptance test checks, since
      the references disagree and none returns cleanly.
      GOLDFISH PASS 1 over the 61 OLDER pages (9 fresh reviewers, scratchpad/REVIEW-m2-g*.md; 8 isolated fixers) done
      11-23 the same evening: every page now carries a "Goldfish pass 1" status line; no finding rejected outright;
      most separating cases MEASURED (new probes xspr3, xsubgc2, xsubmv2, xsubbox2, xsubgpp2, xsubscan2, xva3, xmode2,
      extended xwv / xsubcls / xplt / xclk / xsubfnk / xsubblt / xva2), the rest open rows. Corrections of note: the
      VRAM address rule for ACPAGE > 3 (and 2-3 in SCREEN 7 / 8) -- ACPAGE's high bits are ADDED into H, carry lost;
      SCANL paints RIGHTwards; DSPFNK's width is (LINLEN + 1) / 5 - 1; BLTVV returns with the command running; GETPLT
      sets D := A; SETMLT's R#1 is $2D; CHGMOD rebuilds R#0-R#6 from the copies; TRIGHT stops on CLOC low >= $F8.
      Every MSX2 / MSX2+ page has now had one test-writer pass.
      NEXT: D-TRSPEC (turbo R; generic = FS-A1GT).
