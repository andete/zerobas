- [ ] 💰 **D-NGRAM: EXACT REPEATED INSTRUCTION SEQUENCES — `req_letter` SHIPPED
      (−50 B), THREE CANDIDATES LEFT.** [`docs/spec-ngram.md`](../../docs/spec-ngram.md),
      `scratchpad/ngram_sweep.py --main`. Built because `clone_scout` masks two
      operands BY DESIGN and so cannot see EXACT repeats collapsible into a
      shared body — the shape that paid in D-BAREEND (+45 B) and D-POPRAISE.
      ✅ **SHIPPED: `req_letter`.** `call skip_spaces / call is_letter /
      jp nc,stmt_error` stood open-coded at **TEN** statement entries (DIM,
      ERASE, DEF FN, FIELD, the disk string-var parse, INPUT, both SWAP
      operands, FOR, READ) at 9 B each; one 10 B body + ten 3 B calls replaces
      90 B. Low region read 50 → 68 B free, page 1 154 → 186 B, 2026-08-28.
      🔴 **TWO INSTRUMENT FAULTS CAUGHT BEFORE ANY NUMBER WAS QUOTED**: the raw
      table was ALL `sub/` (mathpack repeats, where thousands of bytes are
      already free — `--main` rescores on main sites only), and **a CONDITIONAL
      jump is not a terminator**, so the top candidate was first mispriced as a
      shared tail it can never be.
      ✅ **SHIPPED 2026-08-28: `req_operand`** (D-NGRAM2,
      [`docs/spec-basic-ngram2.md`](../../docs/spec-basic-ngram2.md)) — `call
      skip_spaces / or a / jp z,loc_missing / cp COLON / jp z,loc_missing`, the
      top-ranked exact repeat in the SCARCE regions. 6 sites x 12 B -> one 13 B
      body + six 3 B calls. **Page 1 read 185 -> 226 B free on 2026-08-28** (a
      READING; run `make basic-reloc`). 18 rows, DIFF 0/18; 2 knives.
      🔬 **A LINE-BASED GREP FINDS ONLY 4 OF THE 6** — four sites carry comment
      lines INSIDE the sequence. Enumerated at instruction level, and checked for
      an INTERIOR LABEL (none), which is what would make the span byte-identical
      without being ENTERED the same way.
      ✅ **ALSO SHIPPED 2026-08-28: `le_call` / `le_call_op`** (D-NGRAM3,
      [`docs/spec-basic-ngram3.md`](../../docs/spec-basic-ngram3.md)) — the
      `subrom_call` + LE_STATUS sequence at LIST / line-STORE / DELETE / RENUM /
      AUTO. Filed at 40 B; **it is 49 B**, because four of the five set `LE_OP`
      immediately before, so a 3 B second ENTRY drops four `ld (LE_OP),a`.
      **Page 1 read 226 -> 275 B free on 2026-08-28** (a READING; run
      `make basic-reloc`). 9 rows, DIFF 0/9.
      🔴 **THE PER-SITE WITNESS HAD TO BE STATIC.** The line STORE is one of the
      five sites and the probe harness TYPES its own program through it, so a
      knife on the helper takes the fixture down and EVERY row moves, controls
      included — there is no control on that apparatus that survives it. Arm S1
      enumerates instead: 0 open-coded copies left, exactly 5 calls.
      ⚠️ **A SIXTH SITE (`relink`) MEASURED AND DECLINED**, 7 B: it returns
      WITHOUT reading `LE_STATUS`, so folding it in changes the A/flags its
      callers see, and `cload.asm` has two plain `call relink` sites whose flag
      dependence is unverified.
      ✅ **ALSO SHIPPED 2026-08-28: `shx_tail` / `shx_op_tail`** (D-NGRAM4,
      [`docs/spec-basic-ngram4.md`](../../docs/spec-basic-ngram4.md)) — the sub-ROM
      string-op RESULT tail at CHR$ / HEX$-OCT$-BIN$ / SPACE$ / STRING$. **Low
      region read 70 -> 94 B free on 2026-08-28** (a READING; run
      `make basic-reloc`). 13 rows, DIFF 0/13.
      🔴 **I NAMED THE SITES FROM NEARBY PROSE AND ONE WENT UNWITNESSED**: the
      sweep reports LINE NUMBERS, and `:733` is CHR$, not SPACE$ as I wrote — so
      CHR$ had no row while the set looked complete. The knife caught it only
      because its prediction named WHICH rows should move. **Name a site from
      its ENCLOSING LABEL.**
      ✅ **ALSO SHIPPED 2026-08-30: `load_commit_prog`** (D-NGRAM12,
      [`docs/spec-basic-ngram12.md`](../../docs/spec-basic-ngram12.md)) — the
      ten-instruction completion tail that the TAPE loader (`do_tape_prog`,
      CLOAD) and the DISK loader (`disk_prog_load`, `LOAD"file"`) each carried
      verbatim. `dpl_done`'s WHOLE BODY was the run, so it is a free `equ`
      alias, not a 3 B shared-tail jump: **22 B gross, 21 B net** after the
      `jr z,dpl_done` that no longer reached had to widen to `jp`. **Page 1 read
      323 -> 344 B free on 2026-08-30** (a READING; run `make basic-reloc`).
      11 disk + 31 tape rows, DIFF 0; 2 knives + S1; 47/47 battery.
      🔴 **THE SWEEP RANKED IT AT 19 B AND IT IS WORTH 22** — it prices every
      collapse as a shared TAIL (one site pays a jump), and cannot see that a
      site whose whole label block IS the run can be reached by a free `equ`.
      **Worth checking on any candidate whose second site is a whole label
      block.** The `--main` board below it is now thin: 18, 16, 15, then 14s.
      🔴 **AND ITS FIRST KNIFE FOUND A HOLE IN A STANDING GATE.** Cutting the
      `$0000` end-of-program marker moved the tape row and NOT ONE disk row:
      `runtail-acceptance`'s fixture re-loads a program byte-identical to the
      one it just typed, so the terminator the cut failed to write was already
      in RAM. Nine rows agreed for a reason that had nothing to do with the
      marker. Closed by a new row, `load-short` (a LONGER program resident, so
      the loader must terminate a real line away) — 11/11 agree with the
      CF-3300, and it moves under the knife.
      ✅ **ALSO SHIPPED 2026-08-31: `str_eval_ix`** (D-NGRAM15,
      [`docs/spec-basic-ngram15.md`](../../docs/spec-basic-ngram15.md)) — `push ix /
      pop hl / call str_eval` at SEVEN sites (relational LHS and RHS, CVI, FRE,
      the shared string-arg parse, INSTR, the string relational's RHS). **Low
      region read 112 -> 121 B free and page 1 361 -> 367 on 2026-08-31**
      (a READING; run `make basic-reloc`). 14 rows, 1 scored DIFF (pre-existing),
      1 NO-ORACLE; 2 knives + S1; 48/48 battery.
      🎯 **THE BODY IS SITED WHERE THE CALLERS ARE NOT.** Four callers are in
      page 1 and three in the SCARCE low region — but `str_eval` itself is a
      page-1 routine the low-region callers already reach, so the body goes
      beside it and the scarce region takes the LARGER share (+9 vs +6).
      Siting by "where the code lives" would have given low +3.
      🔴 **A LINE-BASED GREP FOUND 6 OF THE 7** — `ev_ff_fre`'s site carries a
      comment on its `push ix` line. Enumerated at instruction level instead.
      🔴 **AND A THIRD KNIFE WAS BUILT, RUN AND DELETED**: forcing CF set moved
      ALL FOURTEEN rows, both CONTROLS included — a knife that moves the controls
      has broken the machine, not the subject. The decline half therefore rests
      on the rows agreeing with both references plus K-N15B's asserted zero, and
      the spec says so rather than papering over it.
      ✅ **ALSO SHIPPED 2026-08-31: `fname_dev`** (D-NGRAM16,
      [`docs/spec-basic-runarg.md`](../../docs/spec-basic-runarg.md)) — `call
      fname_expr / ld de,dev_cas / call dev_cmp` at LOAD, RUN"name", SAVE and
      BSAVE, 9 B each. **+15 B**, spent again by the D-RUNARG fix the same row
      set found (net −6 B, page 1 355 -> 349).
      🔴 **THE RISK WAS `fname_expr`'s OUTWARD JUMP, NOT THE Z FLAG** — it does
      `jp nc,els_tc_common` on a non-string filename, which behind a helper sits
      one frame deeper (the D-NGRAM8 shape). Both of that tail's exits RAISE and
      never return, so it cannot bite — and three `n.*` rows drive a non-string
      filename through three of the four verbs to say so.
      ✅ **ALSO SHIPPED 2026-08-31: `req_comma`** (D-NGRAM17,
      [`docs/spec-basic-reqcomma.md`](../../docs/spec-basic-reqcomma.md)) — the
      MANDATORY-comma run at FIELD, INPUT#, SWAP and SOUND. **Low region read
      121 -> 127 B free and page 1 349 -> 357 on 2026-08-31** (a READING; run
      `make basic-reloc`). 12 rows, 2 knives + S1, 48/48.
      📏 **THE DENOMINATOR IS 72 `cp ','` SITES**, grouped at instruction level
      by WHERE THEY JUMP: 4 to `stmt_error` (required — these), 3 to `exec_stmt`
      (an optional comma that ends the statement), the rest two-site groups with
      their own local labels. Only a shared DESTINATION can share a body.
      🔴 **AND THE KNIVES FOUND FOUR ROWS THAT CANNOT REACH THEIR SITE**: I
      predicted 5 and 4, and 4 and 2 moved. `g.sound` read the NEXT LINE's PRINT
      (fixed — joined with `:`, and the knife then moves it); `g.field` reads
      after a CLOSE (the divergence above); `b.field` raises Bad file number
      first; and `b.swap` never presents a missing comma at all, because the
      crunch folds `A B` into the variable `AB` — measured by `x.spacename`, not
      guessed.
      ✅ **ALSO SHIPPED 2026-08-31: `req_gosub`** (D-NGRAM18,
      [`docs/spec-basic-reqgosub.md`](../../docs/spec-basic-reqgosub.md)) — the GOSUB
      keyword the four TRAP statements require (ON STOP / ON INTERVAL= / ON
      STRIG / ON KEY). **Page 1 read 357 -> 371 B free on 2026-08-31** (a
      READING; run `make basic-reloc`). 12 rows on three machines, DIFF 0;
      1 knife + S1; 48/48.
      🔴 **A LINE-BASED MATCH FOUND ZERO OF THE FOUR** — the token is
      `GOSUB_TOKEN` (not the lower-case name the sweep prints) AND a comment line
      sits between the `jp` and the `inc hl` at every site. Matched at
      instruction level, tolerating interior comments.
      🔴 **AND TWO FINER KNIVES WERE INVISIBLE TO THEIR OWN ROWS.** Dropping the
      `inc hl` moves NOTHING: the slot loop then finds no line number and
      SILENTLY CLEARS the handlers, and no row here makes a trap FIRE. Accepting
      a missing GOSUB moves nothing either: `ON KEY 100` is rejected LATER, not
      by this check. What does work is making the helper ALWAYS RAISE — exactly
      the four `g.*` rows move, the three controls hold — which is the
      observable form of "every site was rewired" and refuted the live
      hypothesis that the sites were dead code.
      ✅ **CLOSED SAME DAY (D-NGRAM18b) — AND MY "OWED" NOTE WAS WRONG ABOUT THE
      TREE.** It said a firing row "needs an input fixture this probe does not
      build"; `probes/basic/basic_probe_stop_trap.py` ALREADY presses Ctrl-STOP
      through openMSX's key matrix, and five trap probes sit beside it. Scored
      against it, dropping the `inc hl` moves **all 8** zb rows — the handler is
      silently cleared so the trap never fires.
      🎯 **AND THE OTHER BRANCH IS REACHED, NOT DEAD**: pointing it at a
      DISTINGUISHABLE error makes `ON STOP/KEY/STRIG 100` report `Illegal
      function call`, so the arm runs. `ret nz` moved nothing because a
      DOWNSTREAM check reports the identical `Syntax error` — the D-CVISTRTM
      shape. (`ON INTERVAL=100 100` stays `Overflow`, confirming from the machine
      what its geometry predicted.)
      ⚠️ **"No fixture exists" is a claim about the tree and deserved a
      `ls probes/` before it was written down.**
      ✅ **ALSO SHIPPED 2026-08-31: `evmc_arg_int`** (D-NGRAM19,
      [`docs/spec-basic-argint.md`](../../docs/spec-basic-argint.md)) — the argument
      gate + "is it already an int16?" that ABS, SGN, INT and FIX each opened
      with. **Page 1 read 371 -> 378 B free on 2026-08-31** (a READING; run
      `make basic-reloc`). 16 rows on three machines, DIFF 0; 2 knives + S1.
      🔴 **THE SWEEP RANKED IT 14 B AND IT IS WORTH 7.** Two things leave the run
      for the caller and the ranking can see neither: the `ret nz` returns FROM
      THE VERB (inside a helper it would land one frame too shallow -- the
      D-NGRAM8 bug), and the final `cp 2` publishes a Z FLAG each of the four
      branches on DIFFERENTLY. So the malformed case moves to CARRY and each site
      keeps a 1 B `ret c` -- the D-ARGOPEN shape, a flag a row can see beating a
      frame trick. **The ranking is a floor in BOTH directions**: D-NGRAM12 was
      worth more than ranked, this is worth less.
      🔴 **AND A THIRD MASKED CHECK IN ONE DAY.** `scf` -> `or a` (malformed
      stops reporting carry) moved ZERO rows: `ev_mc_arg_checked` has already
      armed the deferred D-F2-4 error and `check_expr_errors` reports it at the
      statement boundary regardless. The `ret c` decides whether the verb's BODY
      runs on garbage, not what is printed. Re-aimed at reachability, it moves
      all 14 subject rows with both controls holding.
      ➡️ **STILL OPEN, measured 2026-08-28:** an `inc hl` +
      req_letter variant (**31 B**, 6 sites) that **OVERLAPS what shipped and
      must be RE-RUN, not inherited**.
      ✅ **ALSO SHIPPED 2026-08-30: `dpl_get_store`** (D-NGRAM13,
      [`docs/spec-basic-ngram13.md`](../../docs/spec-basic-ngram13.md)) — the disk
      loader's `fat_io_getbyte` + store-at-CLPTR run, open-coded 3x at 14 B.
      **Page 1 read 344 -> 355 B free on 2026-08-30** (a READING; run
      `make basic-reloc`). 9 rows, 3 DIFF (all pre-existing, see below);
      2 knives + S1.
      🔴 **THE 15 B VERSION WORKED AND WAS THE WRONG ONE.** Folding
      `jp c,dpl_err_pop` into the helper is 4 B cheaper and needs a frame fix
      (the helper's own return address sits on the caller's guarded count, so
      the tail must drop two). **K-N13A cut that fix and moved ZERO rows — on
      TWO fixtures picked to make the bogus return address hostile ($0007, then
      $0BB3).** The stack below the loader is the REPL's own, so a stray `ret`
      finds a plausible address in it and the machine wanders back to the
      prompt. 4 B given back for the CF-return shape, whose failure IS a
      reading. The D-ARGOPEN call, for the same reason.
      🔴 **AND A SECOND CHECK DOWNSTREAM HID THE FIRST ONE'S FAILURE.** With the
      EOF swallowed the loader runs past the file and hits EOF again at the next
      LINK-WORD read, which prints the IDENTICAL message — so the two rows that
      read only the MESSAGE cannot move. Only the rows that read the resulting
      PROGRAM see it.
      ✅ **AND THE CLASS IS NOW COUNTED (2026-09-01, D-LOADSHAPE,
      `scratchpad/loadshape_audit.py` — the audit's answer is in its header):
      denominator 9, fully blind 0, partial 1.** Four candidates are genuinely
      guarded (NEW / POKE witnesses); four of the finder's own flags were FALSE
      POSITIVES (token vectors, error-surface rows, a VPOKE-sentinel the regex
      missed); ONE is partial — `disk_probe_save_ascii` witnesses only the
      corrupted line's restoration — adjudicated as covered because a partial
      load is a REFUSAL on this tree (D-TRUNCLOAD's measured EOF arms), so the
      silent-partial shape cannot occur without truncload's rows going red
      first. 🔴 **The four names the filing guessed (`castail`, `bload`,
      `fat-*`, `merge`) are not in the class at all** — their loads come from
      minted fixtures, not a same-boot save. The fear outran its instances.
      🎚️ BUDGET — ROM carve
      🤖 AUTONOMOUS — **marker added 2026-09-01; this block had none**, and an
      🟢 **A PAGE-1 CARVE OUT OF THIS SEAM, 2026-09-06 (D-PENDTAIL) — 8 B IN MAIN
      PAGE 1 AND 4 B IN THE LOW REGION, FOR ZERO NEW BYTES.** `--main` ranked
      `call penderr_set | ld de,0 | ret` at **4 sites, 12 B**: `evmc_sqr_err` and
      `evmc_exp_overflow` ([`basic/expr.asm`](../../basic/expr.asm), page 1) and two in
      [`basic/float-arith.asm`](../../basic/float-arith.asm) (low region). The canonical
      is an EXISTING tail given a name — `penderr_de0` at `cpow_frac`'s — so the
      shared body costs nothing and the other three become a 3 B `jp` in place of
      7 B. Page 1 **0 → 8 B free**, low region **2 → 6 B** (2026-09-06).
      🎯 **AND IT IS NOT THE `ev_f_err` SHAPE THIS SWEEP DECLINES DIRECTLY ABOVE
      IT.** The declined candidate shares a tail that MAKES the decision — "fail
      with no error code", which measured wrong at all seven sites. Here the
      decision is the error CODE; it is made by the `ld a,<code>` that STAYS at
      each site, and only the mechanical call-and-return-zero is shared
      [[a-shared-tail-is-not-a-decision]]. Two candidates one line apart in the
      same ranking, opposite verdicts, and the ranking cannot tell them apart —
      which is why the sweep prices and a human decides.
      ⚠️ **`evmc_sqr_err` IS ONE OF D-DUPSPAN2's ELEVEN OWED CANONICALS**, and its
      body is now a `jp`. A knife planted there scores a different span than the
      one that roster was built against; re-read the roster before cutting it.
      📏 Battery 114/114 green, full — the ROM moved. The carve is
      behaviour-neutral by construction (same instructions, reached by `jp`), and
      the battery is what says so.
      🟢 **AND A SECOND ONE THE SAME EVENING (D-PUBTAIL), 2026-09-06: ANOTHER
      8 B RECOVERED IN PAGE 1 AND 8 B IN THE LOW REGION ON THAT DATE, AGAIN FOR
      ZERO NEW BYTES.**
      `ld (STRPTR),hl | pop hl | jp str_eval_ok` at **five** sites — three in
      [`basic/str-engine.asm`](../../basic/str-engine.asm) (low) and two in
      [`basic/strvar.asm`](../../basic/strvar.asm) (page 1). Canonical `str_pub_ok` is
      the existing tail at `sel_close`; the other four became a 3 B `jp`.
      **Page 1 8 → 16 B free, low region 6 → 14 B (2026-09-06).**
      ⚠️ **THIS TAIL CARRIES A STACK PROTOCOL AND THE `penderr` ONE DID NOT.**
      Every site must arrive with HL = the descriptor and EXACTLY ONE saved
      cursor on top, which the shared `pop hl` takes. A site at a different depth
      would return to the WRONG PLACE, and neither a size check nor a
      byte-identity check would say so
      [[a-mechanical-fix-can-break-a-different-invariant]] — the same shape as
      the `push_lhs_frame` candidate this sweep DECLINES for a frame protocol.
      All five were read first; the battery is what confirms it.
      🔴 **THE FIRST ATTEMPT WROTE NOTHING, AND THAT WAS THE GUARD WORKING.** The
      anchors were built from a COMMENT-STRIPPED dump, so none matched the real
      lines and every assertion tripped before any write. Redone by line index
      with a per-line assertion on the stripped opcode, keeping each site's
      original comment text
      [[check-the-name-is-free-before-cat-heredoc]].
      📏 **TOGETHER THE TWO CARVES TOOK MAIN PAGE 1 FROM 0 B TO 16 B FREE AND THE
      LOW REGION FROM 2 B TO 14 B, ON 2026-09-06, ADDING NO BYTES.** Both figures
      rot — `make basic-reloc`.
      unmarked open item is unclassified, so the loop was skipping the one arc it
      has shipped nineteen slices of. Not a tie: what is left is a MEASUREMENT
      (`scratchpad/ngram_sweep.py --main` — does any candidate still rank above
      its call overhead in the scarce regions?), and D-NGRAM2..19 all shipped
      unattended. ⚠️ **THE TITLE'S "THREE CANDIDATES LEFT" IS A RANKING AND
      RANKINGS ROT** — re-run the sweep, do not spend that number.
      📏 **RE-RUN 2026-09-02 (`scratchpad/ngram_sweep.py --main`, 20760
      instructions, 524 positively-priced candidates before dedup). "THREE" WAS
      STALE: 14 ranked, 3 already ⛔ DECLINED with their reasons recorded, so
      ~11 open.** The ranking has NOT collapsed, but the HEAD has: the top three
      are all declined, and the best open candidate is **12 B**, where the
      shipped slices were 17–50 B. Top open, verbatim:

          12  [TAIL] ld (errmark),a | ld de,0 | ret             4 sites
          12  [sub]  jp nz,ev_f_empty | inc ix | call ev_sp     4 sites
          12  [TAIL] call penderr_set | ld de,0 | ret           4 sites
          12  [TAIL] ld (strptr),hl | pop hl | jp str_eval_ok   4 sites
          12  [sub]  call skip_spaces | or a | ret z | cp colon 5 sites

      ⚠️ **THE FIRST ONE IS THE DECLINED 18 B CANDIDATE'S TAIL** — the same four
      sites minus `ld a,$dd`. D-EVFERR's decline is about what a `jp ev_f_err`
      MEANS (failing with NO error code), so whether it also forbids the tail is
      an open question, not an inherited answer.
      🎯 **THE LAST ONE IS `req_operand`'S NEAR-TWIN** — the same
      end-of-statement test with `ret z` instead of a raise. Read it against
      `req_operand` and `scan_stmt_end` before treating it as new.
      💰 **NOT SPENT, AND THE REASON IS THE WALL, NOT THE RANKING**: page 1 was
      301 B free on 2026-09-02. At 12 B a slice, each costing a knife and a row
      set, the carve pressure that justified D-NGRAM2..19 is not there today.
      Re-read this when a slice is actually blocked on bytes.
      ✂️ **2026-10-10 (loop): the top re-ranked candidate (9 B by the sweep,
      [`carve_ngram.out`](../../scratchpad/carve_ngram.out)) WAS AN EXISTING ROUTINE,
      worth 30 B.** `ld (ARY_KEY),bc / ld a,1 / ld (ARY_TYPE),a / ld a,5 / ld
      (ARY_OP),a / call ary_engine_call` at `tgt_store_desc` and `str_set_key` is
      `var_alloc_or_find`'s body with A = 1, and both sites then reloaded
      `ARY_ADDR`, which that routine returns in HL — so each became `ld a,1 / call
      var_alloc_or_find` with `ret nc` / `jr nc` (its CF contract): page 1 **14 →
      44 B** (predicted 30: hit). No caller of either reads the flags (FPERR is the
      signal: str-engine's `xor a`, ex_read's `check_expr_errors`, `fp_stmt_done`,
      `fn_st_x`). 🔴 **THE FAILURE BRANCH HAS NO BEHAVIOURAL WITNESS:** knife K-NG1
      (`jr nc,ssk_target_oom` cut) moved nothing in array-acceptance (its OOM
      rows assign LITERALS, stored by reference —
      [`carve2_knife_arrays.out`](../../scratchpad/carve2_knife_arrays.out)) nor in a
      new string-scalar OOM probe ([`sskoom_probe.py`](../../scratchpad/sskoom_probe.py),
      [`sskoom_run.out`](../../scratchpad/sskoom_run.out): zerobas `ERR 7 N 0` uncut and
      cut, [`carve2_knife.out`](../../scratchpad/carve2_knife.out)) — FPERR raises the
      error either way; the branch only keeps a descriptor from being written
      through the entry pointer. The deferred-error class
      ([[a-guard-witnessed-only-by-a-deferred-error]]). The probe's VG-8020 side
      gave no capture (its DIM sizing differs) — not a comparison yet.
