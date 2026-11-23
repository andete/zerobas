- [ ] ⚠️ **KEY / STRIG / SPRITE / STOP were NOT run against the D-TRAPSVC rows.**
      2026-08-23, [`docs/spec-basic-trapsvc.md`](../../docs/spec-basic-trapsvc.md) §7.
      `ON INTERVAL` is the only self-firing MSX1 trap, so the other four are
      covered by a **code** argument (they share `check_traps`, `ct_find`,
      `set_state` and `trap_return_check` verbatim; the index is a parameter),
      not by a measurement. The device-driven harnesses exist
      (`basic_probe_key_trap.py`, T2/T4 probes) if the argument is ever attacked.
      ✅ **THE CODE ARGUMENT IS NOW A MEASUREMENT — ON `SPRITE`, 2026-08-26**
      ([`scratchpad/clrtrapstk_sprite_probe.py`](../../scratchpad/clrtrapstk_sprite_probe.py),
      [`scratchpad/clrtrapstk_sprite.out`](../../scratchpad/clrtrapstk_sprite.out)).
      🎯 **THE `CLEAR`/`TRAPSTK` DEFECT MEASURED THE SAME DAY IS A DISCRIMINATOR
      FOR EXACTLY THIS CLAIM**: it lives in `trap_return_check`, the routine the
      argument says all five traps share verbatim. Replaying that 2×2 with
      `SPRITE` instead of `INTERVAL` puts the SAME cell live and leaves the other
      three agreeing at 1:
      ```
      case                        vg8020   zb
      CLEAR, still SERVICING           1  250 (SATURATED)   DIVERGENCE
      CLEAR, trap killed               1    1
      no-CLEAR, still SERVICING        1    1
      no-CLEAR (control)               1    1
      ```
      So the sharing is real where it matters, and the defect is **worse** here:
      `SPRITE` re-fires once per FRAME, so the re-enabled trap saturated the
      counter and **starved the program** — it never completed its second wait.
      ⚠️ **ON THAT ROW THE MECHANISM CELLS ARE UNWRITTEN, NOT ZERO.** `TRAPSVC` /
      `TRAPENA` print as `0` because the starved program never reached the lines
      that `POKE` them. The `INTERVAL` run is where those cells were actually
      read (`TRAPENA=1`); here the evidence is the fire count and the starvation.
      🔴 **AND `basic_probe_sprite_trap.py`'s HEADER IS STALE.** It says
      *"`ON SPRITE GOSUB` is unimplemented on the zerobas side (D-G7-4 left
      `SPRITE ON/OFF/STOP` a no-op)"*. It fires — `basic/sprtrap-body.inc` is
      included via `subromcall.asm`, `ZTI_SPRITE` is a live index, and the
      control rows show one fire on both machines. ~~Doc debt, filed not fixed.~~
      🟢 **THE D-G7-4 HALF WAS ALREADY FIXED ON 2026-08-26** — the probe's
      header carries the strike and the evidence. **This line was itself stale**,
      which is the class it describes, one level up.
      🔴 **AND READING IT FOUND A SECOND FALSIFIED CLAIM IN THE SAME HEADER**
      (2026-09-05): *"deliberately NOT yet wired to a `make` target, so the
      asserting gate `make sprite-trap-acceptance` still has to be built"*. That
      target **exists**, invokes **this file**, is collected by `make gates` in
      the EMULATOR tier, and ran green in 72 s in today's battery. The header had
      been wrong about its own status twice, in two different ways, and both were
      found by READING — nothing that runs can see a docstring.
      ➡️ ~~**STILL A CODE ARGUMENT FOR `KEY` / `STRIG` / `STOP`**~~ — those three need
      device input (key matrix, joystick, the STOP key), and the harnesses exist.
      `SPRITE` was taken first because a sprite collision is reachable from pure
      BASIC, so it needed no device at all. ~~**1 of 4 converted.**~~
      🟢 **`STOP` CONVERTED 2026-09-05 — 2 of 4 — AND IT DOES NOT REPRODUCE**
      ([`scratchpad/clrtrapstk_stop_probe.py`](../../scratchpad/clrtrapstk_stop_probe.py),
      [`.out`](../../scratchpad/clrtrapstk_stop.out)). Same 2×2, driven through
      `basic_probe_stop_trap.run()` (imported, not copied — a second copy would
      sit outside `make latch-check` and re-open the delivery race that gate
      exists for), with its tap length and `run_gap` inherited for its reasons:

          case                        vg8020   zb
          CLEAR, still SERVICING           1    1
          CLEAR, trap killed               1    1
          no-CLEAR, still SERVICING        1    1
          no-CLEAR (control)               1    1
          c.twofire POSITIVE CONTROL       2    2   🎯

      🔴 **AND THE FIRST RUN OF THIS SAID NOTHING WHILE LOOKING LIKE AGREEMENT.**
      Without the fifth row every cell read 1 — which is what the REFERENCE
      correctly reads in all four (a trap left SERVICING does not re-fire until
      `RETURN`), and also exactly what **a second tap that never landed** reads.
      Two causes, one number. The SPRITE replay never needed this guard because
      SPRITE re-fires per FRAME and its live cell SATURATED at 250, which nothing
      else produces [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
      `c.twofire` uses a handler that always `RETURN`s, so the trap is armed when
      the second tap arrives; **it reads 2 on both machines**, which is what makes
      the four 1s a reading.
      🎯 **SO THE CODE ARGUMENT'S PREDICTION IS NOT CONFIRMED FOR `STOP`.** SPRITE
      diverged in `CLEAR, still SERVICING` (1 vs 250); STOP agrees there. ⚠️ **The
      MECHANISM for that difference is NOT established and is deliberately not
      guessed at here** — one 2×2 supports "STOP is correct", not a cause
      [[a-mechanism-inferred-from-one-observation]]. What it does establish is
      that *"the index is a parameter, so all five behave alike"* is too strong:
      two verbs through the same routine gave different answers.
      🟢 **`STRIG` CONVERTED THE SAME DAY — 3 of 4 — AND IT AGREES TOO**
      ([`scratchpad/clrtrapstk_strig_probe.py`](../../scratchpad/clrtrapstk_strig_probe.py),
      [`.out`](../../scratchpad/clrtrapstk_strig.out)). Same 2×2 plus the same positive
      control, through `basic_probe_strig_trap.run()` (imported; trigger 0 IS the
      SPACE key, matrix row 8 bit 0). All four cells **1/1**, `c.twofire` **2/2**.
      📏 **SO THE SHAPE IS: SPRITE DIVERGES, STOP AND STRIG DO NOT.** The code
      argument predicted all four alike; three measured, and one of the three is
      the odd one out.
      🔴 **AND THE THREE RUNS MAY NOT BE MEASURING THE SAME THING — this bounds
      what "3 of 4" is worth.** SPRITE re-fires once per FRAME, so a trap left
      enabled fires with **no new event** and saturates at 250. `STOP` and
      `STRIG` fire once per EDGE, so their 2×2 can only detect a re-enable that
      survives until the **second tap**; a trap left enabled-but-unfired is
      invisible to them. Both read 1 where a re-enable would read 2, which rules
      out *that* failure — it does not rule out SPRITE's. ⚠️ **The MECHANISM for
      the SPRITE divergence is still NOT established and is deliberately not
      guessed at** [[a-mechanism-inferred-from-one-observation]].
      🟢 **`KEY` CONVERTED THE SAME DAY — 4 of 4, THE CONVERSION IS COMPLETE, AND
      IT AGREES** ([`scratchpad/clrtrapstk_key_probe.py`](../../scratchpad/clrtrapstk_key_probe.py),
      [`.out`](../../scratchpad/clrtrapstk_key.out)). Same 2×2, same positive control,
      through `basic_probe_key_trap.run()` (imported; F1 is matrix row 6 bit 5).
      All four cells **1/1**, `c.twofire` **2/2**. The windows are
      ITERATION-bounded, never timed — `TIME` does not exist on zerobas and the
      reference is ~7× faster.
      🎯 **THE ARGUMENT IS NOW A MEASUREMENT ON ALL FOUR, AND IT DOES NOT HOLD AS
      STATED.** *"They share `check_traps`, `ct_find`, `set_state` and
      `trap_return_check` verbatim; the index is a parameter"* predicted four
      identical answers. Measured: **`SPRITE` diverges (1 vs 250); `KEY`, `STOP`
      and `STRIG` do not.** One of four.
      🔴 **AND THE BOUND ON THAT RESULT IS THE PART TO CARRY FORWARD.** `SPRITE`
      re-fires once per FRAME, so a trap left enabled fires with **no new event**
      and saturates. `KEY` / `STOP` / `STRIG` fire once per EDGE, so their 2×2
      detects only a re-enable that survives to the **second tap** — a trap left
      enabled-but-unfired is invisible to all three. Their `1`s rule out THAT
      failure; they do not rule out SPRITE's. ⚠️ **So "3 agree" is not "3 are
      clean", and the MECHANISM for SPRITE's divergence remains unestablished and
      deliberately unguessed** [[a-mechanism-inferred-from-one-observation]].
      ➡️ **WHAT KEEPS THIS ITEM OPEN IS NO LONGER THE CONVERSION** — that is done,
      4 of 4 — **but the unexplained SPRITE cell**, and the fact that no
      edge-fired 2×2 can decide whether the other three share it in a form their
      event source cannot show. A discriminating instrument for that would have
      to observe the trap STATE, not the fire count.
      ✅ **BUILT AND RUN 2026-09-06 (D-TRAPSTATE) —
      [`scratchpad/trapstate_probe.py`](../../scratchpad/trapstate_probe.py). THE
      ANSWER IS THAT `KEY` AND `STRIG` ARE CLEAN AT THE STATE LEVEL, NOT MERELY
      QUIET AT THE COUNT LEVEL.** Reading `ZTRAP`'s per-entry state byte plus
      `TRAPENA`/`TRAPSVC` right after the `CLEAR`, against a no-`CLEAR` control
      and a `returned` negative control:
      | verb | case | entry | state | ENA | SVC |
      |---|---|---|---|---|---|
      | `KEY` | CLEAR | — | all OFF | 0 | 0 |
      | `KEY` | control | e17 | SERVICING | 0 | 1 |
      | `KEY` | returned | e17 | ON | 1 | 0 |
      | `STRIG` | CLEAR | — | all OFF | 0 | 0 |
      | `STRIG` | control | e3 | SERVICING | 0 | 1 |
      | `STRIG` | returned | e3 | ON | 1 | 0 |
      🎯 **`CLEAR` WIPES THE ENTRY TO OFF AND ZEROES BOTH COUNTERS**, and all six
      rows are internally consistent (ENA/SVC agree with the table). So their
      `1`s in the 2×2 are not an event source hiding a wrong state — the state
      is right. SPRITE re-fires 250× through the same `CLEAR`, so its entry is
      NOT left OFF: **the verbs differ at the level of STATE, and the shared-code
      argument is refuted with a reading rather than with a count.**
      ⚠️ **THE MECHANISM FOR SPRITE IS STILL NOT ESTABLISHED AND STILL NOT
      GUESSED AT** [[a-mechanism-inferred-from-one-observation]]. Its state
      cannot be read the same way: the re-enabled trap fires once per frame and
      the program starves before any reporting line, which is the same
      starvation that left its 2×2 mechanism cells unwritten.
      ⚠️ **`STOP` IS OUT OF SCOPE FOR THE INSTRUMENT, AND THE REASON IS THE
      CHANNEL, NOT THE VERB** — `basic_probe_stop_trap`'s capture reads exactly
      `FLAG`/`RAN`/`DONE`, and its `DONE` is set by an INJECTED direct POKE, so
      there is no cell to put a state byte in and nothing to gate it on. Named
      rather than quietly dropped [[an-unnamed-outcome-reads-as-no-outcome]].
      🔴 **AND THE FIRST THREE RUNS MEASURED NOTHING FOR `STRIG` WHILE PRINTING
      A PLAUSIBLE TABLE.** `basic_probe_strig_trap`'s capture emitted no `aux`
      cell, so `r.get("aux", 255)` supplied the sentinel and **the DEFAULT became
      the data** — it decoded to "no live entry" on every STRIG row, and a
      consistency check then reported *"TRAPSVC=1 but the table shows no live
      entry — counter and table DISAGREE"* off a value no machine produced. I was
      one step from filing that as a ROM defect.
      🎯 **WHAT CAUGHT IT WAS AN IMPOSSIBLE VALUE, NOT A SUSPICION.** A
      `--direct` cross-check packs `idx*8 + state`, whose maximum is 31; 255
      cannot occur there, so seeing 255 proved the CHANNEL absent rather than the
      machine odd. The fix is additive (one emitted cell), and the probe now
      **REFUSES** when a row comes back with no `aux` key instead of defaulting
      [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
      🔴 **A THIRD FINDING, IN THE SOURCE**: this run flagged `KEY(1) ON` arming
      **entry 17** as unexpected. The entry was RIGHT — the KEY band is laid out
      REVERSED, KEY 10 at `ZTI_KEY1` and KEY 1 at `ZTI_KEY1+9`
      ([`basic/keytrap.asm:121`](../../basic/keytrap.asm:121),
      [`basic/program.asm:2924`](../../basic/program.asm:2924), three `ld a,ZTI_KEY1+9`
      sites) — and [`basic/sysvars.inc`](../../basic/sysvars.inc:1200)'s *"KEY n → 7+n,
      n=1..10"* was the wrong half of a two-file disagreement
      [[two-sections-of-one-doc-disagreed]]. Corrected in place beside the
      original, 0 bytes.
      ✅ **THE SPRITE STATE IS READ AT LAST — D-SPRSTATE, 2026-09-10 — AND IT
      REFUTES THIS ENTRY'S OWN INFERENCE**
      ([`scratchpad/spritestate_probe.py`](../../scratchpad/spritestate_probe.py),
      [`.out`](../../scratchpad/spritestate.out)).
      🎯 **STOP ASKING THE GUEST.** D-TRAPSTATE read `ZTRAP` with BASIC `PEEK`s,
      which needs the program to reach a reporting line — exactly what the
      starvation prevents, and exactly why this was left unmeasured. openMSX's
      DEBUGGER has no such problem: a self-rescheduling `after time` proc dumps
      all 18 entries plus `TRAPENA`/`TRAPSVC` on the EMULATED clock, no matter
      what the guest is doing. **300 samples per case, to emulated 724 s.**
      | case | SPRITE entry | TRAPENA | TRAPSVC |
      |---|---|---|---|
      | `CLEAR`, still SERVICING | **OFF** | 0 | 0 |
      | no-`CLEAR` (control) | **SERVICING+PEND** | 0 | 1 |
      | `CLEAR`, trap killed | OFF | 0 | 0 |
      🔴 **SO "ITS ENTRY IS NOT LEFT OFF" IS FALSE.** This entry inferred that
      from the fire count — *"SPRITE re-fires 250× through the same `CLEAR`, so
      its entry is NOT left OFF: the verbs differ at the level of STATE"* — and
      flagged it as an inference. Measured, the entry **is** wiped to OFF with
      both counters zero, which is precisely what D-TRAPSTATE read for `KEY` and
      `STRIG`. The three verbs agree at the state level; the divergence is
      somewhere else entirely [[a-mechanism-inferred-from-one-observation]].
      🟢 **THE CONTROL IS WHAT MAKES THAT A READING.** Without `CLEAR` the same
      sampler sees `SERVICING+PEND` with `TRAPSVC=1` at the same instants, so an
      `OFF` is the machine's answer and not a sampler that cannot see a live
      entry — the `aux`-sentinel trap D-TRAPSTATE fell into one level along.
      ⚠️ **BOUNDED: THE TRANSITION ITSELF WAS NOT OBSERVED.** The first sample
      lands after the program is already underway (throttle off), so what is read
      is the SETTLED state, not the `SERVICING` → `OFF` edge. That is enough to
      refute "not left OFF" and not enough to time the wipe.
      ➡️ **WHAT REMAINS IS NARROWER THAN IT WAS**: the 250 fires happen with the
      entry OFF and both counters zero, so the next question is what re-arms or
      re-dispatches SPRITE without going through the entry — a question for the
      CODE, deliberately not guessed here.
      🔬 **THREE APPARATUS FAULTS ON THE WAY, EACH CAUGHT BY A REFUSAL RATHER
      THAN BY ME.** (1) Driving it through `omsx_repl.run_cases` with a
      hand-picked `step` got *"boot-per-case delivery was mangled; nothing was
      measured"* — the machine stored 201, 305, 4010 where 20, 30, 40 were typed.
      Fixed by IMPORTING `basic_probe_sprite_trap`'s `_INJECT_TCL` / `_schedule`
      / `_launch` rather than inventing timing. (2) `_launch` **owns its
      `out_path` and `os.unlink`s it**, so handing it the dump path deleted the
      dump and every row read `NO DUMP` — indistinguishable from Tcl that never
      ran. (3) Diagnosed only by running the same Tcl standalone **with stderr
      visible** (`_launch` sends both streams to `DEVNULL`), where it wrote a
      perfect table — which located the fault in the plumbing, not the script.
      🔴 **CORRECTION, SAME DAY, BEFORE ANY OF THE ABOVE IS BUILT ON: THE SPRITE
      DIVERGENCE NO LONGER EXISTS.** Adding the handler's fire counter `$D000`
      beside the state showed **fires = 1 in ALL THREE cases**, never advancing —
      so the run whose state I had just tabulated was a run in which the defect
      did not occur. Re-running the ORIGINAL 2×2 settles it
      ([`scratchpad/clrtrapstk_sprite_recheck.out`](../../scratchpad/clrtrapstk_sprite_recheck.out)):
      **`CLEAR, still SERVICING` reads 1 vs 1, and the whole 2×2 reports 0
      divergences**, where 2026-08-26 read **1 vs 250 (SATURATED)**.
      🎯 **SO THE STATE TABLE WAS RIGHT AND MY FRAMING OF IT WAS WRONG.** I wrote
      *"the divergence is somewhere else entirely"* and *"the next question is
      what re-dispatches SPRITE"*. There is no divergence and nothing to
      re-dispatch: SPRITE now behaves like `KEY` and `STRIG` at both the count and
      the state level, which is why the entry read OFF with both counters zero.
      **`7d0a6f3f`'s conclusion is withdrawn; its measurement stands.**
      ⚠️ **AND THE ENTRY CARRIED "SPRITE DIVERGES" AS A LIVE FACT FOR FIFTEEN
      DAYS** — through every ROM change since — while the whole shape of this
      block ("SPRITE diverges, STOP and STRIG do not", "one of four") rested on
      it. A filed divergence rots exactly like a wall reading
      [[a-ranked-candidate-rots-like-a-wall]].
      🔴 **AND IT WAS STRUCTURALLY INVISIBLE, WHICH IS THE FINDING WORTH KEEPING.**
      `filed_row_sweep`'s corpus comes from `CITE`, which matches
      `scratchpad/<name>_probe.py` — and **four of the five `clrtrapstk_*.py` do
      not end in `_probe`**, so the sweep has never run them and could never
      report their rows stale. Measured: **21 scratch files carry a divergence
      verdict in code, are cited by an open TODO item, and lie outside the
      sweep's reach**; five of those are `*_knives.py` (which move rows on
      purpose), so ~16 are instruments nothing re-runs.
      🎯 **THIS IS THE SAME REGEX BLIND SPOT D-PINGATE FOUND ON THE PIN SIDE
      TONIGHT** (`basic_probe_nodisk`, unnameable by the orphan scan) — the other
      half of one bug: the pin side is now gated, the PROBE side is not.
      ✅ **DONE 2026-09-10 (D-CLRTRAPNAME): THE FOUR ARE RENAMED AND IN THE
      CORPUS.** `clrtrapstk_{sprite,key,stop,strig}.py` →
      `clrtrapstk_{…}_probe.py` via `git mv`, with all five reference sites
      updated (this file, `spritestate_probe.py`'s import,
      `clrtrapstk_stop_probe.py`'s own header, `basic_probe_trapsvc.py`,
      `basic_probe_sprite_trap.py`). **Sweep corpus 53 → 57**;
      `check_citation_paths` reads 611 cited paths, all resolving.
      🟢 **AND THE SWEEP THEN ADJUDICATED THEM: all four `clean`, 0 UNFILED, 0 NO
      LONGER DIVERGING** ([`.out`](../../scratchpad/filedrow_clrtrapstk.out)) — which is
      the point of the rename and not a formality: SPRITE's closure is now
      something an instrument reports, rather than something a person has to
      remember to re-run.
      💰 **AND IT COSTS ALMOST NOTHING, MEASURED** — the four run in 6–11 s each
      in the sweep, and `clrtrapstk_sprite_probe.py` alone times at **4.5 s** for
      eight boots. That is consistent with tonight's own D-STALLRATE reading
      (openMSX unthrottled at ~400×, an ordinary case living 0.9 wall seconds),
      and it settles the choice: **renaming was right, and the cost objection to a
      wider corpus does not apply to probes this cheap.**
      ⚠️ **One captured gate-run log (`ctrlc_gates2.out`, 2026-09-07) still names
      the OLD path, deliberately**: editing evidence to match a later rename would
      falsify the record. 🔴 It is named WITHOUT its `scratchpad/` prefix on
      purpose — `check_citation_paths` treats a prefixed path as a CITATION and
      requires it to resolve in a fresh clone, and that log is untracked and is
      not evidence for anything here. Committing an unrelated 6.5 KB log to
      satisfy a name-drop would be the wrong fix; the gate was right to ask.
      🔴 **AND THE BULK RENAME ATE THE SENTENCE THAT PROPOSED IT.** The script
      that updated the five reference sites rewrote this very paragraph —
      *"renaming `clrtrapstk_sprite.py` → `clrtrapstk_sprite_probe.py`"* became
      *"renaming X → X"*, a sentence saying nothing. The follow-up edit then
      asserted on the ORIGINAL wording, fired, and wrote nothing. **The assertion
      is what caught it**; a `replace()` with no count check would have left the
      nonsense in place and reported success
      [[an-unnamed-outcome-reads-as-no-outcome]].
      ➡️ **The class is not empty**: ~16 other cited, divergence-emitting scratch
      files remain outside the sweep by name (5 more are knives, which move rows
      on purpose and do not belong in it). This slice took the four carrying a
      LIVE filed finding; the rest want the same treatment, file by file, with the
      same adjudication run after each.
      🎚️ APPARATUS — trap-row coverage
      🤖 AUTONOMOUS — the conversion is 4 of 4, the state question is answered, and
      the divergence that kept this open is closed. What remains is the corpus
      blind spot above.
