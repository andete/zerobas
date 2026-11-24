- [ ] 🐛 **AFTER A PLAIN POWER-ON, ZEROBAS'S PUBLISHED SYSTEM CELLS DIFFER FROM THE VG-8020'S: FRETOP, AND ~20 MS-BASIC
      CELLS ZEROBAS USES FOR ITS OWN STATE (D-BOOTCELLS, found 2026-11-24, Joost: "I also wonder if we already match the
      VG8020 for memory" / "make the measurement without a cartridge").**
      🎚️ TIER 4 — RAM usage (VG-8020): no program run differs, but a program or extension ROM that PEEKs / uses a
      published MS-BASIC cell sees zerobas's value.
      🤖 **AUTONOMOUS** — [`memboot_probe.py`](../../scratchpad/memboot_probe.py) (no cartridge, BASIC's Ok, 12 s; only
      $F39A-$FD99) + [`sysdata_diff.py`](../../scratchpad/sysdata_diff.py) -> [`AE_memboot_diff.out`](../../scratchpad/AE_memboot_diff.out).
      MEMSIZ / STKTOP / SAVSTK / FILTAB now AGREE (D-NMSHOST item 2). Differ: (1) FRETOP $F69B: $F168 (= MEMSIZ) there,
      $F380 here -- layout_from_himem sets it, a later step of zerobas's start-up resets it; (2) published cells used
      for zerobas's own state, the reference's values there differing (mostly 0 after boot): GSP / FSP / CSP / CTLTOP /
      TSP / CTLLIM ($F703-$F719), CSR_ADDR / CSR_CHAR / CSR_ON ($F72C-$F735), RL_HL / RL_ROW0 / RL_COL0 ($F7A9-$F7AD),
      POOLSIZE / TXTCEIL ($F66A-$F66D), DATASTATE ($F6A5), PRGEND ($F6E8), KEYARG ($F856), SUBSLOT / SUBSLOT_OK
      ($FD09-$FD0A); (3) leftover scratch buffers (" 28815" at $F7C6, line text at $FC1A-$FC3F there, zeros here);
      (4) expected: JIFFY, SCNCNT, the expanded-RAM slot cells.
      ➡️ When picked up: FRETOP first (find the step that overwrites it); then move zerobas's own state out of the
      published cells (the RAM map, tools/ram_map.py), one cell group at a time, each with its gates.
