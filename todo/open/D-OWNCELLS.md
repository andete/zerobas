- [ ] 🐛 **ZEROBAS KEEPS 29 BYTES OF ITS OWN STATE IN BYTES MSX1 LEAVES UNDEFINED ($FAF5-$FB02, $FC88-$FC98), WHERE BOTH
      REFERENCES READ 0 -- A PEEK THERE DIFFERS, AND AN RS-232C OR KANJI CARTRIDGE WOULD OVERWRITE THEM (D-OWNCELLS,
      filed 2026-11-25 from D-BOOTCELLS step 3).**
      🎚️ TIER 4 — RAM usage (VG-8020): no program run differs today; a PEEK of those bytes, or a cartridge that uses
      the MSX1 RS-232C queue ($FAF5 up) or the MSX2-named cells there, sees or clobbers zerobas's state.
      🙋 **JOOST** — the goal is his (2026-11-25, accepting step 3 for now): "eventually we need to either avoid
      needing them or use the same location or mechanism as the references". Ask him which route before starting.
      WHAT: D-BOOTCELLS step 3 moved zerobas's own state (SUBSLOT / SUBSLOT_OK, the control pool's GSP FSP CSP
      CTLTOP TSP CTLLIM, the line editor's RL_HL / RL_ROW0 / RL_COL0, the block cursor's CSR_ADDR / CSR_CHAR / CSR_ON,
      POOLSIZE / TXTCEIL, PRGEND / DATASTATE) out of the published MS-BASIC cells (PARM1, PARM2, CONLO, SUBFLG,
      SLTWRK) into the trap table's unused tail ($FC88, $FC8A-$FC98) and $FAF5-$FB02 (basic/sysvars.inc, the build
      guards there). The published cells now hold the VG-8020's values; the moved values show in those undefined
      bytes instead (scratchpad/AE_bootcells3_diff_after.out). subsig-acceptance read $FAF9 and went red (200 against
      0); it now reads only its subject, EXBRSA at $FAF8, and names this item.
      ROUTES (for Joost): (a) need fewer cells -- derive what can be derived (TXTCEIL / POOLSIZE from the layout cells
      MEMSIZ / STKTOP, which since D-BOOTCELLS follow MS-BASIC's rule; PRGEND from VARTAB), keep transient state on
      the stack; (b) the references' own mechanism -- MS-BASIC keeps its state in its documented cells and RAM below
      HIMEM; zerobas could take its few remaining bytes the way a BASIC extension does (below HIMEM, which moves FRE
      and needs a ruling against tier 4's FRE match) or in the cells whose meaning it actually implements; (c) a mix.
      Left from step 3: KEYARG ($F856, 1 B, a leftover value after boot) and 5 B still in SLTWRK ($FD0B-$FD0F: SUBSLOT2
      unused, SUB_PING / SUB_INT_DELTA self-test cells, STRPTR) -- all 0 at boot.
