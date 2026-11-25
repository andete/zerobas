- [ ] 🐛 **A GAP AFTER `&` (`& H10`, `&<TAB>H10`), OR A TAB / LF BEFORE IT: THE VG-8020 SKIPS IT IN VAL, READ AND THE
      TOKENISER; ZEROBAS SAYS SYNTAX ERROR (OR 0) (D-AMPGAP, split from D-VALWS 2026-11-25).**
      🎚️ TIER 6 — every edge: a blank between `&` and its letter is rare in typed BASIC and in data; the everyday
      half of D-VALWS (a TAB inside a decimal number) is fixed.
      🤖 **AUTONOMOUS** — measured (scratchpad/readtab_probe.py --load --prefix, AE_readtab_prefix.out): the CF-3300
      crunches a LOADed `A=& H10` and `A=&<TAB>H10` to `&H10` (LIST shows it closed up) and READs `DATA & H10` as 16;
      zerobas: Syntax error in 10. VAL (rule R-VAL-PREFIX on docs/keywords/VAL.md, KNM VL 84, 164-168, 196, 197):
      `VAL("& H10")` 16 / error 2, `VAL(CHR$(9)+"&HFF")` 255 / 0. `"& "` and `"&"+CHR$(9)` (a gap, then the end) are
      error 2 on both.
      ➡️ THE SITES, all in the SUB ROM's page 0: the tokeniser's tk_hex (basic/tokenise.inc: `inc hl / ld a,(hl)`
      after the '&' -- skip blanks there through tkf_fetch, which since D-VALWS skips space / TAB / LF; a gap followed
      by NEITHER H nor O must still copy the '&' and its blanks verbatim, so HL is saved and restored: ~8 B), VAL's
      svp_base (sub/strheap.asm) and its leading-blank test before the '&', and READ's DATA `&` path (not located
      yet). ~8 B for tk_hex alone; sub page 0 had 17 B after D-VALWS's jp -> jr carve and D-VALWS took 8 -- a carve
      first (more jp -> jr sites: `jp p0cb` at sub2/filestmt.asm lines 434 / 474 / 603 were out of range then).
      Measure first what the reference stores for `& X1` (a gap, then neither H nor O) in a LOADed line.
