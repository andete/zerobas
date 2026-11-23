- [ ] ⌨️ **D-SESSIONS -- TYPED SESSIONS AS INTEGRATION TESTS: THE PROMPT, NOT A LOADED PROGRAM
      (started 2026-11-06; Joost: *"Having typed sessions as integration tests is actually a
      splendid idea."*)**
      🎚️ TIER 1 — happy path: what a user does AT THE PROMPT (typing lines in, AUTO, RENUM,
      DELETE, LIST, retyping a line, STOP / CONT, NEW, MERGE) was never exercised end to end:
      the ladder loads a finished program from tape. 20 of 161 keywords appear in no ladder
      program (2026-11-06, a substring scan): AUTO CONT DELETE LLIST MERGE NEW RENUM ... and
      the tape / sector / device verbs.
      🤖 **AUTONOMOUS** — the reference settles each step.
      ✅ **THE RUNNER (2026-11-06):** [`run_sessions.py`](probes/programs/run_sessions.py), gate
      `sessions-acceptance` (Makefile, run_gates, pick_gates P16d: a changed `.ses` plans it).
      A session `probes/sessions/S<n>_*.ses` is typed one line at a time on an IDLE machine
      (keyboard buffer empty, CURLIN steady 0.7 s), `{STOP}` / `{CTRLC}` / `{WAIT n}`; the text
      screen is snapshotted after every step and compared step by step, then the printer log.
      Its first three runs were apparatus: the boot banner (now a CLS first, never compared),
      the `ZB` prompt inside the WIDTH 37 margin, and labels of repeated lines.
      ✅ **S1_editor (2026-11-06): SAME after the fix it FOUND --** [`S1_editor.ses`](probes/sessions/S1_editor.ses):
      AUTO (ended with Ctrl-C), a line retyped, RUN, RENUM / RENUM 100,,5 / RENUM 1000,110,
      LLIST, LIST ranges, DELETE, AUTO 200,20, NEW. **D-AUTOOK:** a break out of AUTO printed
      `Ok` here and NOTHING on the VG-8020 (R-AU8 had said so; editverb's `aut-` rows read the
      screen from the following LIST's echo, and the `Ok` sat above it). exa_brk
      (basic/program.asm) now clears PRMWANT and opens a fresh line -- the newline was the
      second step the session showed ([`sessions_s1c.out`](scratchpad/sessions_s1c.out) ->
      [`sessions_s1e.out`](scratchpad/sessions_s1e.out) -> [`sessions_s1f.out`](scratchpad/sessions_s1f.out)
      ALL SAME). 🔮 Predicted "a harness problem and probably one AUTO / RENUM divergence":
      both HIT.
      ✅ **S2_stopcont + S3_editclear (2026-11-06): SAME after the fix they FOUND --**
      [`S2_stopcont.ses`](probes/sessions/S2_stopcont.ses) (STOP, Ctrl-STOP, CONT, a variable
      changed between, CONT after an edit, NEW then CONT), [`S3_editclear.ses`](probes/sessions/S3_editclear.ses)
      (what an edit clears, measured as a scratch session first). **D-EDITCLR:** a stored /
      deleted line discards the FOR / GOSUB stack on the VG-8020 (`NEXT without FOR`,
      `RETURN without GOSUB` afterwards); zerobas kept the frames, and their resume pointers
      point into text the edit MOVED -- `GOTO 50` to a NEXT resumed INSIDE the inserted line 25
      ([`sessions_s2c.out`](scratchpad/sessions_s2c.out)). dl_store (basic/program.asm) now
      calls ctl_reset after store_line (in main: the store runs in the lineedit tenant and
      ctl_reset crosses to the sub ROM). And a bare number naming NO line is ERR 8 there
      (trapped by a still-armed ON ERROR) and touches nothing; zerobas relinked, cleared the
      variables and said nothing ([`editclear_a.out`](scratchpad/editclear_a.out)): prog_find_del
      returns CF = deleted, le_delete reports LE_STATUS 8, store_line raises it. After:
      S1 / S2 / S3 ALL SAME ([`sessions_s12.out`](scratchpad/sessions_s12.out),
      [`editclear_a2.out`](scratchpad/editclear_a2.out)); tests/test_program.py pins ERR 8 and the
      unchanged chain. 🔮 Predicted "all three SAME after the fix": HIT. S2's first form waited
      on INKEY$ and found D-STOPKEY3 (below) -- a timing-dependent row, so line 70 now waits on
      a variable set at the prompt.
      ✅ **S4_screenedit (2026-11-06): SAME** ([`S4_screenedit.ses`](probes/sessions/S4_screenedit.ses),
      [`sessions_s4b.out`](scratchpad/sessions_s4b.out)): cursor up onto LISTed lines, overtype, INS,
      a line copied by changing its number, BS inside a typed command. The runner gained
      inline key names ({UP} {INS} {DEL} {BS} ... and {NOCR}); its first run was apparatus (the
      prompt row with text typed over it read `ZB        NEW`; mapped like the bare prompt).
      🔮 Predicted "a screen-editor divergence (INS or the cursor after RETURN)": MISSED --
      D-SCREDIT's work holds.
      ✅ **S5_disk (2026-11-06): SAME after the fix it FOUND --** [`S5_disk.ses`](probes/sessions/S5_disk.ses)
      (`# @DISK`: SAVE, SAVE ,A, FILES, NEW + LOAD, MERGE over a typed program, NAME, KILL,
      LOAD ,R, RUN "file"; CF-3300 vs the DISK target). **D-MERGETOK:** MERGE of a
      TOKENISED file is `Bad file mode` (61) on the CF-3300; zerobas fed the binary to the
      ASCII driver and said `Direct statement in file` (57). fs_merge (sub2/filestmt.asm) reads
      byte 0 first (`$FF` = tokenised, LOAD's own marker) through a new resident-ABI entry
      `p0_dsk_agetbyte`, then re-opens -- ascii_load's rewind. (I first wrote 54, which is
      `File already open`; the next run said so.) 🔮 Predicted "a FILES layout or MERGE-of-a-
      tokenised-file divergence": HIT on the second. THE RUNNER, five apparatus fixes on the
      way, each a run that was wrong: a disk session starts in SCREEN 0 / WIDTH 37 (the
      CF-3300 boots in 32 columns -- a style split ruled to the VG-8020); it waits past the
      BLIND date RETURNs at 6 / 10 s (one landed in the session); IDLE needs the screen too --
      a direct command must reach a prompt that has been still for 0.3 s (zerobas's FILES was
      still reading the directory; the CF-3300's SAVE is silent > 2 s; a read DURING a scroll
      shows a row twice -- [`mergeecho_trace.py`](scratchpad/mergeecho_trace.py) found
      `MERGE "SUBS"` printed ONCE where the snapshot showed it twice); the function-key row
      is skipped when CNSDFG says it is up (it was always the "last row", so no prompt was
      ever seen). After: S1 / S2 / S4 / S5 ALL SAME ([`sessions_all.out`](scratchpad/sessions_all.out)).
      ⏸️ **S6_tape PARKED (2026-11-06)** ([`S6_tape_parked.ses`](scratchpad/S6_tape_parked.ses)): CSAVE / CLOAD /
      CLOAD? on a blank tape inserted by a new `{TCL ...}` step ({TMP} = the machine's
      scratch prefix). A tape RECORDED in the session does not play back reliably in this
      harness: in 7 layouts the VG-8020 found PROG1 again in exactly one (CSAVE, BSAVE, then
      `rewind`); a lone CSAVE then `rewind`, `{WAIT 2}` + `rewind`, or eject + re-insert read
      nothing there, and zerobas varied between Found and Device I/O error
      ([`sessions_s6d.out`](scratchpad/sessions_s6d.out), [`sessions_s6f.out`](scratchpad/sessions_s6f.out),
      [`sessions_s6g.out`](scratchpad/sessions_s6g.out)). Not committed as a gate row: a session
      that is not repeatable on the reference measures the recorder. D-TAPENEXT carries it.
      ✅ **S7_errors (2026-11-06): SAME** ([`S7_errors.ses`](probes/sessions/S7_errors.ses), [`sessions_s7.out`](scratchpad/sessions_s7.out)):
      typos at the prompt, an unclosed quote, a syntax error inside a RUN and the line fixed
      by retyping, ERR / ERL in direct mode, RESUME / CONT with nothing to resume, GOTO a
      missing line, 1/0, 2^1000, NEXT, `A$=5`, SQR(-1). 🔮 Predicted "a divergence in what
      follows a program syntax error": MISSED -- the error paths hold.
      ✅ **S8_input + S9_breaks (2026-11-06): SAME after the fix they FOUND --**
      [`S8_input.ses`](probes/sessions/S8_input.ses) (Redo from start, Extra ignored, a quoted comma, LINE
      INPUT, Ctrl-STOP during INPUT, CONT), [`S9_breaks.ses`](probes/sessions/S9_breaks.ses). **D-STOPINPUT:** Ctrl-STOP
      while INPUT waits is `Break in 90` on the VG-8020 (CONT asks again); zerobas LOST the
      press -- the REPL / INPUT read blocked in CHGET, which never sees Ctrl-STOP -- so the
      next typed line became the answer; Ctrl-C there was taken as an empty answer
      (`?Redo from start`); and Ctrl-STOP at the prompt mid-line abandons the line with NO
      `Ok` there ([`stopinput_a.out`](scratchpad/stopinput_a.out), [`sessions_s8.out`](scratchpad/sessions_s8.out)). Fix: read_line
      (basic/repl.asm) polls Ctrl-STOP for EVERY caller (rl_poll, AUTO's loop, now
      unconditional) and rl_break waits for the release; inp_readline (basic/input.asm)
      takes read_line's abort to inp_break -- SP back to SAVSTK, do_break at SAVTXT, the
      anchor's `ret`; the REPL's abort path (repl_abort) opens a line without the prompt.
      After: S8 / S9 SAME ([`sessions_s8c.out`](scratchpad/sessions_s8c.out), [`stopinput_a3.out`](scratchpad/stopinput_a3.out)).
      ✅ **AND TWO MORE ROUNDS THE SAME DAY.** S10_list showed the VG-8020 opens a line on
      Ctrl-STOP at an EMPTY prompt too (repl_abort's newline is unconditional now); and the
      DISK target's double detection (a second `Ok`, [`sessions_s8b.out`](scratchpad/sessions_s8b.out); two or three
      blank lines for one 0.2 s press, [`stopempty_a.out`](scratchpad/stopempty_a.out)) was D-STOPTEAR's torn read:
      C-BIOS's BREAKX reads the row with interrupts ON, so a longer ISR reads a held key as
      up -- rl_break now confirms the release with a second read, as rp_exec does. After:
      S8 / S9 / S10 ALL SAME on both targets ([`sessions_s8910b.out`](scratchpad/sessions_s8910b.out)). The FULL battery then
      went red on S2_stopcont: the 0.2 s press that BROKE the program was still held when the
      prompt's read began, which aborted an empty line -- the reference reacts to a PRESS. So
      every read first waits for the key to be up (rl_release, which rl_break shares); S1 / S2
      / S8 / S9 / S10 SAME ([`sessions_r4.out`](scratchpad/sessions_r4.out)). D-STOPKEY3 (the
      BIOS's own ^C, INKEY$ = 3) stays open.
      ✅ **S10_list (2026-11-06): SAME** ([`S10_list.ses`](probes/sessions/S10_list.ses)): 40 lines through AUTO, LIST
      forms, LIST ., LLIST, DELETE of a range. (Its {STOP} lands after LIST has finished --
      the runner waits for idle -- so a break INSIDE a scrolling LIST is not exercised.)
      🔮 Predicted "a divergence in the Redo / Extra messages or CONT after a break in
      INPUT": HIT on the second (it was the break itself).
      ✅ **S11_screen (2026-11-06): SAME** ([`S11_screen.ses`](probes/sessions/S11_screen.ses), [`sessions_s11.out`](scratchpad/sessions_s11.out)): KEY OFF / ON,
      KEY definitions (the key row reads `HELLO  LIST` on both), KEY LIST, WIDTH 30 / 20,
      SCREEN 1 and back, LOCATE, COLOR, a SCREEN 2 program returning to the prompt.
      🔮 Predicted "a function-key-row divergence after KEY / WIDTH": MISSED.
      ✅ **S12_progedit (2026-11-06): ONE DIVERGENCE, FIXED (D-CLEARCONT below), then SAME**
      ([`S12_progedit.ses`](probes/sessions/S12_progedit.ses), before
      [`sessions_S12_progedit.out`](scratchpad/sessions_S12_progedit.out), after
      [`sessions_S12_progedit2.out`](scratchpad/sessions_S12_progedit2.out)): every DELETE form
      and its errors, RENUM over a `GOTO 999`, RENUM into an overlap, and CONT after CLEAR, an
      edited line, DELETE, RENUM and NEW. 🔮 Predicted "a divergence in RENUM's Undefined line
      report or DELETE's error for a missing line": MISSED -- both agree; the one difference
      was CONT after CLEAR, which I had predicted would agree.
      ✅ **S13_datafile (2026-11-06): SAME** ([`S13_datafile.ses`](probes/sessions/S13_datafile.ses), [`sessions_S13_datafile.out`](scratchpad/sessions_S13_datafile.out), the
      CF-3300): a data file written at the prompt (OPEN / PRINT # / CLOSE), read back by a
      typed EOF loop, extended with APPEND, read by LINE INPUT #, and the errors on the way
      (EOF after the last line, PRINT # to a closed channel, a second OPEN of #1, KILL of an
      open file, OPEN of a missing file). Checked the screens are not a shared failure:
      ANNA / BERT / CAROL listed, `File already open` / `File still open` / `File not found`
      where expected. 🔮 Predicted "one divergence in an error message or EOF": MISSED.
      ✅ **S14_diskbin + S15_wildnames (2026-11-07): TWO FINDINGS, ONE FIXED, then SAME**
      ([`S14_diskbin.ses`](probes/sessions/S14_diskbin.ses), [`S15_wildnames.ses`](probes/sessions/S15_wildnames.ses); before
      [`sessions_S14_diskbin_hole.out`](scratchpad/sessions_S14_diskbin_hole.out), after [`sessions_S14_diskbin.out`](scratchpad/sessions_S14_diskbin.out),
      [`sessions_S15_wildnames.out`](scratchpad/sessions_S15_wildnames.out)): BSAVE / BLOAD with an offset, a random file
      by hand (FIELD, LSET / RSET, PUT, GET, LOC, LOF, GET past the end, FIELD overflow),
      COPY of a wildcard, FILES patterns, DSKF, MAXFILES. **D-WILDSAVE** (below, fixed) and
      **D-RECHOLE** (below, filed: an unwritten record's bytes). 🔮 Predicted "one divergence
      in an error path (GET past the end, the FIELD overflow, the wildcard SAVE)": HIT on
      the third.
      ✅ **S16_diskprog (2026-11-07): SAME** ([`S16_diskprog.ses`](probes/sessions/S16_diskprog.ses), [`sessions_S16_diskprog.out`](scratchpad/sessions_S16_diskprog.out)): a
      PROGRAM working its files -- a missing file trapped (53 at 20; ERR reads 0 after RESUME
      NEXT), PRINT # and PRINT # USING into two channels open at once, both read back
      interleaved with LOF / LOC, the 4th read trapped (55 at 40), INPUT$ from the prompt and
      past the end, a chain by RUN "file" (X = 0 in the second program). 🔮 Predicted "one
      divergence in an error path": MISS, all SAME. ⚠️ The first two runs were SAME TOO, and
      exercised nothing: my own `WRITE #` (not MSX BASIC -- Syntax error on both) and a
      program's ON ERROR still armed at the prompt (both machines: the INPUT$ lines printed
      TRAP lines). Reading the screens, not the verdict, caught it -- a session that agrees
      can agree on a typo.
      ✅ **S17_strings (2026-11-07): SAME** ([`S17_strings.ses`](probes/sessions/S17_strings.ses), [`sessions_S17_strings.out`](scratchpad/sessions_S17_strings.out)): INSTR,
      MID$ assigned, STRING$ / SPACE$, VAL of `12.5E2` / `&HFF`, HEX$(-1), string compares,
      PRINT USING (`###.##` overflow `%12345.68`, `+#####`, `**$##.##`, `!`, `\  \`, `&`,
      `#,###` overflow), SWAP, ERASE + DIM, and four errors -- on the VG-8020 and both
      targets. 🔮 Predicted "one divergence in a PRINT USING edge": MISS. (The doubled
      200-byte string is Out of string space, not String too long: CLEAR's default 200 B
      comes first -- my guess in the header, corrected; both machines agree.)
      ✅ **S18_math (2026-11-07): SAME, after routing the RULED class through CSNG**
      ([`S18_math.ses`](probes/sessions/S18_math.ses), [`sessions_S18_math.out`](scratchpad/sessions_S18_math.out); first run [`sessions_S18_math_raw.out`](scratchpad/sessions_S18_math_raw.out)): single
      vs double precision, `\` and MOD on negatives, CINT / FIX / INT at the halves, `^`,
      the transcendental functions, E notation, DEFDBL, integer overflow, `&H` / `&O` /
      `&B`, a seeded RND sequence, `0.1+0.2=0.3`. 🔮 Predicted "a divergence in a double
      print": HIT, and INSIDE THE RULED CLASS -- `2^0.5` 1.414213562373 on the VG-8020,
      1.4142135623731 here (true 1.41421356237309...; Joost 2026-07-13, correct rounding,
      docs/keywords/EXP.md). Fractional powers and the transcendentals now print through
      CSNG (6 digits must still agree). Two session slips of mine, the same on both
      machines: `(-8)^(1/3)` and `-32768%` raise (Illegal function call, Overflow) and cut
      their line short -- each on its own line now.
      ✅ **S19_flow (2026-11-07): SAME** ([`S19_flow.ses`](probes/sessions/S19_flow.ses), [`sessions_S19_flow.out`](scratchpad/sessions_S19_flow.out)): DATA /
      READ / RESTORE <line>, DEF FN with two arguments, FOR with STEP -1 and NEXT J,I, ON X
      GOSUB / GOTO with X out of range, nested GOSUB, nested IF THEN ELSE, and Out of DATA,
      RETURN without GOSUB (typed and in a program), NEXT without FOR, Undefined user
      function. `FOR K=5 TO 1` runs its body ONCE on the VG-8020 (K=6 after); zerobas the
      same. 🔮 Predicted "one divergence in which line an error names (Out of DATA: the
      READ's or the DATA's)": MISS -- both name the READ, 100.
      ✅ **S20_tape (2026-11-13): SAME** ([`S20_tape.ses`](probes/sessions/S20_tape.ses), [`sessions_S20_tape4.out`](scratchpad/sessions_S20_tape4.out)): the cassette round
      trip typed at the prompt -- CSAVE / CLOAD + LIST + RUN, SAVE "CAS:" / LOAD + LIST, BSAVE /
      BLOAD "CAS:" with a checksum (9520 on both) -- on the VG-8020 and both zerobas targets,
      openMSX's recorder switched from record to play inside the session ({TCL cassetteplayer
      play / rewind}). The "recorder apparatus" park was the session's own pacing: the
      runner's idle test also holds DURING a tape write, so with 2 s waits the recorder was
      switched before BSAVE's data block was down -- the VG-8020 never found BLK, zerobas
      Device I/O error ([`sessions_S20_tape2.out`](scratchpad/sessions_S20_tape2.out)); with room for each save, both finish
      ([`sessions_S20_tape3.out`](scratchpad/sessions_S20_tape3.out)). 🔮 "SAME; the risk is the apparatus": HIT on both counts.
      - [ ] **SAVE "CAS:" (ASCII): no pause between the header block and the data on zerobas** --
            🎚️ TIER 6 — (filed as TIER 5 "the VG-8020 writes for longer": 6 s after the command
            it was still writing where zerobas showed Ok, [`sessions_S20_tape3.out`](scratchpad/sessions_S20_tape3.out) snapshot 10).
            📏 MEASURED, neither speed nor length ([`savecas_len_probe.py`](scratchpad/savecas_len_probe.py) -> [`savecas_len_run2.out`](scratchpad/savecas_len_run2.out)):
            both machines record the SAME 272 bytes, but the VG-8020's signal is the header
            block (6.57 s), **1.10 s of silence**, then the data block (3.95 s); zerobas's is
            one continuous 10.90 s. The VG-8020 reads zerobas's tapes (tape-save's reference-load
            leg), so this is the tape's LAYOUT, not a failure.
            📏 **ALL THREE VERBS, AND THE BIOS (2026-11-13):** CSAVE and BSAVE "CAS:" the same
            shape ([`savecas_len_csave.out`](scratchpad/savecas_len_csave.out), [`savecas_len_bsave.out`](scratchpad/savecas_len_bsave.out)), and a DIRECT TAPOON + TAPOUT x 64
            from our own code: the VG-8020's signal starts **0.567 s after the motor**, ours at
            once ([`tapoon_delay_run1.out`](scratchpad/tapoon_delay_run1.out)) -- TAPOON's motor spin-up, a BIOS behaviour. ✅ **D-TAPOONDLY:**
            tape/tape.asm's TAPOON waits 0.567 s, motor on, before the leader (13 B; the tape bodies
            had 36 B to $0D01). A first count assumed 26 T a pass and gave 0.654 s -- the MSX's M1
            wait state makes it 30 ([`savecas_len_after.out`](scratchpad/savecas_len_after.out)). After: the leader starts at 0.567 s on
            both ([`savecas_len_after2.out`](scratchpad/savecas_len_after2.out)); ten tape gates green (tapebios, cassave, caswbrk, casrbrk,
            casbrk, cas-ascii, casbin, tapionlead, tapetail, castail; 🔮 "all green": HIT).
            ✅ **D-TAPLEADN, THE LONGER LEADER (2026-11-13):** counted ([`leader_count_probe.py`](scratchpad/leader_count_probe.py)):
            the VG-8020 writes 15359 / 3839 leader cycles (long / short) at 1200, ours 16000 /
            4000 ([`leader_count_run1.out`](scratchpad/leader_count_run1.out)) -- the reference's is HEADER x 1024 / x 256, HEADER being
            the published work-area cell, 15 at 1200 and **31 at 2400** on both references
            ([`header_cell.out`](scratchpad/header_cell.out)): at 2400 ours was HALF the reference's leader. zerobas also held the
            whole cassette table at $F3FC as 15 zero bytes where both references hold CS120 /
            CS240 / the active copy from power-on ([`cstables.out`](scratchpad/cstables.out)). Fixed: TAPOON computes the leader
            from the resolved baud (15 / 31 x 256 or x 1024; tape/tape.asm, tape bodies to $0CF2).
            (The 15-byte table seed was TRIED and taken out -- the item below.) After: 15360 / 3840 at 1200
            ([`leader_count_run2.out`](scratchpad/leader_count_run2.out)), 31743 / 7935 at 2400 on both ([`leader_count_2400b.out`](scratchpad/leader_count_2400b.out), the active
            entry POKEd from CS240). 🔴 It exposed a hole in D-TAPEBIOS's brk_release: BREAKX
            goes false once CTRL is up, and a STOP still held then latched a repeat -- caswbrk's
            phold row read `Break in 90` ([`tapleadn_phold1.out`](scratchpad/tapleadn_phold1.out); the table seed alone passed,
            [`tapleadn_phold_seedonly.out`](scratchpad/tapleadn_phold_seedonly.out)). brk_release now waits for STOP itself (SNSMAT row 7 bit 4).
            Ten tape gates green after both ([`tapleadn2_caswbrk.out`](scratchpad/tapleadn2_caswbrk.out) and the nine beside it).
            ➡️ LEFT: between the header and the data the VG-8020 spends ~0.53 s more (BASIC's side).
      - [x] **The cassette tables ($F3FC, 15 B) read 0 at power-on; seeding them exposed a 0.53 s
            MASKED FDC stretch** -- 🎚️ TIER 2 — ✅ **SHIPPED 2026-11-13 (D-CASSEED), see the end.** both references hold CS120 53 5C 26 2D 0F, CS240
            25 2D 0E 16 1F and the active copy from power-on ([`cstables.out`](scratchpad/cstables.out)); zerobas 15 zeros. A
            boot_wa seed (an LDIR of the 15 bytes, basic/catalias.asm) was built and the full
            battery went RED on programs-acceptance: L5_journal's longest frame-interrupt gap
            0.528 s against the CF-3300's 0.223 ([`tapleadn_journalg1.out`](scratchpad/tapleadn_journalg1.out); D-GCDI's rule) -- and
            0.036 without the seed ([`tapleadn_journal_noseed.out`](scratchpad/tapleadn_journal_noseed.out)), brk_release ruled out
            ([`tapleadn_journal_nobrk.out`](scratchpad/tapleadn_journal_nobrk.out)). Nothing reads the tables but the tape code, so the seed
            moved TIMING: a disk command now meets the drive at a moment that keeps the CPU
            masked ~0.5 s. fdc_settle is ~0.9 ms and D-FDCDI's windows cover only the first-DRQ
            wait, so the stretch is in another FDC wait.
            🎯 **FOUND (2026-11-13, D-IFFREAD):** a PC / SP / IFF sampler in the gap
            (probes/programs/run_programs.py, ZB_GAPTRACE=FILE) -- the stretch is the DRQ waits
            fwd_wait / fdc_rd_wait of the FAT / directory writes closing a save (hkds_go ->
            disk_write_end), with FDC_IFF 0: one sector recorded FDC_IFF 1, the next 0, and IFF
            stayed 0 from there ([`fdcgap_trace4.out`](scratchpad/fdcgap_trace4.out)). fdc_di_save read the caller's state with ONE
            `ld a,i` -- the NMOS erratum: an interrupt accepted DURING it reads P/V 0 though
            interrupts were on; fdc_io_done then left the CPU masked and every later sector
            inherited it. Now asked twice (disk/fat.asm; +1 B). With the seed: the longest gap
            0.036 s ([`iffread_journal_seed.out`](scratchpad/iffread_journal_seed.out)) -- but **a new difference: `NAME "COPY.TXT" AS
            "OLD.TXT"` answers ERR 65 (File already exists) where the CF-3300 has none** (its line
            190), and only with seed + fix together; the fix alone is SAME
            ([`iffread_journal_noseed.out`](scratchpad/iffread_journal_noseed.out)). Reading: the false read had masked these transfers BY
            ACCIDENT; with D-FDCDI's windows working as designed, at the seed's timing one
            directory read comes back wrong. ➡️ That windowed-read fault (L5_journal + the seed
            reproduces it) before the seed ships. Two more single `ld a,i` sites:
            p1_blit_tmpl (disk/kernel.asm, the page-1 bounce's RAM template) and br_back_tmpl
            (disk/runtime.asm) -- both RAM templates with an installed size to keep.
            ✅ **D-CASSEED (2026-11-13): THE ERR 65 DOES NOT REPRODUCE.** The seed re-applied on
            today's tree -- ROM sources byte-identical to the build that gave ERR 65 (`git diff
            1fb60f86 HEAD` touches only disk/fat.asm's D-IFFREAD, which that build had) -- and
            L5_journal run TWELVE times from a fresh build: SAME every time, t=49.4, 44 gaps, max
            0.036 s, identical figures run to run ([`WR_journal1.out`](scratchpad/WR_journal1.out) .. [`WR_journal12.out`](scratchpad/WR_journal12.out)). run_programs
            feeds keys through KEYBUF and gives each run its own copy of disk/empty720.dsk, so
            the run is deterministic; the ERR 65 run (t=47.2, 32 gaps) came from a build that
            cannot be reconstructed, and the "windowed-read fault" reading of it is WITHDRAWN as
            unsupported -- no fault was ever isolated. 🔴 And the seed as first written had its
            own defect: `bw_cas` sat in boot_wa's FALL-THROUGH, so its 15 data bytes ran as
            code (`ld d,e` / `ld h,$2D` / `rrca` / ...) on the way into set_clmlst -- harmless
            register traffic, but not the code that was reviewed. The table now follows
            set_clmlst's `ret` (basic/catalias.asm). The boot sweep (`make sysvarsweep
            ONLY=s0-boot`, [`WR_svs2.out`](scratchpad/WR_svs2.out)) no longer lists $F3FC..$F40A in BASE-DIFF: the 15 B read
            as both references'. The sweep itself had stopped at import -- D-WSZERO S8 renamed
            the VALTYP symbol VALTYP_PUB (probes/basic/basic_probe_sysvarsweep.py, one row).
            ➡️ LEFT (filed, not this item): p1_blit_tmpl / br_back_tmpl's single `ld a,i`.
      - [x] **Two more single-`ld a,i` IFF reads: p1_blit_tmpl (disk/kernel.asm, the page-1
            bounce's RAM template) and br_back_tmpl (disk/runtime.asm)** -- 🎚️ TIER 2 — the
            class D-IFFREAD fixed in fdc_di_save: an interrupt accepted DURING the `ld a,i` reads
            P/V 0 though interrupts were on, so the restore leaves the CPU masked (a frame-
            interrupt gap, D-GCDI's rule). Not yet SEEN at either site; both are RAM templates
            with an installed size to keep, so the second read (+3 B each with the jump) needs
            room in the installed area first.
            ✅ **D-IFFREAD2 (2026-11-14): BOTH ASK TWICE NOW**, as fdc_di_save -- `ld a,i / jp pe /
            ld a,i`, the `jp` aimed at the RAM copy (P1_BLIT / BR_BACK + offset). ROOM: (1) the
            blit's installed run was 27 B, not the 36 init.asm still claimed (FLD_END moved to
            $F019 under it); one `push af` now carries both the sub-slot state and the IFF
            flag (`di` / `ld a,(nn)` / `cpl` leave P/V alone), so the blit stays 27 B; (2) the
            bridge chain grew 5 B to $DF86, under DOS_RESV_TOP $DF93; (3) the disk ROM's 10 B
            came from moving wrbytes_add_recsize (18 B, one `call`) into the 26 B hole in
            front of the $75A5 pin -- the disk ROM's largest 0x00 run is now under 16 B.
            Two new build asserts at the end of disk/disk.asm (the blit against FLD_END, the
            chain against DOS_RESV_TOP), each KNIFED: tightened by a byte, each broke the build.
            tools/check_disk_walls.py crashed on a ROM with no run of 16 B or more; it now
            reports 0. p1multi-acceptance and p1vec-acceptance PASS ([`IR_p1multi.out`](scratchpad/IR_p1multi.out),
            [`IR_p1vec.out`](scratchpad/IR_p1vec.out)). ⚠️ NO ROW WITNESSES THE FIX: the false read needs an interrupt
            accepted during one particular instruction, and neither site was ever SEEN to fail.
      - [x] **SCREEN ,,,n does not select the cassette baud; CSAVE ,n sets only ACT_LOW** --
            🎚️ TIER 3 — on both references `SCREEN ,,,2` copies CS240 (5 B) into the active
            LOW / HIGH / HEADER slots ($F406) and ,,,1 copies CS120 ([`cstables.out`](scratchpad/cstables.out)); on zerobas
            SCREEN's fourth argument leaves the slots untouched, so a program that SCREEN ,,,2s
            and CSAVEs writes 1200 baud. CSAVE ,n sets the LOW word only (sub2/loadsave.asm
            ls_csav_speed; HIGH / HEADER stay). The sub ROM has ~2 B free.
            ✅ **D-CASBAUD (2026-11-14):** cas_sel (sub2/loadsave.asm) copies the selected 5-byte set
            (CS120 / CS240, seeded at boot since D-CASSEED) into $F406; SCREEN's slot 3 (sub2/
            scrstmt.asm) and CSAVE ,n call it. Room: `ld ix,p0_skipsp_test / call p1cb` stood six
            times in loadsave.asm -> ls_skipsp (a `jp p1cb` tail returns to the caller's site, as
            CLPRIM returns to whatever is on the stack); sub page 1 2 -> 9 B free WITH the feature
            (2026-11-14). New `make casbaud-acceptance` (probes/basic/basic_probe_casbaud.py): boot,
            SCREEN ,,,2, ,,,1, CSAVE ,2 -- 4 / 4 as the VG-8020 ([`CB_run2.out`](scratchpad/CB_run2.out); 🔮 HIT); KNIFED
            against the old sub2 -> ,,,2 and CSAVE ,2 DIVERGE ([`CB_knife.out`](scratchpad/CB_knife.out)).
      - [x] **D-CSAVEREST — `CSAVE` in a program skips the REST OF ITS LINE** -- 🎚️ TIER 1 —
            the happy path of saving from a program: `20 CSAVE "X":PRINT "[C]"` then `30 PRINT
            "[D]"` prints [C] and [D] on the VG-8020, only [D] here (found 2026-11-14 writing
            casbaud-acceptance; present on HEAD before D-CASBAUD). 🤖 AUTONOMOUS.
            ✅ **FIXED 2026-11-14:** BSAVE "CAS:" had it too, SAVE "CAS:" did not -- it ENDS the run
            on both machines ([`CR_run1.out`](scratchpad/CR_run1.out)). ls_sv_tenant (sub2/loadsave.asm, CSAVE's and BSAVE
            "CAS:"'s only exit) continued with ls_ret, a handler `ret` that ends the LINE; it
            keeps the cursor across the save engine now and continues at exec_stmt (+3 B; sub
            page 1 6 B free, 2026-11-14). casbaud-acceptance gained the three mid-line rows: 7 / 7
            ([`CR_gate.out`](scratchpad/CR_gate.out)); KNIFED -> CSAVE / BSAVE rows DIVERGE, SAVE's stays SAME ([`CR_knife.out`](scratchpad/CR_knife.out)).
      - [ ] **The 2400-baud high tone is 5013 Hz here, 4811 Hz on the VG-8020** -- 🎚️ TIER 6 —
            [`leader_count_2400b.out`](scratchpad/leader_count_2400b.out); CAS_HHALF24 (tape/tape.asm) was never measured against an oracle,
            as its own comment says. The 1200 tones are 2390 / 2393 Hz.
      ➡️ NEXT sessions: more disk (the CF-3300 via `# @DISK`). NOT a break inside a scrolling LIST
      (2026-11-07): the screen after the break shows WHERE LIST was cut, which is each
      machine's LIST speed, so a screen-compared session would read the speed, not the
      break -- that needs a row that reads the break's outcome without the cut point.
