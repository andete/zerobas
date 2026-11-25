- [ ] 🔍 **BOULDER DASH II IS FRAGILE TO LOW-REGION CHANGES THAT PRESERVE EVERY VALUE
      (D-BD2FRAGILE, 2026-10-31).**
      🎚️ TIER 1 — a program that runs on the reference stops running.
      🤖 **AUTONOMOUS** — registers / RAM only, the tape is RUN, never decoded. With batch 6's fp_trunc (identical INT / FIX in value and
      RAM) the title sits at line 10 with the PC in $FCE0-$FD69 from T120 on; without
      it, on the reference's line 3341. Batches 4 and 5 moved its snapshot distance
      too (30 -> 114 -> 27). Earlier history: D-WSZERO's DISKSLOT reset and the S15
      stack collision (docs/TODO-done.md). Measure first: where SP runs during the
      load on both builds against the region the game loads into, and which cells in
      $FC00-$FDFF zerobas writes after the load that the reference does not.
      📏 **FIRST MEASUREMENTS (2026-10-31, [`bd2_probe.py`](../../scratchpad/bd2_probe.py);
      zerobas HEAD vs HEAD + batch 6's fp_trunc, the same tape; RAM images kept OUTSIDE
      the repo, only addresses compared):**
      (1) **Not a wrong value**: 800 INT / FIX cases identical in value and RAM.
      (2) **The game does not read BASIC ROM bytes**: a read-watch on $0000-$7FFF
      for code running in RAM logged nothing on either build, and its positive
      control (the same watch on $C000-$CFFF) fired 3,772,896 times.
      (3) **Identical up to the game's own loader**: CURLIN runs 140 -> ... -> 265 ->
      10 on the same 0.25 s samples (line 10 at T57.75 on both); the tape-call log
      (TAPION / TAPIN, callers, CF, LOWLIM) is identical to T36.75. 🔴 That log
      then goes BLIND on both builds (nothing after T36.75, where the game's loads
      are) -- the return-address breakpoints break; fix before reading it.
      (4) **Then the block cadence shifts**: the game's loader alternates C-BIOS
      tape reading ($0A00-$0BFF) and a zerobas page-1 step ($6A9x) every ~2.75 s,
      first at T64.25 (good) vs T65.75 (bad). The earliest RAM differences (T60)
      are single bytes in the loader's stack ($C0BF / $C0C3 / $C0C9 / $C0DB /
      $C0DF) differing in bits 5 / 3 / 6 -- F of a pushed AF.
      (5) **The bad build goes off the rails when the game starts** (SP -> $FFxx,
      ~T100): the game hooks H.KEYI to a different target (good $D422 then $D5BD,
      bad $C6FB), and zerobas's H.TIMI service (htimi_guard) runs 2442 times in
      T95-150 on the good build against 10 on the bad, whose PC sits in $FCE0-$FD69.
      (6) The VG-8020 enters the game's line 10 at T54.50 and line 3341 at T140.25
      (zerobas, good: T57.75 / T143.00).
      🧭 **READING**: the class TODO.md already names for Punch & Judy (D-TAPLEAD) --
      the game leaves the motor running while BASIC works, so WHERE on the tape its
      own loader starts listening depends on BASIC's speed, and every speed change
      (batches 4-6 made the math 1.5-3x faster) moves it. The good build is on the
      right side of a margin, not correct by construction. ➡️ NEXT: repair the
      tape-call log (one-shot breakpoints on TAPION's return only, plus openMSX's
      cassette position at each TAPION) and run it on BOTH machines -- whether
      zerobas's TAPION locks on a block the VG-8020's would skip, or the game's
      loader asks at a different tape position, is the split.
      📏 **SECOND MEASUREMENTS (2026-10-31, the cassette position instead of the call log:
      [`bd2_probe.py`](../../scratchpad/bd2_probe.py) `--plain` samples openMSX's own `cassetteplayer
      getpos` -- emulator state -- with PC / SP / CURLIN every 0.25 s; `tapepos A B` compares
      two runs, [`bd2_tapepos.out`](../../scratchpad/bd2_tapepos.out),
      [`bd2_tapepos_bad.out`](../../scratchpad/bd2_tapepos_bad.out)):**
      (7) **The game's own loader starts at the SAME tape position on both machines**:
      first PC in RAM with SP >= $FF00 at tape 88.5749 s on the VG-8020 (T99.00) and on
      zerobas (T101.75) -- it waits for its own header, which re-aligns them.
      (8) **zerobas spends ~3 s longer in BASIC between tape blocks with the motor OFF**
      (the tape stands at 38.386 s for ~4 s on zerobas, ~1 s on the VG-8020; lines
      110 / 265 / 290 / 310) -- speed (tier 5), harmless there.
      (9) **Line 265 and then line 10 run with the motor ON** (tape advancing 1 s/s from
      ~39 s to 88.6 s): there BASIC's speed sets the offset between the program and the
      tape. HEAD + batch 6's fp_trunc sits a constant 4.3 ms of tape behind HEAD from
      line 265 on.
      (10) 🔴 **On TODAY's HEAD (after batch 7) that same fp_trunc build runs the game**:
      line 3341 at T147, as HEAD (it hung on batch 6's base). The margin is a few
      milliseconds of tape in the motor-on phase, and its side moves with every low-region
      change: fp_trunc (24 B) is applicable again today and could tip again tomorrow.
      ➡️ **NEXT**: the margin itself -- how many ms of offset in the line-265 / line-10
      phase the game tolerates, and where the VG-8020 sits inside it (its tape position at
      the line 265 -> 10 entry against ours). A faithful fix is the reference's timing in
      that phase (tier 5 speed work, paused); until then, run Boulder Dash II on every
      low-region change (the tape corpus does) and treat a hang there as this item, not
      as a wrong value.
      📏 **facdemo3.di2 WAS FILED HERE (2026-11-13) AND IS NOT THIS CLASS** -- withdrawn the
      same day: its line 15 loops over **PEEK(&HFB21)** (the only PEEK it makes there,
      [`facusr_run7.out`](../../scratchpad/facusr_run7.out)), and DRVINF read **3 on zerobas, 2 on the CF-3300** ([`facusr_run8.out`](../../scratchpad/facusr_run8.out)).
      The 8-byte usr.asm shift only changed HOW the extra drive went wrong; FILES-SAME before
      was agreement for the wrong reason. Fixed as D-DRVCOUNT (below the D-DISKRUN corpus note).
      📏 2026-11-25, A SECOND TITLE OF THE CLASS, WITH A WINDOW: CHUCKIE EGG resets when the main ROM's code between
      ex_for ($6289) and the $6CF3 pin moves by 3 bytes (D-FORFRAME's first fix; three NOPs at the same spot did the
      same, so it is the layout, not the code; tape corpus RUNS? 6293 -> RESET 8918, scratchpad/AE_chuckie_layout.out). Its
      machine code depends on an address in that stretch -- a BASIC ROM entry the reference has there and zerobas
      matches only by position. Next: log the page-1 addresses its RAM code calls (zerobas's own PCs) and pin the one
      inside $6289-$6CF3, as D-BASICINT2 pinned Demonia's $72D4.
      📏 2026-11-25, CHUCKIE EGG NARROWED TO ONE ADDRESS: $68C3. A layout bisection (scratchpad/chuckie_bisect.py ->
      AE_chuckie_bisect.out: three NOPs before a code label, rebuild, run the tape; 8 rounds over $6289-$6BCC) put the
      dependence in [$68AD caw_id, $68C5 cas_ascii_finish); breakpoints on those 24 bytes during the tape run hit ONCE:
      zerobas executes $68C3 at t=58.0 s (top of stack $0001 -- reached by a jump, not a call; HL $0023, A 0). On zerobas
      $68C3 is the LAST byte of `ld (CAS_WCNT),a` (`32 39 F7`): entered there it runs as RST 30h (CALLF) with the
      following bytes as slot / address -- harmless in this layout by accident, a reset when shifted. So the game jumps
      to an MS-BASIC entry at $68C3 that zerobas does not provide; it "runs" only by luck. ➡️ NEXT (black box): on the
      VG-8020, find where the game's RAM code jumps from (RAM breakpoints, the game's own code) and what entering $68C3
      does there -- registers / RAM / the screen before and after, never the reference ROM's bytes -- then give zerobas
      that routine at $68C3 and pin it (as D-BASICINT2 pinned Demonia's $72D4). The window sits in basic/save.asm's
      cassette ASCII-header writer, so the pin needs its own placement there.
