# D-WSZERO — zerobas's state in [$E98A, $F380) (diskless), and where it goes

A read-only design inventory (2026-10-14, a subagent; nothing built or run but
`tools/ram_map.py`). Inputs: zerobas's sources, symbols and RAM map; the
reference only through PUBLISHED work-area documentation (names, addresses,
documented jobs) and the repo's own measurements. No reference ROM byte read.
The full 428-row table: [`wszero_inventory_table.md`](wszero_inventory_table.md).
(verify) = a published address/role to confirm; 📏 = a measurement the proposal
depends on.

## Bounds and totals

- Window = TXTMAX_NODISK $E98A .. $F380 = **2550 B** (the 2536 in the docs is the
  FRE(0) gap, a different quantity).
- 428 named addresses; **1474 B declared, 1076 B in 24 unattributed runs — all
  holes** (none is an offset-addressed part of a buffer), the largest $F195-$F351
  (444 B), $EE71-$EF64 (243 B, the old CAL_BUF pair), $ED5A-$EDC2 (104 B).
- Class totals: **A** (BLOAD / tape / `,R`) 55 B · **B** (interrupt service) 128 B
  (64 = the $F10A trampoline reservation) · **C** (needed to continue BASIC after a
  load) 290 B · **D** (the rest) 999 B · not ours 2 B (DSKBUF_PTR $F351, the
  CF-3300's own cell).
- Home totals: published same-job cell 917 B · disk-only → the disk floor 289 B ·
  shared published buffer 114 B · dynamic below HIMEM 51 B · eliminate 101 B.

## Two findings

1. **The interrupt service reads the window every frame.** `htimi_service →
   event_poll` (basic/traps.asm) reads TRAPENA $EE0B, TRAPSVC $EE0C, ZINTVAL
   $EE07 on every VBLANK; nonzero → it walks ZTRAP $EDD1..$EE06 and writes
   TRAPPEND $EE1F, STOPHOLD $F027. A binary loaded over $EDD1-$EE1F becomes armed
   traps with garbage handler links one frame later (D-TAPELOAD's class E:
   Sorcery and Elidon load above $E98A).
2. **C-BIOS writes below $F380 too**: 49 B at $F33B..$F357 at boot and $F2B8
   repeatedly (scratchpad/dowrite_probe.out). On the VG-8020 nothing below $F380
   is the BIOS's. A repack-patch question, separate from sysvars.inc.

## The two mechanisms the tapes hit

- **(A) BLOAD eats itself:** the load loop re-reads CURPTR / ENDPTR ($EC20-$EC25)
  after every TAPIN byte; a block covering them corrupts the loop (Disc Warrior:
  `Device I/O error` after reading past the block).
- **(B) the ISR reads garbage** (finding 1).

## Proposed homes (headlines; the table has every cell)

- Class A: EXECPTR → SAVENT $FCBF; RUNFLAG → RUNBNF $FCBE; CURPTR / ENDPTR → the
  stack (measured 2026-10-14, scratchpad/refwork_bload_probe.out: the VG-8020's
  tape BLOAD writes FILNAM $F866-$F876 and $FCBE-$FCC0, no published start / end
  cell); CAS_WANT / CAS_HDRNAME → FILNAM / FILNM2; CAS_BUFP → NULBUF $F862;
  marshalling → TEMP* / stack.
- Class B: ZTRAP → TRPTBL $FC4C; ZINTVAL / ZINTCNT → INTVAL $FCA0 / INTCNT $FCA2
  (📏 C-BIOS may count INTCNT itself); TRAPPEND → ONGSBF $FBD8; TRAPENA / TRAPSVC
  / STOPHOLD derived from TRPTBL; sub-ROM slot cells → SLTWRK $FD09; the
  RAM-resident $0038 trampoline (SUB_INT_RAM) → main page-1 ROM code (needs ~36 B
  of main page 1: a carve first).
- Class C: SAVSTK → $F6B1 (merged with CSP), SAVTXT → $F6AF, CTLTOP → STKTOP
  $F674, FRETOP → $F69B, MEMSIZ / STKTOP published (POOLSIZE derived), PRGEND =
  VARTAB-2, TXTCEIL eliminated (ceiling = HIMEM), CONT → OLDLIN / OLDTXT, DATA →
  DATPTR / DATLIN, ERRRESUME → ERRTXT, DEF FN frame → PARM2 / PARM1 family,
  channel state → PTRFIL + FCB headers, PRDEST → PRTFLG, DRAW S/A → DRWSCL /
  DRWANG. CURLINE / GSP / TSP have no published twin (redesign or last tenants).
- Class D: float scratch → HOLD8 / HOLD2 / HOLD / DECTMP (+ ARG later); tokeniser
  and formatter → FBUFFR; LIST render window → BUF; graphics → the published
  CIRCLE / PAINT / MCL cells + stack frames; disk-only cells → the disk floor.

## Slice plan (crash-critical first; each slice green on its own)

| # | slice | frees |
|---|---|---|
| 0 | apparatus: the WSZERO gate (a synthetic tape BLOADs over the window, then BASIC runs on), a census of window writes, a sweep that each published target is free under zerobas AND C-BIOS, the C-BIOS census below $F380 | 0 |
| 1 | BLOAD / tape (A) | 55 |
| 2 | interrupt service (B); 2b the $0038 trampoline into main ROM after a carve | 64 (+64) |
| 3 | stack / text anchors (C core) | ~45 |
| 4 | run-loop control flags | ~14 |
| 5 | disk-only cells → the disk floor (FLD_TAB gated on a disk channel) | ~385 |
| 6 | DEF FN → PARM2 / PARM1 | 112 |
| 7 | channel / file state → PTRFIL + FCB headers | 23 |
| 8 | math scratch → HOLD8 family | ~230 |
| 9 | graphics + DRAW → published cells + stack frames | ~240 |
| 10 | render window → BUF; marshalling, editor, string-engine cells | ~250 |
| 11 | raise the diskless ceiling to $F380 (the holes become program RAM; FRE(0) parity) | 1076 holes |
