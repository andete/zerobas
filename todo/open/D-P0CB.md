- [ ] 🧱 **D-P0CB — COLD STATEMENTS OUT OF MAIN INTO zerobas-sub2 PAGE 0, THROUGH A
      PAGE-0 CALL-BACK (Joost 2026-10-21: "Yes, but no new RAM")**
      🎚️ BUDGET — ROM size toward the reference; the space every later tier spends.
      🤖 **AUTONOMOUS** — spec [`spec-sub2-p0cb.md`](docs/spec-sub2-p0cb.md). A
      read-only study (2026-10-21) found no statement could move to sub2 page 0 under
      the old rules: every parser uses `rst $10`, and raise / eval / print reach main's
      page 0, which a page-0 tenant switches out. The mechanism is the BIOS's own RAM
      CLPRIM ($F38C), so no new RAM; main pays ~12 B once (`ex_sub2`), then ~4 KB of
      cold statements can follow (E): trap statements ~300 B, the file family
      ~1.4-1.6 KB, SCREEN / COLOR / WIDTH / KEY ~450 B, graphics after a stopwatch.
      ✅ **SLICE A DONE 2026-10-21 (0 B of main):** `p0cb` (sub2/p0cb.asm, 7 B: AF to
      AF', push the live $A8, clear page 0's field, `jp CLPRIM` -- whose `ret` lands in
      the caller), sub2's RST 10h / RST 18h -> main's CHRGTR / OUTDO through it (IX
      saved), and `p0cb_selftest` at page-0 index 2. Imports are a new p0cb class in
      `tools/gen_resident_abi.py`, aliased `p0_*` (the file is shared with zerobas-sub,
      which has its own skip_spaces); `check_tenant_closure.py`'s seed scan stops at
      their header; `check_dead_code.py` follows an alias to the main label.
      `make sub2-acceptance` runs [`basic_probe_sub2_p0cb.py`](probes/basic/basic_probe_sub2_p0cb.py)
      after the ping: 15/15 PASS on BOTH repack machines
      ([`p0cb_run.out`](scratchpad/p0cb_run.out)) -- RST 10h to CHRGTR, A / F (carry) /
      BC / DE / HL through a round trip, a page-1 routine, IX kept, EI inside the 3-3
      page-0 tenant with JIFFY moving and the tenant coming back (D-SUB2EI's twin).
      🔪 K-P1 (page 0 never switched): the CHRGTR rows go red, the page-1 rows stay
      green ([`p0cb_knife_p1.out`](scratchpad/p0cb_knife_p1.out)); K-P2 (`s2_chrgtr`
      does not restore IX): exactly W+12 red, `$60` = CHRGTR's low byte
      ([`p0cb_knife_p2.out`](scratchpad/p0cb_knife_p2.out)); sub2.rom hashed 373d8bd1 ->
      4ea9f489 / d069b234 -> 373d8bd1. 🔮 "15/15 on both" HIT, both knives HIT.
      🔴 The IX row read `$00` once: `sub2/p0cb.asm` was missing from the Makefile's
      SUB2_PARTS, so sub2.rom was NOT rebuilt and the probe ran the previous image --
      an inert build, caught because the new row's value was impossible. Fixed.
      ✅ **SLICE B DONE 2026-10-21: THE EVENT-TRAP STATEMENTS LEFT MAIN.** ON STOP /
      SPRITE / STRIG / KEY / INTERVAL GOSUB, INTERVAL ON|OFF|STOP, STRIG(n) and KEY(n)
      ON|OFF|STOP are sub2/trapstmt.asm's (`trap_tenant`, page-0 index 3); main keeps
      a 4 B stub per entry (`ld c,TT_* / jr ex_sub2`, each label kept for ex_on /
      ex_ff_stmt / screen.asm) and `ex_sub2` (12 B: subrom2_call, then `push de /
      ret` to the continuation the tenant returns). Every main routine the arms use is
      a p0cb call (18 `p0_*` imports); a raise through p0cb never returns, as the `jp
      nz,trap_syntax` it replaces did not; a `jp pop_exec` became the tenant popping
      its own cursor and returning exec_stmt -- no main continuation is ever reached
      through p0cb. STRIG(n) / KEY(n)'s shared middle is one copy (`tt_entry_paren`).
      The trap machinery (check_traps, set_state, ztrap_entry, iv_match) stays.
      📏 Walls (2026-10-21): main page 1 tail 36 -> 291 B free (🔮 ~250: HIT); low and
      the pin pads unchanged; sub2 page 0 16084 -> 15619 B free.
      Witness: interval / key / sprite / stop / strig / trapdepth / trapsvc /
      error-trap and sub2 acceptance all green. 🔪 K-T1 (ON KEY's reversed band not
      reversed): key-trap-acceptance RED on exactly the positional rows --
      F_positional, H_shift_is_key6, AA_empty_slot_midlist, L_key4
      ([`traps_knife_t1.out`](scratchpad/traps_knife_t1.out)); sub2.rom 673b05a5 ->
      c5c6cbea -> 673b05a5. 🔮 HIT. Docs: STRIG.md, SPRITE.md, ON.md; examples PASS 3.
      ✅ **SLICE C1 DONE 2026-10-21: OPEN, CLOSE, MERGE, MAXFILES LEFT MAIN.** Drafted
      by a subagent in its own worktree (build + static checks only, no emulator),
      integrated and measured here. sub2/filestmt.asm's `file_tenant`, reached through
      trap_tenant's head (C >= 8 is a token) from ONE 1-byte main entry (`ld c,a` in
      front of ex_sub2: exec_stmt enters a handler with A = its token), so the four
      stmt_table rows cost 0 B each. Only OWNED code moved; everything shared or called
      back by disk.rom (fch_check, fname_expr, pdfcb_resume, fopen_cross,
      fch_do_close_ch, the cas_* routines, ...) stays in main and is reached through
      p0cb (47 `p0_*` imports in all). Continuations returned in DE: exec_stmt (HL =
      cursor), clr_wipe (MAXFILES), end_line_end (MERGE), disk_error / load_error (they
      print and RETURN when nothing is pending, so they are continuations, not
      raises). `oo_parse_reclen` stays (tests/test_open_len.py runs it on the main
      image); `fatprim_bounce` was deleted (its only caller discarded its outputs).
      📏 Walls (2026-10-21): main page 1 tail 291 -> 290 B, pads +797 B (319 B at
      $6CF3, 496 B at $72D4; no `jr` spans either); sub2 page 0 15619 -> 14526 B.
      Witness: unit tests 78/78; sub2 / stop-trap / key-trap / nodisk / opengrp /
      clearclose / badfnum / diskascii (MERGE) / casdirect / fcbhdr / nodiskopen /
      lptverb acceptance green; the new [`filestmt_probe.py`](scratchpad/filestmt_probe.py)
      against the CF-3300 with a disk copy per case, 29/29 SAME
      ([`filestmt_run.out`](scratchpad/filestmt_run.out)) -- `o.same` reads no output
      on BOTH sides (its MAXFILES=2 clears ON ERROR, so the 54 goes untrapped): no
      reading, not an agreement. 🔪 K-C1 (MAXFILES's ERR 5 bound gone): exactly `m.16`
      diverges; K-C2 (OPEN's wildcard refusal gone): exactly `o.wild`
      ([`filestmt_knife_c1.out`](scratchpad/filestmt_knife_c1.out),
      [`filestmt_knife_c2.out`](scratchpad/filestmt_knife_c2.out)); sub2.rom 399342fd
      -> c1829689 / d0a01523 -> 399342fd. 🔮 all HIT. kwknife: connectedness unchanged;
      LOC's KNIFED verdict moved DIVERGENT -> MISSING (its row opens a file first), still
      connected.
      ⚠️ RISK CARRIED: MERGE now runs the whole ASCII line reader (dispatch_line,
      store_line, the lineedit tenant) inside a p0cb'd call under the sub2 CALSLT --
      nested CALSLTs into 3-2 and disk.rom, possible EI, a deeper stack. diskascii /
      casdirect are green on it; a long or tape MERGE is where it would show.
      ✅ **SLICE C2 DONE 2026-10-21: SAVE, CSAVE, BSAVE, LOAD, CLOAD, BLOAD AND RUN
      "name" LEFT MAIN.** Drafted in a worktree (build + unit tests, no emulator),
      integrated here. sub2/loadsave.asm's `ls_tenant`, reached from file_tenant's
      tail; the six 4 B ex_* stubs in interp.asm are now labels on C1's shared `ld c,a`
      entry, and do_run's name arm does `ld c,RUN_TOKEN / jp ex_sub2`. Moved: the
      parse halves of do_bload / do_cload / do_load / do_run's name arm, and most of
      basic/save.asm (BSAVE / SAVE / SAVE ,A / CSAVE arms, csav_speed, tape_parse_name,
      bsave_opt4). STAYED, reached through p0cb: do_tape_prog (the TAPION / TAPIN loop
      is real-time -- one p0cb runs it whole), disk_prog_load (autoexec_run calls it),
      sv_tenant and a new bload_sub (their sub-ROM calls carry an INLINE index byte,
      which a p0cb caller cannot pass), load_handoff / lh_back and run_prog_top
      (continuations and pin targets), and the shared cas_* / list_all /
      load_commit_prog. Continuations in DE: exec_stmt, disk_error, end_line_end,
      run_prog_top, load_handoff, and bp_ret for the handler's own `ret`. One hook
      call converted: SAVE ,A's `call H_CHCLOSE` -> p0cb.
      📏 Walls (2026-10-21): main page 1 pads +776 B ($6CF3 319 -> 1095 B), tail 290 B;
      low region tail 6 -> 11 B; sub2 page 0 14526 -> 13440 B.
      Witness: loaddi-acceptance 7/7 -- 🔮 "red: the tenant runs under DI" MISSED, the
      disk paths re-enable interrupts themselves (cg_back, disk.rom); then the FULL
      battery. 🔪 K-LS1 (LOAD ,R never runs): runtail-acceptance RED on exactly
      `loadr-hit` (`<nothing>` against the CF-3300's ZQ9), `load-plain` and its
      listing control green ([`p0cbc2_knife_ls1.out`](scratchpad/p0cbc2_knife_ls1.out));
      sub2.rom 4ac6f2e3 -> 57091d44 -> 4ac6f2e3. 🔮 HIT.
      ⚠️ RISKS CARRIED: the tenant enters under sr_slot's DI, so main-side work an ASCII
      LOAD / SAVE ,A does between crossings runs masked until something re-enables
      (loaddi is green, but it pins DISK verbs; a long ASCII TAPE load is the case to
      watch); a deeper stack (as MERGE, C1); RUN "file" now needs zerobas-sub2.
      ➡️ NEXT: slice D (SCREEN / COLOR / WIDTH / KEY), and the tape loop (~230 B more)
      only after a TAPIN timing study.
      ✅ **SLICE D DONE 2026-10-24: SCREEN, COLOR, WIDTH AND KEY LEFT MAIN.** Drafted by a
      subagent in its own worktree (build, host tests and static checks only), integrated and
      measured here. sub2/scrstmt.asm's `scr_tenant`, reached from ls_tenant's tail; the four
      stmt_table labels sit on C1's shared `ld c,a` byte (0 B). Moved: ex_screen / scr_extra,
      ex_color and its helpers (clr_eval / clr_prep / clr_commit from the LOW region),
      ex_width, ex_key and its arms, and SCREEN's sprite-argument helpers from graphics.asm.
      STAYED: ex_cls / cls_keyline, key_repaint (CLS and the prompt share it), spr_tenant
      (the sprite statements), and a new `key_op` label on key_repaint's tail (0 B); one new
      main routine, `key_drain` (11 B), the continuation for KEY LIST / KEY n,"text" so their
      print loop runs in main, off sub2's frame (D-BLOADSTK's lesson). Six `p0_*` imports.
      📏 Walls (2026-10-24): main low region 8 -> 41 B free, the $6CF3 pad 893 -> 1274 B,
      page-1 tail 287 -> 291 B (418 B of main); sub2 page 0 13476 -> 12940 B. Host tests 87/87;
      tests/msxtest.py bridges subrom2_call into sub2 when a test seeds SUBSLOT2.
      📏 screenerr-acceptance 76/76 agree on slice D ([`scrbaud_knife_base.out`](scratchpad/scrbaud_knife_base.out));
      🔪 the D-SCRBAUD knives, re-pointed at sub2/scrstmt.asm (their old target had moved --
      an inert knife until then): K-SB1..4 each reach sub2.rom and move exactly their rows,
      restore BYTE-IDENTICAL ([`slicED_scrbaud_knives.out`](scratchpad/slicED_scrbaud_knives.out)).
      📏 **THE TAPIN TIMING STUDY (2026-10-24), the tape loop's precondition:**
      [`tapin_margin.py`](scratchpad/tapin_margin.py) CLOADs a 40-line tokenised program
      from a CSAVE-shaped .cas on zerobas diskless and RUNs it; [`tapin_margin_knives.py`](scratchpad/tapin_margin_knives.py)
      plants N `djnz` passes (13 T each, + 21 T) at the top of ctp_body -- once per program
      byte -- each build ROM-hashed, the restore BYTE-IDENTICAL. Baseline OK; **96 passes
      (~1270 T) OK, 128 (~1680 T) BROKEN**, and 255 / 510 / 1020 broken
      ([`tapin_margin_run.out`](scratchpad/tapin_margin_run.out), [`tapin_margin_run2.out`](scratchpad/tapin_margin_run2.out)).
      So the loop has ~1300-1700 T of slack per byte at openMSX's .cas playback rate. Moved
      into sub2 it would pay a p0cb round trip (~150 T, counted from sub2/p0cb.asm + CLPRIM)
      for TAPIN and another for cas_put: ~300 T, about a fifth of the slack. 🔮 "OK up to
      ~6600 T, the two stop bits" MISSED -- the margin is a quarter of that.
      📏 **AND ON A REAL 2400-BAUD TAPE (2026-10-24):** the VG-8020 itself wrote it
      ([`tapin_wav2400.py`](scratchpad/tapin_wav2400.py): CLOAD the .cas, then `CSAVE"PROG",2`
      into a fresh recording; cas_decode reads 4822 Hz short half-periods = 2400 baud, 1297
      bytes, the program). zerobas CLOADs it with 0 / 32 / 48 / 64 / 96 / 112 / 128 / 160
      passes -- ALL OK ([`tapin_margin_run3.out`](scratchpad/tapin_margin_run3.out),
      [`tapin_margin_run4.out`](scratchpad/tapin_margin_run4.out)); a copy cut to 60 % reads
      `Device I/O error`, so the WAV is what plays. 🔮 "the slack halves at 2400" MISSED: the
      reference-written 2400-baud tape is MORE tolerant (>= ~2100 T) than openMSX's .cas
      playback (~1300-1700 T), which is the worst case measured.
      ✅ **THE TAPE LOOP MOVED 2026-10-24 (drafted in a subagent's worktree, integrated and
      measured here).** sub2/tapeprog.asm: do_tape_prog's header dispatch, the ctp_* read
      loop and its error shims, the end of the read, cas_put, verify_error and the tok_payload
      include (none has another caller); sub2/loadsave.asm calls it directly. STAYED in main,
      through p0cb: TAPION / TAPIN / TAPIOF (BIOS), cas_open_match (OPEN / MERGE use it),
      cas_ascii_load, load_commit_prog and the dpl_* tails (shared with the disk LOAD),
      print_msg / err_verify. ONE p0cb per program byte (TAPIN): +136 T per byte (256 -> 392 T,
      counted); the loop runs at the same stack depth (TAPIN entered at S-24 before and after).
      📏 Walls (2026-10-24): the $6CF3 pad 1274 -> 1591 B (317 B of main), sub2 page 0
      12940 -> 12573 B; host tests 87/87 (test_loadbase enters sub2's ctp_begin through the
      sub2 bridge; a planted fault turned its four CLOAD rows red). 📏 Margin after the move
      ([`tapin_margin_postmove.out`](scratchpad/tapin_margin_postmove.out)): base OK, d64 (~850 T
      more) OK, d255 BROKEN -- as before the move; 🔮 "d64 still OK" HIT.
      📼 The tape collection after it ([`tapecorpus_tapeloop.out`](scratchpad/tapecorpus_tapeloop.out)):
      SAME 9, NEAR 12, RUNS? 21, RESET 0 -- all 42 titles in their previous class.
      ✅ **SLICE E DONE 2026-10-24: DELETE, RENUM AND AUTO'S HEAD LEFT MAIN** (drafted in a
      subagent's worktree, integrated and measured here). sub2/pgmedit.asm's `pe_tenant`,
      reached from scr_tenant's tail; the three stmt_table labels on the shared `ld c,a`
      byte. The engines were already the sub ROM's lineedit tenant -- only the statement
      heads moved, so 88 B of main (page-1 tail 291 -> 361, the $72D4 pad 496 -> 514; sub2
      page 0 12573 -> 12439 B, 2026-10-24). AUTO's modal loop exa_loop STAYS in main (it waits
      on the keyboard per line -- D-BLOADSTK's rule), returned as a continuation, at the
      statement's own SP; DELETE / RENUM run 18 B deeper. Host tests 87/87 with four new
      test_statements rows; planted faults K1-K3 turned exactly those rows red.
      📏 editverb-acceptance 61/61 across the VG-8020, the CF-3300 and zerobas
      ([`sliceE_editverb.out`](scratchpad/sliceE_editverb.out)); the tape collection unchanged,
      42 titles ([`tapecorpus_sliceE.out`](scratchpad/tapecorpus_sliceE.out)). The FULL
      battery's one red was tools/dupspan_indep.py's selftest: gp_raise's span ran on into the
      $72D4 pad once ex_delete left -- the tool now accepts the `jp raise_error` followed by
      pad bytes only (its teeth kept: real code after it still fails).
      ✅ **STUDY CONCLUSION: the move is timing-safe** -- ~300 T of p0cb against >= ~1270 T
      of slack on the worst tape measured, 4x headroom. ➡️ NEXT: move the tape loop
      (do_tape_prog's ctp_* body, ~230 B) into the sub2 tenant, TAPIN / cas_put through p0cb;
      witness: the tape gates, the tape collection, and tapin_margin.py's d64 row (~850 T
      more on top of the move) as the margin check after it.
      ⏱ THE SPEED COST, measured by the FULL battery's kwtime (2026-10-24, T5 is paused --
      Joost 10-20: ROM space first, "it'll also have speed impact"): COLOR's border form 2x ->
      2.8x the reference's time, KEY's display-on 3.1x -> 3.4x, WIDTH 0.8x -> 0.81x, SCREEN
      unchanged (docs/tier-status.md). A game that runs COLOR every frame pays it.
      📼 The tape collection on slice D ([`tapecorpus_sliceD.out`](scratchpad/tapecorpus_sliceD.out)):
      SAME 9, NEAR 12, RUNS? 21, RESET 0 -- all 42 titles in the class they had before it.
      ⚠️ RISK CARRIED: these statements now run 18-22 B deeper (one CALSLT + p0cb frames), the
      D-BLOADSTK class for a no-CLEAR loader that then runs SCREEN / COLOR / WIDTH / KEY; and the
      tenant enters under sr_slot's DI (C-BIOS's VDP routines re-enable).
