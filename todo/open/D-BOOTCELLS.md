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
      MEASURED 2026-11-24 (typed PEEKs, VG-8020 vs zerobas NODISK; Joost: "yes, I think we need to fix those boot state
      differences"): FRE("") and FRE(0) AGREE after `CLEAR 300,&HC000`, `MAXFILES=3` and `MAXFILES=0` (300 / 15531,
      300 / 14997, 300 / 15798) -- zerobas reserves the right AMOUNT -- but its cells stay static (MEMSIZ $F168, STKTOP
      $F0A0, FILTAB $F16A; FRETOP = HIMEM). The reference keeps them live: MEMSIZ = HIMEM - ((MAXFILES+1) * 267 + 2)
      ($BDE8 / $BBD2 / $BEF3 for MAXFILES 1 / 3 / 0 under HIMEM $C000), STKTOP = MEMSIZ - the string space ($BCBC /
      $BAA6 / $BDC7), FILTAB = MEMSIZ + 2, FRETOP = MEMSIZ (one reading $BDE9 = MEMSIZ + 1 right after CLEAR: to
      re-check). And its strings sit between STKTOP and MEMSIZ, zerobas's from HIMEM down (inside the reference's file
      area). THE FIX: the layout cells live through CLEAR / MAXFILES by that rule, the string heap's ceiling = MEMSIZ,
      the stack top = STKTOP; FRE must not move (the regression check).
      FILTAB's TABLE (measured, same run): MAXFILES+1 words at FILTAB, each pointing at a 265-byte file control block laid
      out right after the table -- FCB i = FILTAB + 2 * (MAXFILES+1) + 265 * i (MAXFILES 1: $BDEA -> $BDEE, $BEF7;
      MAXFILES 3: $BBD4 -> $BBDC, $BCE5, $BDEE, $BEF7; MAXFILES 0: $BEF5 -> $BEF7); 265 + the 2-byte entry = the 267 in
      MEMSIZ's rule. zerobas's table reads $FFFF (its file engine keeps its own structures).
      PLAN, a step at a time, each gated: (1) one layout routine for the CELLS -- MEMSIZ by MAXFILES, STKTOP = MEMSIZ -
      the string space, FILTAB and its table's pointers -- run at boot, by CLEAR and by MAXFILES (generalising
      basic/files.asm layout_from_himem, which hard-codes MAXFILES 1 and 200); FRE must not move; (2) the string heap's
      ceiling = MEMSIZ, so FRETOP = MEMSIZ (heap_reset / strheap_ceiling / the GC); (3) the published cells zerobas
      uses for its own state, one group at a time, out to its own RAM (the RAM map); (4) the FCBs themselves: whether
      zerobas's file engine should keep its state in them is a design question -- ask Joost before.
      THE ORDER (read from zerobas's own source, 2026-11-24): zerobas's file blocks are 267 B a channel, MAXFILES+1 of
      them (sub/strheap.asm strheap_chantab, FCH_CTXSZ) -- the reference's 265-byte FCB + its 2-byte table entry -- but
      they sit BELOW the string pool, and the pool sits under HIMEM: [blocks][strings]HIMEM, where the reference has
      STKTOP[strings]MEMSIZ[FILTAB table + FCBs]HIMEM. Same pieces, same total (so FRE agrees), other order. So steps
      (1) + (2) of the plan are ONE unit: swap the order (blocks between MEMSIZ and HIMEM, strings between STKTOP and
      MEMSIZ: strheap_chantab / strheap_floor / strheap_ceiling, the file engine's block lookup, CLEAR / MAXFILES), then
      write the cells and FILTAB's table by the measured rule. FRE and every file / string suite are the regression check.
      THE DESIGN (2026-11-24, from sub/strheap.asm): the whole map is DERIVED from HIMEM (C = min(HIMEM, TXTCEIL)),
      POOLSIZE and MAXF in three routines -- strheap_floor (C - POOLSIZE), strheap_chantab (floor - (MAXF+1) * 267),
      strheap_varceil (= chantab, clamped to CSP) -- plus main ROM heap_reset (FRETOP := C) and layout_from_himem (the
      cells, boot only). THE SWAP = new derivations: MEMSIZ = C - (MAXF+1) * 267 - 2; chantab = MEMSIZ + 2 (the blocks
      fill [MEMSIZ+2, C)); the string pool [MEMSIZ - POOLSIZE, MEMSIZ), heap_reset FRETOP := MEMSIZ; varceil = the
      pool's floor (= STKTOP); then the cells by the measured rule at boot / CLEAR / MAXFILES. ⚠️ 2 BYTES TO SETTLE BY
      MEASUREMENT: zerobas's varceil today is $F0A2, the reference's STKTOP $F0A0, and FRE(0) agrees -- the swap must
      keep FRE(0) (find what FRE(0) is computed from before moving varceil). FILTAB's table is NOT written in this
      unit: its first 2 * (MAXF+1) bytes would overlap zerobas's block 0 (blocks are 267 B, the reference's FCBs 265 B
      after the table) -- that is the FCB-structure question (plan step 4), for Joost.
      ➡️ WHEN THE SWAP LANDS (Joost 2026-11-24): hand it to C-BIOS as an item in its private inbox -- the reference's
      live layout rule (MEMSIZ / STKTOP / FILTAB / FRETOP / NULBUF through boot, CLEAR, MAXFILES), FILTAB's pointer table,
      how zerobas reordered its memory with FRE unchanged, and the measured numbers as acceptance (C-BIOS's own BASIC
      cartridge has CLEAR / MAXFILES too).

      ✅ STEPS (1)+(2) DONE 2026-11-24: the order is MS-BASIC's. sub/strheap.asm strheap_memsiz = min(HIMEM,TXTCEIL)
      - (MAXF+1)*267 - 2; the pool is [MEMSIZ - POOLSIZE, MEMSIZ) and the GC compacts against MEMSIZ; the channel
      blocks sit at FILTAB = MEMSIZ + 2 (table 2*(MAXF+1) B, then FCB #0..); varceil = STKTOP. sh_ctl_reset publishes
      STKTOP, main's heap_cells (basic/main.asm, past the low region's pins) MEMSIZ / FRETOP / FILTAB / NULBUF from it at
      every clear_vars (boot, RUN, NEW, CLEAR, MAXFILES). Boot / CLEAR 300,&HC000 / MAXFILES=3 / MAXFILES=0: MEMSIZ,
      STKTOP, FRETOP, FILTAB, NULBUF and SAVSTK equal the VG-8020's, FRE("") / FRE(0) unchanged. The pool top fell 2 B
      (the MEMSIZ..FILTAB gap), so sh_free_vars counts varceil - ARYEND and the four reserves moved 2 B to keep every
      edge absolute: STK_EDGE 131->129, STK_STORE 141->135 (also re-based off FCB #0 onto STKTOP), STK_EVAL 115->113,
      STK_ALLOC 88->86 (dimedge 14/14). STILL OPEN: (a) the VG-8020's FRETOP reads MEMSIZ + 1 after `CLEAR n,addr`
      (not after `CLEAR n` or MAXFILES; re-checked, reproducible) -- zerobas reads MEMSIZ; (b) FILTAB's pointer TABLE
      contents (its bytes are reserved, still unwritten); (c) plan step (4) (step (3): below).

      ✅ **STEP (3) DONE 2026-11-25, 29 of the 30 bytes** (six commits, one cell group each). RE-MEASURED FIRST
      (`memboot_probe.py` + `sysdata_diff.py`): the list was the one above, FRETOP already agreeing.
      📏 WHERE THEY COULD GO, decided by measurement, not by a delta between names: FRE and HIMEM rule out RAM below
      HIMEM, and $F39A-$FD99 has no unnamed free byte that is not a reference cell. So the hosts are the work-area
      bytes MSX1 BASIC does not define: TRPTBL's reserved tail past its 18 entries, and the MSX2-only bytes of the
      MSX1 RS2IQ, $FAF5-$FB02 (DPPAGE .. LOGOPR; $FB03 up is the RS-232C area, DRVINF, left alone). On the VG-8020
      both read 0 through a boot, a program RUN (FOR / GOSUB / READ / DEF FN), CLEAR 300,&HC000, MAXFILES=3 / 0,
      FILES (diskless), PLAY, SCREEN 2 + LINE / CIRCLE / DRAW / PAINT, KEY / INTERVAL / STRIG traps, ON ERROR, NEW
      (twelve snapshots, controls moving: MEMSIZ, the PLAY cells, GRPACX, TRPTBL's head):
      [`AE_bootcells3_hosts.out`](../../scratchpad/AE_bootcells3_hosts.out) by
      [`bootcells3_hosts_probe.py`](../../scratchpad/bootcells3_hosts_probe.py). zerobas already had DRAW's
      TRANSIENT cells in most of those bytes, so each group is a SWAP: the state cells take the reserved bytes,
      the transients take the PARM1 / PARM2 / CONLO / SUBFLG bytes the state cells left (where the reference itself
      keeps only residue) -- no byte gains a second user. GFX_DSP / GFX_DTMP took the two hosts inside the DEF FN
      shadow slots ($F7A9, $F7AC): both live only inside one DRAW tenant activation.
      | group | from | to |
      |---|---|---|
      | SUBSLOT / SUBSLOT_OK | SLTWRK $FD09 / $FD0A | LOGOPR $FB02 / TRPTBL $FC88 (trap_init's fill now stops at TRAPSVC) |
      | CSP CTLTOP TSP CTLLIM GSP FSP | PARM1 $F712-$F719, $F703-$F706 | TRPTBL $FC8A-$FC95 |
      | RL_HL / RL_ROW0 / RL_COL0 | PARM2 $F7A9-$F7AD | $FAFE-$FB01 |
      | CSR_ADDR / CSR_CHAR / CSR_ON | PARM1 $F72C, $F734, $F735 | $FAF5, $FAF7, $FAFD |
      | POOLSIZE / TXTCEIL | CONLO $F66A-$F66D | $FAF9-$FAFC |
      | PRGEND / DATASTATE | PARM1 $F6E8 / SUBFLG $F6A5 | TRPTBL $FC96 / $FC98 |
      BEFORE / AFTER: [`AE_bootcells3_diff_before.out`](../../scratchpad/AE_bootcells3_diff_before.out),
      [`AE_bootcells3_diff_after.out`](../../scratchpad/AE_bootcells3_diff_after.out). Every moved cell's value now
      shows only in the reserved bytes (ref 0 there); PARM1 / PARM2 / CONLO / SUBFLG / SLTWRK $FD09-$FD0A hold the
      VG-8020's values after boot. Equates only (plus trap_init's fill length, the same instruction): the five walls
      of `make basic-reloc` read the same before and after. The RUN entry pinned at $73AC stores PRGEND, so
      tools/pin_plan.py expects the new operand there.
      🔴 LEFT: **KEYARG** ($F856, ARG's last byte, FE after boot, 1 B). The bytes do not add up: 30 B of state against
      29 reserved bytes, because DRAW's GFX_DVAL ($FC99) keeps its overlap with DISKOP_ERR (RTYCNT $FC9A) and so
      frees only one host byte for the two it needs. KEYARG is TRANSIENT (written right before each keystr tenant
      call), so what differs is a leftover, not live state. It needs 1 byte, or a store of 0 after the call (a
      code change). Also still in SLTWRK, all 0 after boot so not in the diff: SUBSLOT2 $FD0B (an unused equate),
      SUB_PING $FD0C and SUB_INT_DELTA $FD0D (self-test cells), STRPTR $FD0E-$FD0F (transient, in the disk ABI) --
      5 B more if SLTWRK is to be empty.
      ⚠️ THE HOSTS' OWN RISK: an RS-232 cartridge (RS2IQ is its queue on an MSX1) or an MSX1 kanji / ROMA-KANA
      extension (CHRCNT / ROMA / MODE) would write $FAF5-$FB02; nothing on the VG-8020 does.
      🔧 APPARATUS: `memboot_probe.py`'s zerobas run hangs in `get_screen` (180 s timeout) after the SYSDATA line is
      written but before it is flushed -- the zb log is cut at 4096 B and `sysdata_diff.py` dies on it. The probe now
      flushes before `get_screen`, so the data survives; why `get_screen` hangs on zerobas is not looked at.

