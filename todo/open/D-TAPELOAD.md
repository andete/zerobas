- [ ] 📼 **D-TAPELOAD — MANY `.cas` AND `.wav` TAPES DO NOT LOAD (Joost, 2026-10-11;
      TRIAGED 2026-10-14, see the end)**
      🏗️ **JOOST 2026-10-28: *"yes, triage the RUNS? tapes after the deferred work"*.** The 21 titles
      tapecorpus_run.py tallies RUNS? (both running, screens far apart): per title, a timing / phase
      difference or a real divergence -- fix ours, file the rest with their evidence. Queued right
      after D-DEFERRSTUDY's current families.
      ✅ **TRIAGED 2026-10-28** ([`runsq_triage.py`](scratchpad/runsq_triage.py) -> [`runsq_triage.out`](scratchpad/runsq_triage.out): both machines every
      2 s T400..T420, bytes apart per VDP table, the BEST ref x zb frame pair, the bytes apart in
      EVERY pair; then side-by-side tile renders, kept in session scratch -- third-party screens):
      | class | titles | reading |
      |---|---|---|
      | timing / phase, nothing persistent | Ballblazer, Blow Up, Lazy Jones, Navy Moves, Sorcery, Demonia, Elite | a frame pair identical or within 108 B |
      | attract-mode phase (render) | Manic Miner (other demo level), Fruit Panic (other caption), Buzz Off (round 0195 / 0200), Ninja 2 (same picture) | small persistent remainders (35-600 B) |
      | timing + ~60 B persistent | Shark Hunter (two windows: best 94 / 136) | an earlier render caught a different phase |
      | speed | Space (zerobas has printed FURTHER: line 2260 / 2190) | TIER 5, paused |
      | font (C-BIOS's glyphs, not the VG-8020's) | Lazer Bykes, Punch & Judy (873 B of pattern table each), Jump Jet, Blocker (+ phase), Blagger | the Loopy Laundry glyph question, parked by Joost 2026-10-17 |
      | real, already filed | Chuckie Egg (zerobas black), Space Shuttle (blue screen), BMX Simulator | D-SLOT3EXP ($FFFF written from game code), parked "Later" 2026-10-27 |
      🔮 Sorcery predicted as timing: hit (best 0). No NEW defect: every non-timing title lands on
      an existing item (font, slot 3) or on speed.
      🏁 **TIER-1 WORK DONE (2026-11-05):** Joost closed the font item (D-BIOSINT) and slot 3
      (D-SLOT3EXP) as WON'T FIX the same day, so the non-timing titles are known
      differences; Space (zerobas printed further) is speed, now TIER 5 work (the pause
      was lifted). What stays here is the corpus run itself, re-run on every ROM change.
      📼 **THE TAPE RUN, REBUILT AND TRACKED (2026-10-22):** the one-off harness and its
      pick_martos (51) lived in a lost session scratchpad, and the standing rule below (re-run
      ALL the tapes after a page-0 / page-1 layout change) was overdue -- D-DISKREST, D-P0CB
      A-C2 and D-COLOREQ all moved main. [`tapecorpus_run.py`](scratchpad/tapecorpus_run.py) +
      [`tapecorpus_pick.list`](scratchpad/tapecorpus_pick.list) (every collection title TODO.md
      names: 42, derived so it can be rebuilt; the collection's location is TAPECORPUS_DIR,
      never written here). openMSX's own autorun types the load command (omsx_preflight
      un-arms it on every launch -- the tool drops that trace first, as basic_probe_autorun.py
      does). [`tapecorpus_run1.out`](scratchpad/tapecorpus_run1.out), VG-8020 vs zerobas
      diskless, the screen at T420: **SAME 9, NEAR 11, RUNS? 21, ZB-PROMPT 1, RESET 0.** 🔮
      "few or no RESET" HIT; "a quarter SAME / NEAR" MISSED low (20 of 42). Most RUNS? rows sit
      at the SAME program line on both (animation phase). Known: BMX Simulator (D-SLOT3EXP, 🙋).
      🔧 **2026-10-27: a still-LOADING machine read as RESET.** `state()` called a direct-
      mode screen with the boot banner on it BANNER, and the banner stays on screen above
      `Found:` while a tape loads -- so Space, sampled at T300, read RESET
      ([`tapeload_space_t300.out`](scratchpad/tapeload_space_t300.out) after the fix). New states ZB-LOADING /
      REF-LOADING (scratchpad/tapecorpus_run.py), checked before the banner. The finding
      behind it is D-ASCTAPESPD (TIER 5).
      🆕 **Blocker** (no history before -- it entered the pick on a stray word): zerobas stops
      with `Undefined line number in 88` (`GOSUB 217`) where the VG-8020 runs on to line 132's
      `HIT SPACE KEY`. A CLOAD tape; loaded, NOT run, zerobas's program is intact (lines 135-140
      and 200-230 list as they should, [`blocker_list.out`](scratchpad/blocker_list.out)); after
      the run line 139 ends in garbage tokens and nothing past 140 is left -- the program text
      is overwritten WHILE IT RUNS. Its setup lines VPOKE the colour table and use
      STOP ON / INTERVAL ON / PLAY ([`blocker_cload.out`](scratchpad/blocker_cload.out), the
      VG-8020's half; zerobas's half of that run lost its timing).
      📏 **NARROWED (2026-10-22, work-area cells and a hash of $8001..VARTAB -- an equality
      check, nothing interpreted):** the game REWRITES ITS OWN PROGRAM TEXT on the VG-8020 too
      -- the hash changes every second from line ~68 on, and its USR routine ($E000, the tape's
      2nd file, `DEF USR=&HE000`) runs from line 260. On zerobas the first change comes at the
      same lines (65-68) and USR is never reached: the WRITES land somewhere else. Ruled out:
      PLAY changing a literal-assigned string in place (own program,
      [`playlit_probe.out`](scratchpad/playlit_probe.out): intact on both -- 🔮 MISSED); CLOAD's
      VARTAB (zerobas $B2CE, the VG-8020 $B2CF -- the reference counts one more zero past the end
      link; POKEd to $B2CF before RUN, zerobas still fails in line 88 -- 🔮 MISSED, unless RUN
      re-derives VARTAB). STANDING DIFFERENCE: the simple-variable area (VARTAB..ARYTAB) is 185 B
      on the VG-8020 against 134 B here at the same lines (52 / 42 at line 15) -- the game's
      `DEF FN`s (five) live in the reference's variable table; zerobas keeps DEF FN in its own
      pool (D-DEFFN). A game that addresses its variables through the work-area pointers writes
      elsewhere on zerobas. Also: MEMSIZ ($F672) reads 0 here, $F168 there; STKTOP ($F674) $F380
      here, $F0A0 there. ➡️ NEXT: measure the DEF FN layout with an own program (DEF FN then a
      variable: VARTAB / ARYTAB and VARPTR of the variable, both machines); if it is the cause,
      that is a D-DEFFN layout item, not a tape one.
      📏 MEASURED the same night -> **D-DEFFNVAR** (filed below): one `DEF FN` makes the
      reference hold one more 5-byte variable entry than zerobas. Whether that is Blocker's
      cause is NOT shown: the game's writes would have to address its variables by pointer
      arithmetic. ➡️ Next for Blocker: list its lines 60-140 on zerobas for POKE / VARPTR and
      see which address it computes.
      ✅ **FOUND AND FIXED the same night -> D-PLAYIY (below): NOT the DEF FN layout.** Lines
      60-90 hold no POKE (🔮 MISSED). A pointer trace
      ([`blocker_trace.out`](scratchpad/blocker_trace.out),
      [`tapetrace_probe.py`](scratchpad/tapetrace_probe.py)) showed VARTAB fixed and the
      line chain cut at line 140's link ($8B03) between lines 25 and 65 -- the reference's
      546 lines stay whole. A write watchpoint on zerobas
      ([`blocker_watch.out`](scratchpad/blocker_watch.out)) caught `pl_voice` storing a
      voice descriptor there from line 62 on (`PLAY "...",A1$,A3$`). After the fix
      ([`blocker_trace_fixed.out`](scratchpad/blocker_trace_fixed.out)) the chain stays 546
      lines and the game runs the lines the reference ran (132, 217-237, 336/338).
      📼 **RE-RUN after D-PLAYIY (2026-10-22, the low region changed):**
      [`tapecorpus_playiy.out`](scratchpad/tapecorpus_playiy.out) -- **SAME 9, NEAR 12, RUNS? 21,
      ZB-PROMPT 0, RESET 0.** Two classes moved, both up: Blocker ZB-PROMPT -> RUNS? (both at
      line 132; it seeds RND from TIME, so the playfields differ), Elite RUNS? -> NEAR. No title
      lost a class; the rest is the VRAM distance of animated screens. 🔮 "Blocker leaves
      ZB-PROMPT, nothing regresses" HIT.
      📼 **RE-RUN after D-LOADBASE / D-HSTKE (2026-10-22):**
      [`tapecorpus_loadbase.out`](scratchpad/tapecorpus_loadbase.out) -- SAME 9, NEAR 10, RUNS?
      22, RESET 1. Boulder Dash and Elite flipped NEAR -> RUNS? on the 128-byte line (129, 198:
      animated screens). 🔴 **Demonia RUNS? -> RESET, reproducible** -- 🔮 "nothing regresses"
      MISSED. Bisected ([`demonia_reset.out`](scratchpad/demonia_reset.out),
      [`demonia_timing.out`](scratchpad/demonia_timing.out)): hstke off -> RUNS?; only the RUN
      site off -> RUNS?; hstke's pushes WITHOUT the hook call -> RUNS?; and with NO hook at all,
      20 nops at that site -> RESET, 40 / 80 -> RUNS?. So D-HSTKE is not the cause: the
      attract demo crashes on some timings whatever the RUN site does -- at T281 the CPU
      reaches $0000 with SP $E1AC over $FFFF words (empty RAM), ~11 ms after an ordinary slot
      switch (the game writes $FFFF = 00 itself, so it knows slot 3 is expanded). Which timing
      the corpus hits is luck; the latent crash is ours. ➡️ What the game executes in the
      last milliseconds before $0000 (a PC ring on zerobas from T280, its own RAM code
      addresses only) -- likely a BASIC / BIOS internal entry it calls (D-BASICINT /
      D-BIOSINT class) on a path the reference survives.
      📏 2026-10-23 (after D-STEP7DATE / D-KEYREP / D-TPAPTAIL (c) / D-F346): Demonia alone
      reads **RUNS?**, both at line 50 ([`demonia_rerun.out`](scratchpad/demonia_rerun.out)) --
      🔮 "still RESET" MISSED: the timing moved again. The latent crash is unchanged in kind;
      today's layout no longer lands on it, and 2026-10-22's 20-nop reproduction was against
      another layout. Not chased further without a reproduction on the current build.
      📼 **RE-RUN after D-DEFFNVAR / D-BLOADSTK (2026-10-24, two page-1 layout shifts):**
      [`tapecorpus_bloadstk.out`](scratchpad/tapecorpus_bloadstk.out) -- **SAME 9, NEAR 12,
      RUNS? 21, RESET 0** (42 titles). Three moved, all up: Boulder Dash RUNS? -> NEAR, Hustler
      RUNS? -> NEAR, Demonia RESET -> RUNS?; none lost a class. 🔮 "RESET 0, nothing
      regresses" HIT.
      📼 **Demonia RESET AGAIN (2026-11-13, after D-INITIO) -- AND NOW REPRODUCED ON THE CURRENT
      BUILD, SO CHASED** ([`tapecorpus_initio.out`](scratchpad/tapecorpus_initio.out): SAME 10, NEAR 11, RUNS? 20, RESET 1; 🔮 "no class
      worse" MISSED; Elite RUNS? -> SAME). Deterministic ([`demonia_run1.out`](scratchpad/demonia_run1.out)); reverting
      initio.patch -> RUNS? ([`demonia_run2.out`](scratchpad/demonia_run2.out)), but so does NOT the value: variant A (reg 15
      only), B (reg 11 only) and **C (no PSG change at all -- 7 NOPs, the same layout)** all
      RESET ([`demonia_A.out`](scratchpad/demonia_A.out), [`demonia_B.out`](scratchpad/demonia_B.out), [`demonia_C.out`](scratchpad/demonia_C.out)). And INITIO runs at boot, so every
      timing after it moves: the game's own INITIO calls (it calls it, from $A747, during its
      load) already arrive 0.09 s apart from the pre-patch run ([`demonia_trace3_head.out`](scratchpad/demonia_trace3_head.out) /
      [`demonia_trace3_pre.out`](scratchpad/demonia_trace3_pre.out)). 📏 **The crash, traced (scratchpad/demonia_probe.py, registers / RAM
      only):** at 279.0973 s the game's OWN RAM code moves SP to $E1AC -- RAM it never wrote,
      $FF -- and returns to $FFFF; executing there pushes $0000 and the machine resets ([`demonia_trace5.out`](scratchpad/demonia_trace5.out),
      [`demonia_trace6.out`](scratchpad/demonia_trace6.out): the only writes to $E1A8.. are that push). The SP value is in no work-area
      cell ([`demonia_trace7.out`](scratchpad/demonia_trace7.out)); no data read of the moved ROM bytes ([`demonia_trace2.out`](scratchpad/demonia_trace2.out)). 🔴 A
      hypothesis RULED OUT: a BIOS call returning with interrupts enabled where the reference
      leaves them off (a game borrowing SP under DI) -- 14 entries the game calls in its last
      60 ms, called under DI, return with the SAME IFF on the VG-8020 and here ([`bioseif_probe.py`](scratchpad/bioseif_probe.py)
      -> [`bioseif_run1.out`](scratchpad/bioseif_run1.out)). Standing: a timing-selected path in the game's own code; the input that
      selects it is not found. D-INITIO stays (two references agree on it). ➡️ Which value the
      game's code turns into SP $E1AC -- a PC ring over its RAM code in the last 0.1 ms before
      279.0973 (the transitions log shows only BIOS crossings), then where that value came from.
      🎚️ TIER 1 — happy path: loading existing software from tape.
      🤖 **AUTONOMOUS** — since 2026-10-14 (it waited on the failing tapes
      themselves): a tester's report (Quibus, relayed by Joost) names ~45 that fail
      and ~40 that load, and the files are on this machine (outside the repo:
      run, never decoded, never copied in, never part of a gate).
      Joost: *"many .cas and .wav tapes are not loading"*.
      📌 **2026-10-16, after D-WSZERO closed** (zerobas keeps no state in program
      RAM, the diskless ceiling is $F380): the same 51 read SAME 14, RESET 3 --
      **Buzz Off, Shark Hunter and Loopy Laundry still reset** (back at the boot
      banner, T1 L65535 PC $01D8, while the VG-8020 runs them). Not the
      workspace any more: the class-A hypothesis below (a published BASIC-ROM
      entry point zerobas does not provide, or reference RAM state it does not
      keep) is now the one to measure, per title.
      📏 **MEASURED THE SAME DAY** (tape_triage's TRANS log: every distinct
      transfer of control from RAM into $0000-$7FFF, interrupts excluded -- PC
      values only, no ROM byte read, run outside the repo): the three are TWO
      classes, and neither is the workspace.
      (A1) **Buzz Off and Shark Hunter call the reference's BIOS INTERNALS**:
      their game code jumps to ~90 addresses in $0748-$0820 and $0D12-$126B, and
      $0468 / $046B / $046E -- inside the MSX BIOS, not its published jump table.
      zerobas's BIOS is C-BIOS (repacked), whose internals are elsewhere, so the
      jumps land in unrelated code and the machine resets. The BASIC ROM is not
      involved. 🙋 **A scope question for Joost**, beyond D-BASICINT's ruling
      (which covers the BASIC ROM's undocumented entries): should the repacked
      C-BIOS provide the reference BIOS's internal entry points at their
      addresses? (Black-box only, like D-BASICINT; a large surface.)
      📏 **DO THESE TITLES RUN ON OTHER MSX MODELS? (Joost 2026-11-01: "it may be interesting
      to see if these titles run at all on e.g. an MSX2 or other different MSX" -- asked
      before ruling on (A1) and D-BASICPUB's scope.)** Measured 2026-11-01 with
      `tapecorpus_run.py --ref <machine>` (the tape RUN, never decoded; its state at
      T60..T420): on the **Toshiba HX-10** and the **Canon V-20** (European MSX1s) Buzz Off,
      Shark Hunter, Harry Fox and Punch & Judy end in the SAME states as on the VG-8020
      (the HX-10 even at the same distances) -- they RUN
      ([`tapes_xmachine_Toshiba_HX-10.out`](scratchpad/tapes_xmachine_Toshiba_HX-10.out),
      [`tapes_xmachine_Canon_V-20.out`](scratchpad/tapes_xmachine_Canon_V-20.out)). On the
      **Philips NMS 8250** (MSX2) Buzz Off, Shark Hunter and Harry Fox RESET after loading
      (`Disk BASIC version 1.0` / `Ok` by T180), and Punch & Judy stops at `Disk offline in
      10` (the disk drive's default device, not MSX2 as such)
      ([`tapes_xmachine_Philips_NMS_8250.out`](scratchpad/tapes_xmachine_Philips_NMS_8250.out)).
      The **Sony HB-75P** run is NOT a reading: all four rows sit at `S2 L0`, the machine's
      built-in firmware rather than BASIC, so the tape never loaded
      ([`tapes_xmachine_Sony_HB-75P.out`](scratchpad/tapes_xmachine_Sony_HB-75P.out)).
      Loopy Laundry is not in the tape pick list (not run). 🔮 HIT both ways ("MSX1s run
      them, the MSX2 does not"). ➡️ So these internals are STABLE ACROSS THE MSX1 BASIC 1.0
      FAMILY and broke with MSX2 -- input for Joost's scope ruling, not a ruling.
      🏗️ **RULED (Joost, 2026-11-01):** *"record these expected internal addresses (game +
      which address, no further investigation needed now) but we can't already be compatible
      with all of them yet. We still have completeness and correctness and size constraints
      already as big challenges."* -> RECORDED in
      [`docs/game-internal-addresses.md`](docs/game-internal-addresses.md) (supported, recorded,
      other models); no further investigation, no new entries. $2010 (the font) stays PARKED
      (Joost, same day: "keep it parked").
      (A2) **Loopy Laundry (pick_martos's copy) calls ~25 BASIC-ROM internals**
      besides the pinned $73AC: $4604 $4649 $4669 $4B02 $4C70 $4CA9 $4DDC $593F
      $5EAC $629D $62A4 $62B2 $62F3 $6686 $67F1 $6AB6 $6AF9 $6B12 $6C48 $6F18
      $6F92 $732B $732E $7331 $79CF, and the BIOS internals $01C4 / $1462 / $1B49
      -- several sit next to D-BASICPUB's documented entries (CHRGTR $4666,
      FRMEVL $4C64, PTRGET $5EA4, FRESTR $67D0), so this title is D-BASICPUB's
      scope at full size (D-BASICPUB waits on Joost for scope and tier). ⚠️ The
      2026-10-15 note below that **Loopy Laundry runs** was measured on
      `pick.json`'s copy (another dump, another file); pick_martos's copy has
      reset at T180 in every run since 2026-10-14 -- not a regression.
      🔴 **CORRECTION, THE SAME DAY: (A1) AND (A2) ABOVE ARE WRONG.** The TRANS log
      records every RAM->ROM transfer, RETURNS included: the reference BASIC calls
      its hooks (a `ret` in $FD9A-$FFC9) and they return into the ROM, and a game
      routine the BIOS calls returns into the BIOS. Kept to transfers whose SOURCE
      is game RAM (below $F380) the picture is: **Buzz Off / Shark Hunter** --
      every transfer comes from ONE game address ($EE1A / $BFA1) to many BIOS
      addresses, i.e. a game routine the BIOS calls (a hook handler) returning to
      its caller; on zerobas the same routine returns into C-BIOS's own code.
      They do NOT call BIOS internals, and the A1 question is withdrawn; their
      reset is unlocated. **Loopy Laundry** -- only $73AC (pinned, and zerobas
      reaches it too) and a jump into the BIOS interrupt handler from $CC5D; the
      ~25 "BASIC internals" were hook returns. Its reset at t=68 s is unlocated.
      **Demonia** (`Syntax error in 50`) -- its machine code CALLS **$72E9 and
      $72D4**, undocumented BASIC-ROM internals; on zerobas $72E9 is inside
      FIELD's code (`exf_havech`), which raises the Syntax error: the D-BASICINT
      class, ruled autonomous (characterise black-box, implement at the address).
      ✅ **2026-10-16: Demonia RUNS** -- D-BASICINT2 pinned both entries, then
      D-BIOSREGS matched five C-BIOS register contracts its game code depends on;
      it plays the VG-8020's attract demo. Corpus (pick_martos, same list as the
      morning): SAME 15, RESET 3 (Buzz Off, Shark Hunter, Loopy Laundry), IOERR 1,
      no title worse. ✅ **2026-10-17: Buzz Off and Shark Hunter RUN** (D-BIOSINT,
      $0D12). 📏 **Buzz Off and Shark Hunter's reset LOCATED the same day**:
      both CALL the reference BIOS's internal $0D12, which is C-BIOS's reset on
      zerobas -- D-BIOSINT, a scope question for Joost. **Loopy Laundry**
      (pick_martos) -- LOCATED the same day, and it is the same class. Its second
      BLOAD loads $C400-$F3FF (exec $EA60; zerobas's own CURPTR / ENDPTR /
      EXECPTR cells), over the stack: the file PLANTS a return chain there, and
      the `ret` at the end of the load (zerobas: bl_apply_ofs, SP=$F08E) follows it
      -- $2010, $18E8, the hook cell $FED0, $3002, ... -- reference-ROM internal
      addresses, each presumably a short tail like D-BASICINT's $3297. On zerobas
      $2010 / $18E8 are C-BIOS code (D-BIOSINT's scope) and $3002 is BASIC's
      ary_engine_call (D-BASICINT's), and the machine resets at t=68.46. ⚠️ It
      also needs zerobas's stack at that `ret` where the reference's is -- not yet
      compared. (Corrections on the way: "page 1 mapped to RAM" was zerobas's
      own sub-ROM BLOAD tenant in slot 3-2 -- A8=$FC with slot 3 expanded -- and
      the EXPTBL hypothesis was refuted: nothing reads EXPTBL / SLTTBL from t=8 to
      30 s. Two harness logs that held game bytes -- stack words after the load,
      and AF in the load loop -- were deleted unread past the first lines; the
      harness now blanks both.)
      (D) **Head over Heels' `Out of memory in 40`** is a GOSUB refused at 671 B
      free by the 768-B frame margin, where the reference keeps ~130: filed as
      D-GOSUBOOM (TIER 1), with the reference's own behaviour after a trapped
      overflow measured.
      ➡️ Measure first, per tape, on the VG-8020 and both builds: WHERE it
      stops -- no `Found:` (the leader / header / baud detection: TAPION,
      `cas_baud`), a `Device I/O error` mid-file (TAPIN's edge timing against
      a real recording's drift and noise -- `.wav` exercises this, a `.cas`
      does not), or a load that completes and then crashes (a loader that
      calls the BASIC ROM's own entry points, or reads reference RAM state
      zerobas does not keep -- a compatibility question, not a tape one).
      Classify first; the three classes have different fixes and different
      tiers. Synthetic rows (cas_encode, 1200 / 2400 baud, short / long
      leaders, multi-file tapes) can start before the corpus arrives.
      📏 **TRIAGED 2026-10-14** (a one-off run outside the repo: each `.cas`
      loaded on the VG-8020 and on zerobas diskless with the loader its header
      names, VRAM / VDP registers / CURLIN / PC dumped at 60, 180, 300 and 420 s
      of emulated time; 42 reported titles found). The reported verdicts held:
      the controls (River Raid, Arkanoid, Navy Moves, Deus Ex Machina, Pac-Man)
      reach the same screen on both. The failures fall into five classes:
      **A. THE MACHINE RESETS** -- 13 titles (Manic Miner, Buzz Off, Shark
      Hunter, Boulder Dash, Chuckie Egg, Blow Up, ...): the load completes and
      zerobas is back at its boot banner while the VG-8020 runs the game.
      Hypothesis, NOT yet measured: the game's own code calls a published
      MSX-BASIC ROM entry point (the math pack, CHRGTR, ...), which zerobas,
      with C-BIOS at $0000-$2764 and its BASIC from $2765, does not have at
      that address. ➡️ Measure first which addresses the failing code enters.
      **B. THE TAPE READ FAILS** -- `Device I/O error` (Disc Warrior, Jump Jet,
      Gunfright, Harry Fox) or `Found:` then back at the prompt (Grog's Revenge,
      Humphrey, Lazer Bykes, Loopy Laundry, Hustler, Mutant Monty).
      **C. THE GAME'S OWN LOADER REPORTS A LOAD ERROR** (City Connection, Ninja 2,
      Oil's Well): machine code reading the tape through the BIOS (TAPION /
      TAPIN), which is C-BIOS's implementation here.
      **D. A BASIC ERROR IN THE LOADER** -- `Syntax error in 50` (Demonia),
      `Out of memory in 40` (Head over Heels: the RAM gap, TIER 4), BMX
      Simulator stuck at line 40.
      **E. A CRASH INSIDE THE INTERRUPT HANDLER** (Sorcery, Elidon).
      ✅ **FIRST FIX, D-BLOADRTAIL (2026-10-14):** Demonia's line 50 is
      `BLOAD"CAS:...",R:RUN`. A synthetic tape showed the cause: after
      `BLOAD"CAS:",R` zerobas dropped the rest of the line (and ended a program)
      where the VG-8020 runs it -- `,R` was a `jp`, not a `call`. Re-run after
      the fix (same tapes): Ballblazer and Game Over now reach the reference's
      screen byte for byte, Grog's Revenge within 14 B; Lazer Bykes gets as far
      as `Undefined line number in 410`, Demonia to `Missing operand in 50`
      (the loaded part replaces the program, probably), and Chuckie Egg, Knight
      Tyme and Lazy Jones now fail later than before. 🔮 "the `Found:` group
      recovers": HIT for Grog's Revenge and Lazer Bykes (partly), MISS for
      Loopy Laundry and Punch & Judy (a different loader shape).
      ➡️ Next: D first (cheapest, one line each), then A (largest), B and C.
      HAL (the tester's "crashes on line 600, probably PRINT USING") is likely
      D-PULONG, fixed 2026-10-14; a re-test with the new nightly is asked for.
      📏 **RE-RUN AFTER D-WSZERO SLICES 1-4 (2026-10-14):** 8 more titles reach
      or approach the reference (D-WSZERO has the list). The 10 still in class A
      are mostly NOT entry points: 6 reset because zerobas's stack sits 2.3 KB
      below the reference's ($E6A6 vs $F09E, no `CLEAR` in the loader) and the
      game's data lands on it -- D-WSZERO's ceiling, bottom-up. Still open as
      before: B (Fruit Panic, Harry Fox `Device I/O`; Loopy Laundry, Punch &
      Judy `Found:` -- 🔧 2026-10-15, D-BASICINT's pins: Loopy Laundry RUNS, and
      Punch & Judy now stops with `Device I/O error in 10` on its next tape load,
      joining Harry Fox; class B is now "a BASIC-level tape load fails with
      Device I/O" -- 📏 MEASURED THE SAME DAY, and it is TWO defects, not one
      (session triage harness, outside the repo: every TAPION return and every
      TAPIN that set CF, with caller, CF, LOWLIM / WINWID -- never A; and the
      TRANS log of RAM -> ROM transitions, PC values only):
      (B1) **Punch & Judy = D-TAPLEAD's pinned residual `mid`, on a real tape.**
      zerobas's BASIC loader calls TAPION ~2.6 s earlier on the tape than the
      VG-8020's (the game leaves the motor running while BASIC works), TAPION
      returns CF=0 with **LOWLIM $2A against every normal lock's $15**, and the
      next TAPIN sets CF -> `Device I/O error in 10`. The VG-8020 locks at
      LOWLIM $0D. Same signature as the gate row (41 vs 21): a run of LONG
      halves taken for the leader's short. -> D-TAPLEAD's residual is now TIER 1.
      ✅ FIXED THE SAME DAY (D-TAPLEAD's residual, above): Punch & Judy now
      loads past line 10; its NEXT divergence (one extra TAPIN before its third
      load, then direct mode on a graphics screen from T180) is open.
      📏 **THAT NEXT DIVERGENCE IS D-WSZERO, NOT TAPE (2026-10-15).** A per-caller
      count of TAPION / TAPIN calls between the second and third file (the stack
      word at entry and SP -- never A) shows the second file's data block read in
      full on both machines (6 + 337 bytes, the sub-ROM BLOAD loop), and then, on
      zerobas only, a TAPION + TAPIN called from RAM at $E9DD with SP = $E9DC --
      while zerobas's own stack sat at SP $EA02-$EA04 during that BLOAD. The
      game's file loads over zerobas's STACK (the reference's is near $F0xx and
      that RAM is free there), a `ret` runs game bytes out of context, they call
      the tape, and the stray TAPIN eats the third file's first header byte: the
      search then skips that file (24 s later) and the game ends at the prompt.
      -> Punch & Judy joins D-WSZERO's RESET class (its window, its ceiling);
      no tape fix applies. B2 (Harry Fox) is NOT this: its stacks are normal
      (SP ~$8CA5 after its CLEAR on both) and no RAM code calls the tape; zerobas
      just runs four more header + program loads (sub-ROM loaders) than the
      VG-8020 -- its BASIC takes another path; locate it with a line trace.
      📏 **B2 NARROWED (2026-10-15): HARRY FOX ASKS FOR A DIFFERENT FILE NAME.**
      A CURLIN sample every 0.25 s (a line NUMBER, never the program): the
      VG-8020 leaves line 50 after its second load and runs 140 .. 400 (the next
      program); zerobas stays on line 50. On zerobas that search wants $41 (BLOAD
      + a NAME, CAS_WANT_ON) and the header IS $D0, yet it SKIPS (csd_bin) every
      file to the tape's end. An EQUALITY witness -- a hash of the published
      FILNAM ($F866, 6 B) at each search, never the bytes -- reads $34D1 on the
      VG-8020 and $36B2 on zerobas at line 50, against the SAME $AD06 on both for
      the first (direct) BLOAD, the control. So the program BUILDS a different
      name here; the search is not at fault: OUR tapes
      ([`casname_probe.py`](scratchpad/casname_probe.py) ->
      [`casname_run.out`](scratchpad/casname_run.out),
      [`casname_run2.out`](scratchpad/casname_run2.out),
      [`casname_run3.out`](scratchpad/casname_run3.out)) match alike on BOTH
      machines for `CAS:` / `cas:` / `Cas:`, trailing spaces, a kana name, a
      name built by an expression, a name longer than six, and skip alike for a
      space after the colon, a lowercase name, $00 padding and a short prefix.
      🔮 "a lowercase device separates them": MISS; "zero padding or a prefix":
      MISS. Also ruled out: the BIOS ID bytes $002B-$002D are never read (a read
      watch, addresses only); zerobas runs NO `PEEK` between t = 20 and 24 s (a
      breakpoint on PEEK's own `ld e,(hl)` in OUR ROM, $4EDB -- verified in the
      listing), and raises NO error through raise_error between 13 and 30 s (so
      not an ON ERROR detour). The VG-8020's line samples show 30 -> 45 -> 50 and
      zerobas's 30 -> 50, but a 0.25 s sample can miss a fast line: weak.
      ➡️ Still to try: INP / USR / VDP / STICK / INKEY$ as the input (breakpoints
      on OUR ROM's handlers), a finer CURLIN trace (a breakpoint on the line
      dispatcher, line numbers only), and errors raised by other paths
      (stmt_error $4306).
      🔴 **CORRECTION (2026-10-15, later the same day): THE "NO PEEK" AND "NO
      raise_error" LINES ABOVE WERE NEVER MEASURED.** Their harness edits put Tcl
      braces inside a Python f-string -- a SyntaxError -- so every run from the
      PEEK edit on died before the emulator started, and an absent output file
      read as "nothing fired". Re-measured with the harness fixed AND a positive
      control (exec_stmt fires 4 / 6 / 1 / 1 times on lines 30 / 40 / 45 / 50):
      no FRE, INP, USR, VDP, PEEK, TIME, STR$, CHR$, HEX$, INKEY$, LEFT$, MID$,
      RIGHT$, STRING$, SPACE$, VAL, ASC, LEN or INSTR runs in lines 30-50 on
      zerobas. A CURLIN write-watch (every change, line numbers only) gives
      65535 -> 65310 -> 30 -> 40 -> 45 -> 50 on BOTH machines: line 45 is NOT
      skipped (the 0.25 s samples missed it). FILNAM-hash control done properly:
      OUR tape's `BLOAD"CAS:AB"` hashes $21A4 at the search on both machines, so
      the witness holds -- Harry Fox's line 50 still asks for $36B2 vs $34D1.
      📏 **AND A REAL DEFECT ON THE WAY: D-VARTABADOPT (fixed).** An EQUALITY
      witness on the program text -- a hash and the length of [TXTTAB, VARTAB)
      at every line change -- reads $088F / 1302 B on the VG-8020 throughout,
      but on zerobas VARTAB - TXTTAB fell to 2 at the first line after the ,R
      loader: Harry Fox's first file loads its BASIC program and SETS VARTAB, as
      the reference keeps the program end there; zerobas derives VARTAB from its
      own PRGEND, and the next variable reset put VARTAB at an EMPTY program's
      end -- variables then stored over the program's text. Fixed byte-neutral
      ahead of the pins: BLOAD,R's `call nz,lh_jphl` -> `call nz,lh_runr`
      (syncs VARTAB := PRGEND + 2 before the code runs) and lh_back's `jp
      exec_stmt` -> `jp lh_adopt` (PRGEND := VARTAB - 2 after it) -- a no-op
      unless the code moved VARTAB, so a VARTAB stale from another path cannot
      leak in. Page 1 46 -> 20 B (2026-10-15). Gate row rvt64 in
      basicint-acceptance (-64 on both); knife K-VA1 (the adoption store cut)
      -> ZB 0, DIVERGES: HIT ([`vartab_knife.out`](scratchpad/vartab_knife.out)).
      With it, Harry Fox's program text stays intact ($088F / 1302 B on both)
      -- 🔮 "and line 50 then matches file 2": MISS, the name still differs
      ($36B2); bare `BLOAD"AB"` / `BLOAD"AB",R` match alike too
      ([`casname_run4.out`](scratchpad/casname_run4.out)). Parked: the input of
      that name is still unlocated.
      ✅ **LOCATED AND FIXED 2026-10-17 (D-CASDOT): THE NAME HAS A DOT.** The
      published pointer cells at lines 40-50 (a CURLIN write-watch, addresses
      only) read VARTAB = ARYTAB = STREND on both machines -- no variables at
      all; on zerobas a breakpoint on exec_stmt fires ONCE on line 50 (the
      positive control) and READ / RESTORE never: line 50 is one BLOAD with a
      literal name, the same text on both. A witness that says only WHICH of
      FILNAM's six bytes agree (a salted non-linear hash per position, the salt
      random per run and never printed) read `====xx`: the last two differ.
      Our own tapes then gave the rule (casname_run5*.out): the VG-8020 ends a
      `dev:name` name at its '.'. 🔮 "a '.' is copied raw by the reference and
      cut by zerobas": MISS, the other way round. Harry Fox now gets past line
      50: IOERR -> BASICERR, the program its loader RUNs next stops with
      `Out of memory in 30` -- ➡️ D-HFOXOOM below, ✅ fixed the same day:
      **Harry Fox RUNS** (its title screen as on the VG-8020).
      📏 **THE REAL TAPES AFTER D-BIOSINT / D-CASDOT / D-HFOXOOM (2026-10-17, the
      one-off run outside the repo, pick_martos, 51 titles; classes only):** SAME
      14, RUNS? 32, RESET 1 (Loopy Laundry -- D-BIOSINT's 🙋, the font), ISRCRASH 1.
      Against the morning's run: Buzz Off, Shark Hunter RESET -> RUNS?, Harry Fox
      IOERR -> RUNS? (🔮 HIT). Two others moved and neither is new: BMX Simulator
      RUNS? -> ISRCRASH reads identically to the morning's up to T300 (both runs
      leave line 50 for the prompt by then) and only its final state flips, as
      recorded above; Ballblazer SAME -> RUNS? is a phase at the last dump (it was
      512 B apart at T300 in the morning too). ➡️ Next by evidence: BMX Simulator
      leaves line 50 between T180 and T300 where the VG-8020 stays on it -- 📏
      LOCATED the same day: D-SLOT3EXP below (🙋, the machine's slot shape).
      📏 **WHERE THE OTHER BIG DIFFERENCES START (2026-10-17; ten RUNS? titles,
      zerobas's VRAM at each dump against EVERY VG-8020 dump of the same run --
      counts of differing bytes only):** Klax is IDENTICAL to T300 (0 B) and apart
      by T420; Elite identical at T180, apart by T300; Ninja 2 and Manic Miner
      near (1074 / 712 B) to T300, apart by T420 -- a real divergence onset to
      chase, in that order. Blagger, Lazer Bykes and 737 Flight (all SCREEN 1)
      keep a steady 2800-4300 B from the start, the size of a font difference
      (zerobas draws C-BIOS's) -- probably not a defect, unconfirmed. Chuckie Egg:
      D-SLOT3EXP. ➡️ Next: Klax between T300 and T420. 📏 Narrowed the same
      day: Klax parts between T320 and T340, and never writes $FFFF (see
      D-SLOT3EXP's notes: its RAM already differs at T320 in three game cells).
      Manic Miner TRACKS the VG-8020 at ~700 B from T400 to T540 (zerobas's dump
      against every VG dump); its T420 split was a transient at a screen change,
      the other way round at T445 -- not a defect by this reading. Elite and
      Space Shuttle write $FFFF from game code: D-SLOT3EXP candidates.
      📏 **AND THE ONSETS ARE MOSTLY PHASE (2026-10-17):** Klax writes its three
      diverging cells from the same PCs every frame on both machines, but zerobas
      runs 40 ms (two frames) BEHIND -- the "same PC at T300 / T320" was the frame
      loop coinciding -- and the frame-timed attract demo then parts (🔮 "a code
      path differs": MISS); it never touches $FFFF after its loader's slot scan
      (a read watch). Ninja 2 tracks at ~1070 B to T380, then from T400 shows a
      screen 12 KB from every VG-8020 dump, in the SAME loop (PC $40DF / $40E2,
      SP, VDP registers all equal): the demo's state moved on differently --
      likely the same load-timing phase, unproven. Elite holds a steady ~3150 B
      from T300 (and writes $FFFF: D-SLOT3EXP). **So D-TAPELOAD's corpus now holds
      no located functional divergence that is not waiting on Joost** (D-BIOSINT's
      font, D-SLOT3EXP's slot shape): what remains is load timing (zerobas's tape
      load ends a few frames off the VG-8020's), steady SCREEN 1 font-sized gaps,
      and titles that track.
      🆕 Found on the way (OUR tape): a named BLOAD whose file is NOT on the tape
      -- the VG-8020 keeps waiting at the end; zerobas raises `Device I/O error`
      after ~5 s of silence (TAPION's CAS_FLATMAX budget). 🎚️ TIER 6, unfiled
      beyond this line until a tester meets it.
      (B2) **Harry Fox is NOT a tape defect.** Both machines load the SAME four
      files (TAPIN counts 16 / 1336 / 1352 / 10287 / 10303 / 12440 / 12456
      identical); then the VG-8020 starts the game while zerobas's BASIC goes on
      loading four MORE files until the tape ends (TAPION CF=1 at t=246 s ->
      `Device I/O error in 50`). Where its BASIC diverges is not located yet.
      🔴 AND D-BASICINT'S HARRY FOX PREMISE WAS WRONG: the TRANS log shows the
      SAME game instruction ($8033) transferring to $6CF3 on the VG-8020 and to
      $6545 -- our lh_back -- on zerobas, i.e. it RETURNS through BLOAD,R's
      return address; it does not hard-code $6CF3. The entry-state log saw the
      reference's own return points. The $6CF3 / $3297 pins are correct (the
      black-box rows) but Harry Fox does not need them; $73AC IS hard-coded
      (Loopy Laundry runs because of it). Whether Punch & Judy's $3297 is a
      return point too is unmeasured. 🔮 Scored: "TAPION returns carry on the
      BASIC-level load": MISS for Punch & Judy (TAPION locked WRONG with CF=0;
      TAPIN carried), and for Harry Fox a hit in letter only (the carry is the
      end of the tape, not the cause), C (City Connection, Ninja 2, Oil's Well -- all stop at
      the same PC), D (Head over Heels `Out of memory`), the `PC 0038` loop
      (Chuckie Egg, BMX Simulator's later crash).
      ✅ **CLASS C FIXED: D-TAPLEAD (2026-10-14) -- `TAPION` LOCKED ONTO DATA.**
      After D-WSZERO slices 5-7, class C held five titles (City Connection,
      Ninja 2, Oil's Well, Blow Up, Exterminator), all ending on the same screen
      of one shared machine-code loader, `Load error or aborted`, at the same PC.
      📏 The triage harness logged only the published tape entries ($00E1 /
      $00E4 / $00E7) -- the caller word and, at each return, the CARRY and the
      published LOWLIM / WINWID; never A, which for TAPIN is the game's byte (one
      first run did print A; its output was deleted and the harness changed).
      The loader calls TAPION while the previous file is still playing: the
      VG-8020 waited for the next leader and read 641 bytes; zerobas returned in
      ~27 ms with a long-half LOWLIM and the next TAPIN set carry. Our TAPION
      (tape/tape.asm) accepted ANY 256+16 carrier halves without a flat.
      🔮 "LOWLIM / WINWID values" (forcing the VG-8020's 13 / 10 after the
      loader's TAPION): MISS -- same `Load error`.
      🔧 After LOWLIM, `tapion_verify` requires CAS_VERIFY (128) half-periods in
      a row that are all SHORT; a long half or a flat relocks. Data cannot hold
      that (every byte has a long start bit; the longest run of shorts is ~40);
      a leader has thousands. 14 B in the C-BIOS page-0 tape block, which ran 10 B
      into island 4 ($0CC9, basic/islands.asm's error-message table): paid by
      `call stmotr_on` in TAPION (-2), one shared out/ret tail in stmotr (-1),
      and island 4 moved to $0CCF -- its 50-byte table now fills it exactly
      (tools/build_mainrom.py's ISLAND4_LO follows).
      🔴 My first stmotr reorder put `stmotr_off` where the dispatch FALLS
      THROUGH: STMOTR with A=1 stopped the motor (TAPOON's writes ran motor-off).
      tests/test_tape.py caught it; TAPION was untouched (it calls stmotr_on
      directly now), and the gate rows, the knife and all 51 tapes were re-run on
      the corrected ROM -- identical. A byte-saving reorder is a semantic change
      wherever control falls through.
      📏 Real tapes, all 51 (one-off, outside the repo): SAME 9 -> 12 (City
      Connection, Exterminator, Oil's Well byte for byte), class C 5 -> 0 (Blow Up
      within 723 B of VRAM, Ninja 2 runs on), and as a side effect Fruit Panic
      (`Device I/O`), Chuckie Egg (the `PC 0038` loop) and Formula 1 Simulator
      (reset) now run; NO title that matched before changed. 🔮 HIT.
      📏 Gate `tapionlead-acceptance` (our own two-file tape + our own routine:
      TAPION, A's header, TAPION, K bytes of A's 206-byte data, TAPION AGAIN,
      one TAPIN = B's header byte $D0): k190 / k200 / k204 / end SAME. 🔪
      [`taplead_knife.py`](scratchpad/taplead_knife.py) ->
      [`taplead_knife.out`](scratchpad/taplead_knife.out): K-TL1 (the loop cut,
      byte-neutral -- the first cut added 2 B and overflowed the tape block's
      1-byte margin, NOT SCORED) -> k190 diverges, HIT.
      ⚠️ **RESIDUAL, PINNED:** 🎚️ TIER 1 since 2026-10-15 -- Punch & Judy stops on
      exactly this (class B1 below: LOWLIM $2A vs $15 on a real tape). `mid`
      (K = 8, a TAPION deep inside the data) still
      diverges: it measured a run of LONG halves (zero bits) as its short --
      LOWLIM 41 against a leader's 21
      ([`taplead_lowlim.out`](scratchpad/taplead_lowlim.out)) -- so every half
      classifies short and the verify passes on data. A lower bound would catch
      it, but at these counts (~3 per half at 1200 baud, ~1.5 at 2400) one would
      also reject real 2400-baud leaders: a redesign of the measurement, not a
      patch; and the tape block has 1 B left. Also measured, no row: after
      TAPION the VG-8020 leaves LOWLIM / WINWID 13 / 10, zerobas its own 21 and
      never writes WINWID.
      ✅ **RESIDUAL FIXED (2026-10-15): TAPION'S VERIFY CHECKS FULL CYCLES, BOTH
      WAYS.** After the measure, one settle CYCLE is discarded, then CAS_VERIFY / 2
      (64) cycles must each satisfy cycle*2 < LOWLIM (< 1.75 x the average cycle:
      a 0-bit is data) AND cycle*4 >= LOWLIM (>= 0.875 x: a 1-bit cycle in a lock
      that averaged LONG halves is data). A ratio window, so scale-free on openMSX
      and on hardware. `tapionlead-acceptance` 5/5 SAME, `mid` UNPINNED.
      How it got there (each step measured on openMSX, our ROM, our tape):
      (1) a per-HALF lower bound (B > LOWLIM >> 4, taken free from 7*sum's high
      byte) passed the simulator and refused EVERY real leader -- the first
      verify half read B = 1 on 290 of 347 locks
      ([`taplead_bvals.out`](scratchpad/taplead_bvals.out)): the LOWLIM
      arithmetic eats most of the half in progress. (2) Full cycles with ONE
      settle half: the first verified cycle still read 4-5 against the leader's
      steady 6 ([`taplead_cycles.out`](scratchpad/taplead_cycles.out), the lower
      bound disabled for the measurement). (3) A settle CYCLE: 5/5.
      🐛 Found on the way: tapion_haveavg copied the sum through DE and CLOBBERED
      D -- cas_half's current level -- so the first verify half was measured
      against a garbage level. Now through BC. tests/test_tape.py's leader grew
      400 -> 440 halves: TAPION genuinely needs 401 once D is right (the old 400
      passed only because of the bug).
      📏 Room: the tape bodies needed ~26 B and had 1. err_msgtab (46 B, error
      codes 1..23 -- 24 and 25 left it, both were `err_subhosted`, which every
      code past the bound already takes; the bound `ERR_MSGTAB_N` is now DERIVED
      from the table) went from island 4 back to main page 1, at the END of
      basic/missing.asm because D-BASICINT's pins sit earlier (46 B added ahead
      of a pin drove its `ds` negative and the build refused). Island 4 is
      retired; the tape may run to C-BIOS's compat tail $0D01, the cap every
      other variant's patch already has (tape_end $0CE8 on 2026-10-15). Moving
      FREE_ORG down into island 3's 8 B padding was rejected: the MSX2 C-BIOS
      mains have content up to $09ED. Cost: main page 1 118 -> 72 B (2026-10-15).
      🔮 Scored: per-half bound "mid SAME, the rest stay": MISS (all five
      diverged); one-settle-half cycles: MISS (all five); settle cycle: HIT.
      🔪 Knives ([`taplead_knife.py`](scratchpad/taplead_knife.py) ->
      [`taplead_knife2.out`](scratchpad/taplead_knife2.out)): K-TL1 (the whole
      verify cut) -> mid + k190 diverge, end SAME: HIT; K-TL2 (ONLY the lower
      bound cut, byte-neutral) -> ONLY `mid` diverges: HIT -- the gate sees the
      new bound and nothing else depends on it.
      📼 Punch & Judy (run, never decoded): zerobas's BASIC loader now locks at
      t = 31.5 s with LOWLIM $15 (the VG-8020: 31.6 s), the next file loads with
      the same TAPIN counts, and at T60 zerobas is in line 770 within 380 B of
      the reference's VRAM. 🔮 "the line-10 load succeeds": HIT. A LATER
      divergence remains (one more TAPIN before the following load, 3093 vs
      3092, which then comes 24 s later; from T180 zerobas sits in direct mode
      on a graphics screen) -- unlocated, filed in class B1 below.
      📼 **All 51 (pick_martos, the SAME collection as the 10-14 baseline
      summary_m7):** SAME 12 -> 11; better: Punch & Judy, Formula 1 Simulator,
      Knight Tyme. Two worse, each A/B'd against HEAD's tape code on today's tree:
      **Ballblazer** 0 -> 279 B at T420, deterministic -- but TAPION locks within
      0.13 ms of the old code's on EVERY block (the settle cycle), so it is the
      game's animation phase at the dump, not a load difference; **A View to a
      Kill** 54 B -> `Syntax error in 140` at the prompt, IDENTICAL with the old
      tape code -> NOT this change; filed below as 🆕 D-AVTAK. 🔴 And the first
      comparison ran `pick.json` -- the OTHER collection, archive dumps -- against
      summary_m7: six "regressions", and a bisect that failed at every commit.
      The apparatus was the difference [[apparatus-is-part-of-the-measurement]].
      🆕 **D-AVTAK -- A View to a Kill stopped loading: `Syntax error in 140`**
      (🎚️ TIER 1, found 2026-10-15). 54 B from the VG-8020 at T420 on 10-14
      (summary_m7, before D-TAPLEAD's commit) -> zerobas at the prompt with
      `Syntax error in 140` on 10-15, with the tape code of HEAD (6b729794) and
      of the cycle verify alike. Candidates: every ROM commit since 10-14 20:57
      (D-TAPLEAD e30dcfae first -- its own "no title that matched changed" check
      counted only SAME titles, and this one was at 54 B). ➡️ Bisect on
      pick_martos (session triage harness; a worktree build repoints the shared
      machine -- re-repack from main after).
      📏 **BISECTED (2026-10-15): 967cd255, D-BASICINT's PINS.** c19e7fd6 54 B,
      e30dcfae (D-TAPLEAD) 54 B, c577b59c 54 B, 8644bd09 54 B, 967cd255 `Syntax
      error in 140`. 🔮 "c19e7fd6 works": HIT; "D-TAPLEAD first" as the suspect:
      cleared. The TRANS log (RAM -> ROM transitions, PC values only), on the
      good AND the bad build alike, shows the game's code at $C060 going to
      **$73E5** -- the same number on both, so it is HARD-CODED: a fourth
      undocumented BASIC-ROM internal, 57 B past $73AC. (Its `$BDC2 -> $5494`
      is `usr_ret` on both builds: a return through USR's return address, not
      an entry.) On the VG-8020 $73E5 is CALLED (stack top $C063, the game's
      return), three times in line 140, with HL in the game's RAM ($C19E /
      $C1B3), DE $0038 / $8279 / $8277, BC $00F3 / $FB92, A $07 / $83 / $00.
      On the good build zerobas's byte there was `lrset_finish+4` -- a `jr
      z,lrf_var` that the game's Z flag took into an unrelated LSET tail which
      happened to return harmlessly; the $73AC pin shifted `lrset_rhs+6` under
      it. **The pins did not break a feature: they ended a coincidence.**
      📏 **CHARACTERISED (2026-10-15): $73E5 IS THE PLAY STATEMENT'S BODY**
      ([`basicint_73e5_probe.py`](scratchpad/basicint_73e5_probe.py): OUR code,
      run by USR, calls $73E5 with HL at a tokenised text it POKEd; outputs on the
      screen, under ON ERROR). With a garbage buffer at HL: ERR 13 and our code
      after the `call` never runs ([`basicint_73e5.out`](scratchpad/basicint_73e5.out)).
      With TEXT at HL ([`basicint_73e5_t.out`](scratchpad/basicint_73e5_t.out),
      [`basicint_73e5_s.out`](scratchpad/basicint_73e5_s.out),
      [`basicint_73e5_len.out`](scratchpad/basicint_73e5_len.out)): `""`, `"A"`,
      `"AB"`, `"ABC"` RETURN (HL past the argument, at the line's end); `7` and `A`
      -> 13; `"HELLO"` and A$ = "XYZ" -> 5 -- the rule is the CHARACTERS (H, X, Y
      are not music-macro commands), not the length. And right after, PLAY(1)
      reads -1 ([`basicint_73e5_play.out`](scratchpad/basicint_73e5_play.out)):
      the string was QUEUED as music. So the game plays its tunes by CALLING
      BASIC's PLAY handler, HL at its own `"..."` arguments, and it RETURNS.
      🔮 Scored: "it returns": HIT (for valid MML); "it moves or compares memory
      between HL and DE": MISS; my first decoding of DE as the string's address
      was wrong (the bytes there are not the string).
      ✅ **PINNED (2026-10-15): $73E5 = `jp basicint_play`.** basicint_play
      (end of basic/missing.asm, PAST every pin) CALLs PLAY's body `pl_args` (a
      0-byte label after ex_play's `inc hl`), and PLAY's success exit -- was `jp
      exec_stmt`, now `jp pl_exit`, the same 3 B -- RETURNS when the word under
      the cursor is basicint_play's return point, else chains the next statement.
      No RAM flag, so an error raised mid-PLAY leaves nothing behind. The pin sits
      after lrset_tgt's `ret` with a 6 B gap REFILLED by ex_on_key (moved from
      basic/program.asm, whose copy is now the ELSE arm): pad 0, pin waste still
      6 B, `make pin-check` 4/4. Cost: page 1 72 -> 46 B (2026-10-15).
      🔴 **PINS ARE RIGID -- learned twice in this slice.** The first cut grew
      play.asm by 2 B (a pushed exec_stmt + `ret`): play.asm sits AHEAD of the
      $6CF3 / $73AC pins, both at pad 0, so their `ds` went negative -- and
      **pasmo then writes an EMPTY binary with rc 0**; only split_islands' "image
      base $8000 is ABOVE $2765" says so. Re-bridging $6CF3 just carried the 2 B
      on to $73AC. Any growth upstream of a pad-0 pin needs a re-plan; prefer a
      change that is byte-neutral ahead of the pins and puts its bytes AFTER them.
      📏 Gate rows play_ok ("ABC": [OK + PLAY(0..3)] and the HL returned),
      play_e5 ("HELLO"), play_e13 (7): 3/3 SAME, `make basicint-acceptance` 10/10.
      🔪 K-AV1 (basicint_play's call cut, byte-neutral) -> play_ok DIVERGES: HIT
      ([`avtak_knife.out`](scratchpad/avtak_knife.out)). The probe on the pinned
      ROM ([`basicint_73e5_pinned.out`](scratchpad/basicint_73e5_pinned.out)):
      HL and the error codes match on every row; two leftovers, both NOT the
      entry's: (a) "AB" leaves the reference reporting voice 2 busy after a
      DIRECT call, which a plain `PLAY "AB"` does not (same PLAY(0..3) on both
      machines) -- reference state its statement path sets up, not chased; (b)
      A$ = "XYZ" -> the reference raises 5, zerobas plays it -- and a plain
      `PLAY A$` does the same, so it is a PLAY divergence: 🆕 D-PLAYXYZ below.
      📼 **A View to a Kill: 54 B at T180 / T300 / T420 again**, and zerobas now
      reports line 140 as the VG-8020 does (the pre-pin build read 5184). 🔮 HIT.
      🆕 **D-PLAYXYZ -- `PLAY "XYZ"` plays on zerobas; the VG-8020 raises 5**
      (🎚️ TIER 6, found 2026-10-15 by D-AVTAK). `A$="XY"+"Z":PLAY A$` -> `Illegal
      function call` there, nothing here. X is MML's execute-substring and Y is
      not a command; which character the reference refuses is unmeasured.
      ✅ **NO LONGER REPRODUCES (re-measured 2026-11-04,
      [`playxyz_20261104.out`](scratchpad/playxyz_20261104.out)).** 18 rows, VG-8020 and zerobas
      NODISK agree on every one: `"XYZ"`, `"X"`, `"Y"`, `"Z"`, `"W"`, `"Q"`, `"H"`, `"CY"`, `"C XYZ"`
      -> `Illegal function call`; `"XYZ;"` -> `Type mismatch`; `"XA$;"` plays; and the variable /
      concatenated forms (`A$="XY"+"Z":PLAY A$`, `PLAY A$+"Y"`) -> 5 on both. 🔮 "the VG-8020
      raises 5 for X without `;`": HIT; "zerobas still plays it": MISS -- a later PLAY change
      already closed it.
      🔴 **The class lesson:** ANY layout change in page 0 / page 1 can break a
      game that hard-codes an internal address where zerobas's code worked by
      luck; no gate can hold third-party tapes, so the 51-tape run on
      pick_martos is the only guard -- run ALL 51 after a ROM layout change, not
      the titles the change was for (D-BASICINT ran three).
      🙋 **CLASS "FOUND" = GAMES CALLING AN UNDOCUMENTED BASIC-ROM INTERNAL
      (2026-10-14).** Loopy Laundry and Punch & Judy BLOAD,R a binary that, on
      BOTH machines, calls BASIC-ROM address $73AC directly (the harness's TRANS
      log: each distinct RAM -> ROM transition, PC values only). On the VG-8020 a
      stored BASIC program then runs (lines 60 / 3080); on zerobas the stack is
      reset and the prompt comes back. Punch & Judy also calls $3297 there. Neither
      is a published entry point (the BIOS jump table ends at $0180): they are
      interpreter internals, documented only by disassemblies, which
      docs/allowed-sources.md excludes. Black-box ORACLE observation of what a
      call to $73AC does would be admissible, and an implementation would need
      code at that fixed address inside main page 1 (0 B free on 2026-10-14). ➡️ **Joost: should
      zerobas provide undocumented MSX-BASIC internal entry points that games
      call, characterised black-box?** Until ruled, the class is parked.
      📏 **Harry Fox is the same class** (`Device I/O error in 50`): on the
      VG-8020 its second file's code calls the published BIOS (INIGRP, LDIRVM,
      DCOMPR) and then the BASIC-ROM internals $6CF3 (where the reference spends
      ~25 s before the next load) and $3297; zerobas skips that pause, reads on
      past the reference's last file and fails. Three titles, three internal
      addresses: $73AC, $6CF3, $3297.
      ✅ **RULED (Joost, 2026-10-15):** *"Yes, we'll have to figure out those
      undocumented addresses and support them."* -> filed as **D-BASICINT**
      (below): characterise each address BLACK-BOX on the VG-8020, implement it
      at the same address.
