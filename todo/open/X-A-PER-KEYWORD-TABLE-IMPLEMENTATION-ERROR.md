- [ ] 🙋 **A PER-KEYWORD TABLE (implementation · error handling · performance) —
      PARKED BY JOOST 2026-09-10, WITH THE FEASIBILITY MEASURED.** Asked for as
      three columns over every BASIC keyword. The row denominator is solid —
      **155 entries in [`basic/kwtable.inc`](../../basic/kwtable.inc)** plus the ~8 the
      reference tokenises and zerobas does not — but the three columns are not
      remotely equal, and a three-column table invites reading them as if they
      were [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
      🔴 **THREE NAIVE VERSIONS OF THE IMPLEMENTATION COLUMN WERE BUILT AND ALL
      THREE COLLAPSED, IN THE SAME DIRECTION — 100%:**
      | attempt | result | why it is wrong |
      |---|---|---|
      | grep probe sources for the keyword | 155/155 | `AND` scored 91 — an English word in DOCSTRINGS |
      | typed BASIC literals only (`ast`, docstrings excluded) | 155/155 | still 100% |
      | exclude the dominant suite | 148/155 | `basic_probe_lnblank.py` **types all 155 keywords**, for blank-line handling, not semantics |
      🎯 **SO "IS THIS KEYWORD TYPED SOMEWHERE" IS ~100% AND MEANS NOTHING.** The
      column anyone actually wants is *"is this keyword's behaviour
      DIFFERENTIALLY SCORED, by a row that goes red if it breaks"* — and that
      needs to know **which row is ABOUT which keyword**, which nothing records.
      ➡️ **THE UNLOCK IS A ONE-LINE `subject:` TAG PER GATE ROW**, naming the
      keyword the row exists to test. Mechanical, bounded, and it would sharpen
      the filed-row sweep for free. `kwsweep` is a partial head start: 55 rows,
      **37 scored**, 18 crunch-only.
      📏 **COLUMN 2 CAN BE COVERAGE, NEVER COMPLETENESS.** **70/155 (45%)** of
      keywords are typed inside an error-scoped suite; `missing-acceptance` covers
      21 verbs and the rest (`lineerr`, `penderr`, `onerr0`) are CROSS-CUTTING,
      not per-verb. Nobody has enumerated the error SURFACE of a keyword, so
      "how complete" has no denominator to be a fraction of.
      🔴 **COLUMN 3 HAS NO DATA AT ALL.** `interpspeed_probe` measures **8
      synthetic rows** (FOR/GOTO/WHILE/arith/str), not keywords, and the only
      filed figure is a whole-interpreter band of 2.5–3.8×. A per-keyword accuracy
      column needs a new benchmark harness AND a decision about what "accurate"
      means (cycles against the reference? wall time? both machines?). That is an
      arc, not a slice — and it is the column with the least behind it today.
      🎚️ STANDING — the tier framework's denominator (see the 🎚️ legend at the top of this section)
      ~~🙋 **NEEDS-JOOST** — parked at his request on 2026-09-10. The recommendation~~ (re-marked 2026-09-10, see below)
      on the table when it was parked: **build column 1 alone**, via the `subject:`
      tag, and ship one column that is true rather than three where two are
      decoration.
      🎚️ **UNPARKED IN SPIRIT 2026-09-10 — THIS TABLE IS THE PRIORITY TIERS'
      DENOMINATOR.** Joost's five tiers (legend at the top of this section) are
      per keyword, and the three columns asked for here map onto them almost
      exactly: column 1 = TIERS 1+3+5, column 3 = TIERS 2+4. The steering he
      asked for cannot pick anything without a per-keyword row to pick FROM — the
      loop drifted into TIER 5 and apparatus precisely because the queue had no
      TIER 1–3 rows in it. What he has approved so far: recording the tiers and
      tagging every open item (done). What is still his call: **(c)** building
      column 1 via the `subject:` tag and making it the loop's pick list, TIER 1
      first, `LOF` −256 as the first row off it.
      🎯 **RULED (Joost, 2026-09-10): build it — step (c) is approved.** Column 1 via a
      `subject:` tag per gate row, over the 155-entry `kwtable.inc` denominator
      plus the missing keywords; it becomes the loop's pick list, TIER 1 first.
      The line/screen editor is on that list by his instruction.
      🔴 **D-KWCOVERFLOOR (2026-09-13): `make kwcover` RODE A SKIPPED BATTERY AND
      THE REPORT PRINTED A CONFIDENT, FALSE TABLE.** The capture exists only while
      the battery's 88 EMULATOR targets run, and a normal `make gates` skips those
      when the ROMs and probe sources are byte-identical to the last green run —
      which they were. It collected **754 typed lines from 3 suites** and reported
      `EXERCISED 153 / UNEXERCISED 6`, naming `CONT` `LOAD` `NAME` `PAINT` `PLAY`
      `VAL` as typed by nothing in the battery. **A full run types all six.**
      | | typed lines | suites | verdict |
      |---|---|---|---|
      | the skipped run | 754 | 3 | `UNEXERCISED 6` — every one false |
      | the full run, same day | **46 813** | **83** | `UNEXERCISED 0` |
      ➡️ **FIXED BOTH ENDS**: the `kwcover` target now forces `gates-full`, and
      `tools/kwcover.py` **REFUSES** below a 40-suite floor with "NOTHING WAS
      MEASURED — do not read a keyword list from this run" instead of printing one.
      The refusal was verified against the exact capture that fooled it.
      ⚠️ **THE ENTRY THAT BUILT THIS CAPTURE SAID ITS STRENGTH WAS THAT IT "RIDES ON
      A NORMAL BATTERY RUN"** — the question "which keywords does the battery run?"
      answered by the battery running rather than by reading the probes. That is
      still true and still the right design; what it missed is that a battery is
      allowed to DECLINE to run, and a capture with no producer looks exactly like a
      measurement with a small answer
      [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
      🟢 **STEP (c) HAS ITS DENOMINATOR AT LAST — MEASURED, NOT SCANNED (D-KWCOVER,
      2026-09-11, [`docs/spec-basic-kwcover.md`](../../docs/spec-basic-kwcover.md),
      `make kwcover`).** Joost: *"given that we have so many keywords still at 'no
      known gap' shouldn't we identify their status first before picking up new
      work?"* The capture rides on a normal battery run — `omsx_repl.run_cases`,
      the one chokepoint every probe types through, appends each typed line tagged
      with its suite — so the question "which keywords does the battery actually
      run?" is answered by the battery running, not by reading the probes.
      **46 193 typed lines, 82 emulator suites, battery 126/126 green:**
          typed by SOMETHING                          **159 / 159**
          typed by a BEHAVIOURAL suite                **157** (`lnblank-acceptance` sweeps all 159 by design)
          sweep-only                                  **2**  — `BSAVE` `CALL`
          THIN (0 or 1 behavioural suite)             **27** — the risk list below
      `ATN ATTR$ BASE BSAVE CALL CLOAD CMD COLOR COS CSAVE CSNG CVD DELETE DSKF
      FIX GET INKEY$ INP IPL LOG PAD RESTORE SET SGN TAN VDP VPOKE`
      🎯 **SO "NO KNOWN GAP" NEVER MEANT "NOTHING RUNS IT"** — it meant no row is
      known to SCORE it, and the gap is 27 keywords, not 105. Several of the thin
      rows are visibly APPARATUS rather than subject: `VPOKE` appears only as the
      screen editor's setup line, `GET` only inside a `LOC` readout, `PAD` only in
      a blank-sweep line.
      🔴 **THREE SOURCE SCANS CAME FIRST AND ALL THREE WERE WRONG** — matching the
      probes' Python strings for BASIC scored English prose (`AND` "exercised by
      125 suites", an EMPTY unexercised set), and tightening it then LOST real rows
      (`KILL "A.BAS"` keeps no token once its literal is stripped; an English
      word-boundary rule loses `FORI=0TO39:VPOKE160+I,39:NEXT`, because MSX needs
      no spaces). Each returned a plausible table
      [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
      ➡️ **NEXT, AND NOW AFFORDABLE:** exercised ≠ verified. The capture says which
      suites to re-run per keyword, so a handler can be disabled by patching the
      BUILT ROM (seconds, no rebuild) and only its 1–4 suites re-run; keywords with
      disjoint suite sets can be knifed in the same ROM. A keyword whose handler
      can be disabled with the battery still green is BLIND, and that is the row
      list [[gateblind-slice]]. Spec §2.
      🤖 AUTONOMOUS — the instrument is built and the list is measured.
      🤖 AUTONOMOUS — the denominator is MEASURED now (D-KWCOVER); the subject tags are the remainder.
