- [ ] 🐌 **D-LOOPPROF — WHERE A PLAIN STATEMENT'S TIME GOES: FIVE MEASURED LEVERS (filed
      2026-10-20 from a host profile)**
      🎚️ TIER 5 — on-par speed: the `%` FOR loop, 84 ticks against 73 over 3000 passes on 2026-11-14 (the rest is faster than the VG-8020).
      🤖 **AUTONOMOUS** — each lever is a slice; results must stay byte-identical.
      📏 **RE-MEASURED 2026-11-06 ON BOTH MACHINES** ([`loops4_time.out`](../../scratchpad/loops4_time.out),
      the four cases x300 in TIME ticks, VG-8020 / zerobas): `A=I+7` **70 / 72**, `A=I*7`
      **98 / 78** (faster here), the empty `%` loop **7 / 19**, the default empty loop
      **24 / 24**. D-TRAPCOST's rounds (2026-11-05/06) did most of it. What is left is the `%`
      NEXT: ~3370 T a pass against ~1500, spread thin -- the 25-byte frame copy (~525 T),
      the loop variable looked up by name every NEXT (~240 T), the statement loop.
      ✅ **THE FRAME COPY (2026-11-06):** nx_have (basic/program.asm) checks the limit and step
      types IN the frame and, both int16, copies only the 13 bytes nx_fast / nx_again read; a
      bail re-copies all 25 (nx_fslow). Model `%` loop 3367 -> 3159 T/pass (🔮 ~-200 -> -208
      HIT, the default loop the same -208); machine 19 -> 18 ticks, the others 71 / 77 / 24
      ([`loops4_time2.out`](../../scratchpad/loops4_time2.out)). tests/test_forint.py,
      test_forfast.py green. ➡️ NEXT: the variable's by-name lookup each NEXT.
      ✅ **THE RUN-LOOP ROUND TRIP (2026-11-06):** a continuing NEXT re-enters exec_stmt
      directly (nx_again, basic/program.asm), as a handler does at a statement's end, instead
      of returning through rp_lp / rp_exec / `call exec` -- the Ctrl-STOP poll (and the STOP
      shadow) still sends it the old road, and CURLIN is published for the FOR's line. Model
      `%` loop 3159 -> 2826 T/pass; machine ([`loops4_time3.out`](../../scratchpad/loops4_time3.out)) `%` 18 -> 16, default
      24 -> 22 -- 🔴 AND THE FULL BATTERY WENT RED TWICE ON IT: (1) S3_editclear -- a NEXT TYPED at
      the prompt continues a PROGRAM's loop, so DIRECTF must be re-derived (derive_directf, not
      curlin_pub); (2) C3_euler / C6_wordsort -- 372 frame-interrupt gaps up to 94 ms, PC in
      ctl_reloc ([`nxdirect_gap_c3.out`](../../scratchpad/nxdirect_gap_c3.out), asavedi_pc_probe.py gained --min=): rp_lp's stack
      RE-BASE (D-SPMERGE step 4) is what reclaims a freed inner FOR / GOSUB frame, and skipping it
      made every inner FOR relocate the stack under DI. The re-entry now re-bases too (the live
      block is checked to be exactly [loop return][SAVSTK anchor]; anything else takes the old
      road). The honest figures after both: model `%` 3045 T/pass; machine
      ([`loops4_time4.out`](../../scratchpad/loops4_time4.out)) 71 / 78 / **`%` 18 -> 17** / default **24 -> 23** (🔮 ~17 HIT); C3 /
      C6 SAME with 0 gaps, S3 SAME ([`nxdirect_c3c6.out`](../../scratchpad/nxdirect_c3c6.out), [`nxdirect_s3.out`](../../scratchpad/nxdirect_s3.out)).
      tests/test_forfast / forint / control_flow / statements / traps green.
      ✅ **D-NXCACHE (2026-11-07): NEXT no longer looks its variable up.** ex_for (live copy
      basic/fat.asm under BASICINT_PINS; program.asm's ELSE copy the same) keeps the loop
      variable's ENTRY and, for an int16 limit, stores it in the limit slot's spare bytes
      (FOR_LIM+3..+4); nx_have's fast copy takes those 2 bytes too (13 -> 15) and nx_fast
      reads the entry instead of calling var_find_typed. Safe for the frame's life: a new
      scalar is inserted at ARYTAB and only the arrays shift (sub/arrays.asm scv_alloc), and
      CLEAR / RUN / NEW / a typed line drop every frame. Page 1 285 -> 290 B (the dropped
      call), the low region's pinned hole took ex_for's +12. 🔴 The first build edited only
      the ELSE copy: tests/test_forint.py's "int path taken" rows caught it (every NEXT bailed
      to nx_fslow, the cache read 0). Model ([`loopprof_host.py`](../../scratchpad/loopprof_host.py) c) 3045 -> 2798 T/pass;
      **machine ([`loops4_time5.out`](../../scratchpad/loops4_time5.out), twice): 71 / 78 / 17 / 23 -> 69 / 75 / 13 / 21** (VG-8020 70 /
      98 / 7 / 24) -- 🔮 predicted `%` 16: MISSED, it is 13 (the machine's lookup costs more
      than the host model charges). tests/test_forfast / forint / control_flow / statements
      green.
      ✅ **D-NXINPLACE (2026-11-08): a `%` NEXT steps IN THE FRAME -- `%` 12 -> 10 ticks.** Profile
      first ([`loopprof_1108.out`](../../scratchpad/loopprof_1108.out), `%` loop 2611 T/pass): nx_have 497 (the 15-byte copy into
      FOR_CUR), exec_stmt 416, nx_again 387, then nx_fast / nx_fint / nx_fadd / nx_fput / nx_fcmp
      / cmp16_bits / set_factyp2 ~450 between them. `nxi` (basic/program.asm, entered from
      nx_have when limit and step are int16 and the D-NXCACHE entry is type 2) adds the step to
      the variable in place (an int16 overflow falls back to nx_fullcopy, which raises what it
      always did), tests the end signed by flipping both sign bits, sets FACTYP = 2 as
      combine_cmp leaves it, and copies only FOR_LINE / FOR_BODY for nx_again. FOR_CUR is
      statement-exclusive scratch (BUFTX), so not filling it strands no reader. Host model
      ([`loopprof_nxi.out`](../../scratchpad/loopprof_nxi.out)) 2611 -> 2315 T/pass (🔮 ~2200: MISSED, nxi's own test costs ~170 T);
      **machine ([`loops4_nxi.out`](../../scratchpad/loops4_nxi.out)) 66 / 73 / 12 / 20 -> 65 / 72 / 10 / 20** (VG-8020 69 / 97 / 7 /
      24; 🔮 `%` 10: HIT). 💰 Page 1 151 -> 36 B free. tests/test_forfast.py counts `nxi_take`
      as the int path (and `nxi_ovf` as a bail) and steers `nxi` like nx_fast; forint /
      forfast / control_flow / statements / traps green. ➡️ What is left of the `%` pass:
      exec_stmt + es_idx (~550 T, the statement dispatch) and nx_again (~390: BREAKX, the STOP
      shadow, the SAVSTK re-base checks).
      📏 **RE-PROFILED 2026-11-11 ([`loopprof_1111.out`](../../scratchpad/loopprof_1111.out), machine model):**
      `A=I+7` 12.2k T a pass (VG ≈ 14.7k), `A=I*7` 14.2k (≈ 20.6k), the default empty loop
      3.7k (≈ 5.0k) -- all three now FASTER than the VG-8020; only the empty `%` loop
      lags, 2.4k (≈ 1.7k, 10 ticks against 7). Its pass: exec_stmt 416 + es_idx 138 (the
      dispatch every statement pays), nx_again 387 (BREAKX, the STOP shadow, the SAVSTK
      re-base -- each one needed), nxi ~620. Looked at and NOT taken: inlining exec_stmt's
      `call check_fperr_only` (27 T a statement; cee_abort_fp discards its caller's return
      address, so it cannot be a plain `jp`); Route D's 18 `jp` -> `jr` (a taken `jr` is 2 T
      SLOWER, on hot loops such as PRINT's exp_loop -- a speed tier must not pay for room
      that way, and page 1's pin pads hold ~1.7 KB anyway). ➡️ The remaining `%` gap
      (~700 T) needs a design, not a peephole: a lighter dispatch for the statement after a
      NEXT that loops back (the body's first statement), measured on a NON-empty body so it
      is not a benchmark special case.
      The D-CONCATLIT round-2 design (a combined first-append op) was weighed the same day
      and deferred: ~6 %, and the snapshot is load-bearing for array elements / RVDESC.
      📏 [`loopprof_host.py`](../../scratchpad/loopprof_host.py) →
      [`loopprof_host.out`](../../scratchpad/loopprof_host.out): per-routine T on the host Z80
      plus the costs the host skips (1063 T a sub-ROM crossing: `subrom_call` 152 +
      C-BIOS's CALSLT into expanded 3-2 911; BREAKX ~85) models the machine to ±3 %
      (`A=I+7` 139 modelled vs 137 measured; `I%` 40 vs 39; default 31 vs 32). Per pass:
      `A=I+7` 29.1k T (VG ≈ 14.7k), `A=I*7` 38.0k (≈ 20.6k), the `%` NEXT loop 8.4k
      (≈ 1.7k), the default fast NEXT loop 6.6k (≈ 5.0k).
      Levers, ranked (machine T a pass):
      1. **an exact-int fast path for float `+ − *`** (both operands exact int16 -> the
         int16 path, the result packed as the BCD path would; overflow falls back): ~6600
         in `A=I+7` (23 %), ~14 900 in `A=I*7` (39 %). Costs ~35-45 B (estimated 2026-10-20), LOW region, hooked in
         `combine_*` -- `fp_add` / `fp_mul` / `flt_to_int16` / `arga_pack_fac` are
         resident-ABI roots and run with page 1 switched out.
         ✅ **BUILT 2026-10-20 (D-INTFAST):** `caddsub_float` / `cmul_float` first ask
         `fx_cvt` whether both operands are exact int16 (`nx_pki` on a float operand);
         if so the existing int path computes, and an in-range answer is packed by
         `nx_pack` and finished through the BCD path's own tail (`fac_dbl_int16`), so
         FACTYP, DE and every register come from the same `flt_to_int16` over the same
         FAC; an overflow runs today's float path. Paid for in part by carves
         (`caddsub_widen_both` gone, redundant pushes / `or a` / a dead store): low
         region 49 → 6 B free on 2026-10-20 (+43 net), page 1 unchanged. Drafted by a
         subagent, measured here. `tests/test_intfast.py` (new): 160 116 leaf calls (every
         type pairing at the int16 walls, products / sums across them, fractions, rhs
         `$8000`, pre-set FPERR; 120 000 random) and 425 programs, all identical to the
         old image. ON THE MACHINE ([`intfast_before.out`](../../scratchpad/intfast_before.out)
         → [`intfast_after.out`](../../scratchpad/intfast_after.out), ×300 ticks): `A=I+7`
         137 → 120 (VG 70), `A=I*7` 192 → 136 (98), `A=I-J` 210 → 198 (93); **slower:**
         `A=1.5+I` 135 → 142 (the exactness test) and an exact product that overflows
         int16, `A=I*4682`, 210 → 230. float / math / tmfp / intarg acceptance green.
         ⚠️ A NON-CANONICAL operand (a leading-zero mantissa or an A-F nibble -- only
         POKE or CVS / CVD of foreign bytes make one) is read as the integer its digits
         spell and the result packed canonically, where the BCD add could keep the odd
         form; D-FORFAST's NEXT has the same exposure. Same value, different bytes.
      2. **no CALSLT per scalar reference** (every lookup crosses into the sub-ROM's
         `scv_find`): ~1375 a reference -- a resident walk in main (~45-55 B, needs a
         carve), or for NEXT only the variable's entry address cached in the FOR frame's
         spare bytes (~15-20 B of page 1, estimated 2026-10-20).
      3. **an int16 arm in NEXT for `%` loops** -> D-FORINT below.
      4. **the fast NEXT's BCD round trip** (`nx_pki` + `nx_pack` ~1600 a pass): keep the
         int16 counter and the last-written packed bytes in the frame's spare bytes, a
         4-byte compare proves the body left the variable alone; ~1350, ~25-35 B of page 1 (estimated 2026-10-20).
      5. smaller: `nx_have` copies the whole 25 B frame (~400); `flt_to_int16` runs twice a
         pass in `A=I+7` producing a DE nobody reads (~1700 each); each name is walked
         twice (`var_str_type`, then `var_name_key`); a one-digit literal widens by a
         16-step `div10` + a 15-byte `zero_fill` (~1300).
      🔴 Harness trap found on the way: an unseeded `FN_FEND` makes every host scalar
      lookup walk a 256-byte page (~9000 T); tests/test_forfast.py's F4 now seeds it.
      ✅ **A SAME-LINE NEXT KEEPS DIRECTF / CURLIN (2026-11-07).** nx_again re-derived DIRECTF and
      re-published CURLIN every pass; when the loop's line is the line already running (a FOR
      and its NEXT on one line) both are that line's already, so derive_directf is skipped (C =
      CURLINE changed). Model `%` loop 2815 -> 2696, default 3693 -> 3574 T/pass
      ([`nxdd_prof.out`](../../scratchpad/nxdd_prof.out)); machine ([`loops4_time7.out`](../../scratchpad/loops4_time7.out)) **66 / 73 / 12 / 20** (from 67 / 75 / 13 / 21;
      VG-8020 69 / 97 / 7 / 24) -- 🔮 "the `%` loop stays 13": MISSED on the good side, every loop
      gained a tick. Page 1 took 12 B (2026-11-07). Looked at and DROPPED: skipping nx_have's
      15-byte frame copy when FOR_CUR already holds that frame -- FOR_CUR is BUFTX, a scratch
      buffer other statements write, so a cached "this frame" key could be clobbered into a
      false match.
      ✅ **D-SEPONCE (2026-11-14): A `:` IS ONE STATEMENT BOUNDARY, NOT TWO.** Every
      `stmt:stmt` ran exec_stmt's boundary work twice: the handler's `jp exec_stmt` landed
      on the `:` (PRDEST, the FPERR reader, TEMPPT, es_bound), the `:` dispatched to ex_sep,
      and ex_sep's `jp exec_stmt` ran all of it again for the next statement -- nothing
      executed in between, so only SAVTXT could differ. exec_stmt's `:` arm is es_sep now
      (basic/interp.asm): past the `:`, SAVTXT, back to the dispatch. es_trap (basic/traps.asm)
      had refused a `:` because the re-entry gave it a second chance; it fires AT the `:`
      now -- the handler's frame resumes there, and the `:` dispatches the same statement.
      Model (scratchpad/loopprof_host.py, [`LP_base.out`](../../scratchpad/LP_base.out) -> [`LP_after.out`](../../scratchpad/LP_after.out)): exactly
      **-183 T per `:`** in every case (🔮 ~180 HIT); the empty `%` loop 2382 -> 2199 T a
      pass. Machine ([`loops4_time8.out`](../../scratchpad/loops4_time8.out), x300 ticks, VG-8020 69 / 97 / 7 / 24): zerobas
      66 / 73 / 12 / 20 -> **64 / 70 / 10 / 19** (🔮 65 / 72 / 11 / 19: MISSED on the good
      side). The nine trap suites green (trapstmt, interval, stop, key, strig, sprite,
      error, trapdepth, trapsvc). Unit tests: test_stmt_dispatch names es_sep for `:`;
      the old-vs-new differentials (test_forfast / forint / intfast) collapse CONSECUTIVE
      IDENTICAL snapshots, which the old image took twice per `:`.
      ✅ **D-NXBARE (2026-11-14): a bare NEXT skips is_letter.** nx_head's RST 10 (CHRGTR)
      already returns Z exactly on 0 / `:` -- the terminator nx_notletter accepted after
      is_letter failed -- with A = that byte and NC, as its own tests left them; `jr
      z,nx_find` right after it (basic/program.asm, +2 B). Model ([`NB_after.out`](../../scratchpad/NB_after.out)): **-112 T
      a pass** in every case (🔮 ~90: HIT, bigger); empty `%` loop 2199 -> 2087. Machine
      ([`loops4_time9.out`](../../scratchpad/loops4_time9.out)): 64 / 70 / 10 / 19 -> **63 / 70 / 9 / 19** (VG-8020 69 / 97 / 7 / 24).
      Unit tests 97 / 97.
      ✅ **D-ESIDXAL (2026-11-14): THE KEYWORD DISPATCH WITHOUT A 16-BIT ADD -- 138 -> 101 T a statement.**
      stmt_table moved from interp.asm (where it sat at $4180, low byte $80) into the $72D4 pin's
      pad (basic/field.asm, at $7111): its rows never cross a page there (asserted: low byte
      + 174 <= 255), so es_idx forms the row as H = page, L = low + 2 x row -- no `ld d,0` / `add
      hl,de` / push-pop of the cursor; the out contract is unchanged to the register. A first
      cut 256-aligned it in the $6CF3 pad and paid ~124 B of alignment (2026-11-14); the low-byte form
      needs none. The 178 B it left fell in front of the $475A pin -- which the wall readout
      did not list (it does now: see the crt_rows item). Model ([`EA_after.out`](../../scratchpad/EA_after.out)): exactly
      **-37 T per keyword statement** (🔮 ~-37 HIT; case (e) -111 for GOSUB / NEXT / RETURN).
      Machine ([`loops4_time10.out`](../../scratchpad/loops4_time10.out), three identical runs): **63 / 70 / 10 / 18** -- the
      default loop gained a tick, the `%` loop LOST one (9 -> 10) although its pass is 37 T
      shorter: 300 passes are ~10 ticks, so the loop's start against the 50 Hz interrupt moves
      a reading by one when layout shifts (🔮 "% 9, default 18": MISSED by that tick).
      📏 **3000 PASSES (2026-11-14, `LOOPS4_N=3000 scratchpad/loops4_run.py`, [`loops4_n3000.out`](../../scratchpad/loops4_n3000.out)):** VG-8020
      715 / 986 / 73 / 240, zerobas 684 / 779 / **88** / 199 -- the reading without the tick:
      every loop but the empty `%` one is FASTER than the VG-8020; that one 1.21x.
      ✅ **D-ESINLINE (2026-11-14): exec_stmt's three per-statement calls inline.** The FPERR test
      (`ld a,(FPERR) / or a / call nz,check_fperr_only` -- the same call when a code is
      pending, so its abort discards the same return word), es_bound's latch / trap tests (each
      handler still reached by a `call` from exec_stmt, so es_latch's break path and es_trap see
      the depth es_bound's `jp` gave them; a latch still skips that boundary's trap test, es_bl)
      and skipsp_test (`call skip_spaces / or a`). es_bound is gone from program.asm. Room: the
      $475A pad D-ESIDXAL opened, 188 -> 168 B; page 1's tail 32 -> 47 (2026-11-14). Model
      ([`EI_after.out`](../../scratchpad/EI_after.out)): **-106 T a pass** in the empty loops (one full statement + the `:`'s
      dispatch), -212 in `A=I+7` (🔮 ~1900 for (c): MISSED, 1944 -- the `:` path counted twice).
      Trap / error suites (trapstmt, interval, stop, key, strig, sprite, error-trap, trapdepth,
      trapsvc, error) green; unit tests 97 / 97. Machine, 3000 passes ([`loops4_n3000b.out`](../../scratchpad/loops4_n3000b.out)):
      zerobas **675 / 769 / 84 / 195** (🔮 `%` ~85: HIT) -- the `%` loop 1.15x the VG-8020's 73.
      ✅ **D-NXLATCH (2026-11-14): nx_again's INTFLG test is gone.** It sent a latched STOP /
      CTRL-STOP down the old road to rp_exec; since D-BRKLATCH step 2 exec_stmt reads the latch
      at every boundary itself, and nx_again enters exec_stmt at the body's first statement --
      the same boundary. Model ([`NL_after.out`](../../scratchpad/NL_after.out)): **-27 T a pass** in every case (🔮 HIT);
      stop-trap / direct-ctrl / iscntc / interval-trap / trapstmt acceptance and unit tests green.
      ➡️ The `%` loop's rest (~1917 T against ~1530): nx_again's re-base checks (~330 T), the
      int16 step (~620), the dispatch of NEXT (~550).
      🏗️ **JOOST (2026-11-14): *"investigate what the references do ?"*** -- before a frame redesign,
      black-box the references' FOR frame: the stack RAM a `FOR I%=1 TO N` pushes (size,
      what it holds: the variable's address? the limit / step pre-converted?), read through
      the debugger on the VG-8020 (and the CF-3300), RAM only -- never a ROM byte.
      📏 **READ (2026-11-14, [`forframe_probe.py`](../../scratchpad/forframe_probe.py) -> [`forframe_run1.out`](../../scratchpad/forframe_run1.out); the CF-3300's run did not reach
      its prompt by typed keys at 8 or 25 s -- unread, [`forframe_run2.out`](../../scratchpad/forframe_run2.out)):** the VG-8020's
      `FOR I%=1 TO 32000` frame, just below STKTOP $F0A0, stable across two samples: the FOR
      token ($82), **a POINTER to I%'s value** ($8019; I%'s entry is at VARTAB $8016), a step-
      sign byte, 10 bytes of $9F $00 (room the int loop leaves unused -- float limit / step
      slots, by its size), the body's text pointer, **step 1 and limit 32000 as plain int16**,
      line 10, the text pointer again. **So the reference's int frame keeps what ours keeps**
      (D-NXCACHE's cached entry, int16 limit / step): the frame LAYOUT is not where its 1.15x
      comes from -- it is the per-pass path (nx_again's checks ~330 T, the int16 step ~620,
      NEXT's dispatch ~550, against ~1530 for the whole VG-8020 pass). ➡️ Shorten that path
      rather than redesign the frame: e.g. NEXT's step without the cached-entry re-fetch and
      re-bias (nxi_take ~350 T for an add / store / signed compare).
