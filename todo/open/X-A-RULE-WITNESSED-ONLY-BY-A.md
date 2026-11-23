- [ ] 🔴 **A RULE WITNESSED ONLY BY A *DEFERRED* ERROR IS WITNESSED BY NOTHING —
      and one shipped guard was in exactly that state.** Filed 2026-08-23 by
      D-DEFFNKNIFE,
      [`docs/spec-basic-deffnknife.md`](../../docs/spec-basic-deffnknife.md) §4.
      `raise_error`'s `FN_FEND` reset had a comment in TWO files
      (`basic/interp.asm`, `sub/arrays.asm`) naming `o.errrestore` as *"the row
      that says so"*. Knife K-FE1 disabled the reset and `deffn-strict` stayed
      **0 of 69 divergent**: `X/0` is a DEFERRED FPERR *"realized at the
      statement boundary"* (`fp_runtime_error`'s own header), so the FN call
      RETURNS NORMALLY, `fn_leave` restores the frame, and `raise_error` runs
      with nothing stale to reset. ✅ **The instance is CLOSED** — `o.errfend18`
      / `o.errfend13` were measured on both references (`5 18` / `5 13`, and
      `2 18` / `2 13` under the knife), added to the row set (`deffn-strict` is
      now **0 of 71**), and both comments corrected.
      📏 **SCOUTED 2026-08-23**,
      [`docs/deferblind-scout-2026-08-23.md`](../../docs/deferblind-scout-2026-08-23.md),
      no ROM byte moved. **21 `penderr_set` sites; exactly ONE raises on the
      spot** (`str_heap_oom_error`), the other 20 return — so ERR 6/11/5/2/9/7/
      10/13 can EACH arrive deferred or immediate depending on the SITE, and
      🔴 **the ERR code a row expects carries NO information about whether that
      row can witness an ordering-sensitive guard.** The class was then stated
      checkably (*a cell meaning "we are inside X", cleared by X's normal exit,
      NOT cleared at the statement boundary, and READ outside X* — `exec_stmt`'s
      own `xor a / ld (PRDEST),a` is why PRDEST is safe by construction and
      FN_FEND was not) and **measured EMPTY for the FOR stack, the GOSUB stack
      and the string heap**: 27 of 27 readings agree across both references and
      zerobas. ✅ **And the instrument was CALIBRATED on the known positive** —
      the same 12 rows re-run under K-FE1 move `fn.imm` (`5`→`2`) and **nothing
      else**, so the nine zeros are a reading and not a silence.
      🔴 **STILL OPEN — THE DENOMINATOR IS THREE CONSTRUCTS.** 96 cells in
      `sysvars.inc` describe themselves as live/in-progress/pending; the
      "read outside X" filter leaves a short untested list, headed by
      **`TRAPSVC`** (incremented on trap dispatch, decremented ONLY by
      `ex_return`'s hook — so a handler left via `RESUME <line>` never
      re-enables its trap, and `TRAPSTK_MAX` is 6), then `FCH_ACTIVE`/`FCH_NUM`/
      `FCH_MODE` and `GFX_DFTOP`. ⚠️ **`TRAPSVC`'s trigger is a DIFFERENT one** —
      *RESUME out of a trap handler*, not deferred-vs-immediate — and both
      references would be expected to leak too, so it needs its own reference
      measurement. Use §4's shape: three ways (immediate / deferred / no fault)
      and prove the row can go red before believing a zero.
      ⚠️ `o.errrestore` looked like a *stronger* row than the two that
      replaced it, and nothing but a knife could tell.
      🔴 **`TRAPSVC` MEASURED 2026-08-26 — AND IT IS A LIVE DIVERGENCE WITH A
      CEILING OF SIX.**
      ([`scratchpad/trapsvc_depth.py`](../../scratchpad/trapsvc_depth.py),
      [`scratchpad/trapsvc_depth_screen.py`](../../scratchpad/trapsvc_depth_screen.py)).
      Same program on both machines: an `ON INTERVAL` handler that re-arms and
      leaves by `GOTO` — the leak form, which needs no fault at all.
      ```
      zerobas    dies after 6 leaked dispatches:  "Out of memory in 900"
      VG-8020    no error at all in the same window; still running
      control (handler RETURNs)   30 fires, err 0, done 1 — IDENTICAL on both
      ```
      🎯 **SIX IS `TRAPSTK_MAX`.** `check_traps` guards `cp TRAPSTK_MAX` and
      jumps to `gosub_stk_over` → ERR 7. The references have no `TRAPSTK`; they
      leak GOSUB frames, and that stack is far deeper.
      🔴 **AND THE FAILURE IS UNTRAPPABLE.** The message is *"Out of memory
      **in 900**"* — line 900 is the `ON ERROR` handler. The raise enters the
      handler, the handler needs a frame it cannot have, and the program stops
      dead. So `ON ERROR` does not merely fail to help; it is the line that gets
      blamed.
      ⚠️ **THE `141` FROM THE COUNTER RUN IS NOT QUOTED AS A COUNT.** That read
      came back with `err=115` and `done=76` beside it — neither a valid ERR nor
      a valid flag — so the whole $D000 window is untrustworthy on a program
      that never finished. The screen is the reading; "well past 6" is all the
      counter supports.
      ⚠️ **ONE REFERENCE.** `basic_probe_interval_trap` has only ever driven the
      VG-8020; pointing its `run()` at the CF-3300 returned an **all-$FF** window
      on every row, which the first cut printed as `fires=255 err=255 done=255`
      — garbage read as data. The probe now calls that an instrument fault.
      🎯 **SO THE FILED SHAPE HELD BUT THE TRIGGER WAS NARROWER THAN THE CLASS,
      AGAIN**: the item says *"RESUME out of a trap handler"*; a plain `GOTO`
      does it, with no error anywhere, and that is the form measured here
      [[trapsvc-slice]].
      💰 **NOT PRICED, AND THE FIX IS A SPEND.** Raising `TRAPSTK_MAX` costs
      3 B per slot of RAM; popping the record when a frame is abandoned costs
      main page-1 bytes. Both are budget decisions.
      🎚️ APPARATUS — unwitnessable guard
      🔁 **RULED (Joost, 2026-09-10): stays as classed** — not before TIERS 1–4 unless it
      blocks a keyword tier; still his call when it is picked.
      🔭 SCOUT-THEN-ASK — measured and isolated 2026-08-26; the FIX costs bytes, which is yours to spend.
