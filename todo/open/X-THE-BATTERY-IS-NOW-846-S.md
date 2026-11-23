- [ ] 🐌 **THE BATTERY IS NOW 846 s AND EACH EMULATOR UNIT PAYS ITS OWN BOOT —
      COLLAPSE SUITES THAT SHARE A MACHINE INTO ONE RUN.** Joost's suggestion,
      filed 2026-09-01 with the number that motivates it: D-COLLECTALL took the
      battery from **49 units / 450 s to 92 units / 846 s**. Nothing is wasted —
      every added unit measures something real and 92/92 are green — but the
      marginal cost is dominated by **per-unit openMSX boots**, not by rows.
      📏 **64 EMULATOR UNITS.** Individual probes already batch their cases
      (`omsx_repl.run_cases(..., batch=True)`), so the win left is one level up:
      several SUITES that want the same machine and the same reset sharing a
      single boot.
      ⚠️ **THE OBSTACLE IS STATE, AND IT IS THE REASON THIS IS NOT FREE.** Some
      suites boot per case ON PURPOSE — D-EDITVERB's printer-log deltas and
      D-LPTVERB's accumulated `LPOS` state both say so in their headers — and
      D-EDITVERB records the exact failure mode: a shared log where one case's
      capture becomes a whole log and every later delta is silently wrong "in
      the direction of a plausible-looking divergence".
      ➡️ So the shape is a per-suite OPT-IN, not a blanket change: a suite
      declares "machine M, reset R, no cross-case state" and the runner packs
      those together. 🔴 **And it needs the control D-EDITVERB's note implies —
      a batched suite must produce the SAME rows as it did unbatched, checked
      once per suite when it opts in.**
      🎚️ APPARATUS — battery wall time
      🤖 AUTONOMOUS — a gate settles it, and the before/after row sets are the
      oracle.
      🔴 **RE-MEASURED 2026-09-01 (D-BATCH1) AND THE PREMISE ABOVE IS WRONG.**
      "The marginal cost is per-unit openMSX boots, so share a boot across
      SUITES" — no. `run_cases` already defaults to `batch=True`, **one boot for
      a whole matrix**, so a batched suite boots ONCE and sharing across suites
      would save ~0.5 s each.
      🎯 **THE COST IS BOOT-PER-CASE WITHIN A SUITE.** `batch=False` — described
      in `run_cases`'s own docstring as "the historical default" — is passed by
      **35 of the 60 emulator probes**, and it is the battery's dominant cost.
      **30 of those 35 carry no reason within 25 lines of the call** (a crude
      scan: a candidate list, not a verdict).
      📏 **PROVED ON ONE: `strparen-acceptance` 35 s → 5 s (7x), 16/16 rows still
      matching their references**, verified by running the matrix BOTH ways and
      diffing every row (0/16 differ) before flipping it.
      🔴 **AND THE GENERIC CONTROL WAS BUILT AND WITHDRAWN — IT WAS UNSOUND.** A
      `$ZB_BATCH=0` switch at the `run_cases` chokepoint cannot reproduce the old
      behaviour, because **`reset` lives in different places in the two modes**:
      the probe prepends it per case for `batch=False`, the harness injects it
      for `batch=True`. Forcing the other mode from outside yields a THIRD
      behaviour (no reset, or two). Its first run said `rc 0 vs 2` and that was
      the instrument, not the suite.
      ➡️ **So the remaining work has a PREREQUISITE nobody had named**: make
      `run_cases` own `reset` in BOTH modes, and the both-ways diff becomes a
      one-command control for all 30 candidates. Until then each conversion needs
      its own hand-built comparison, which is what this one got.
      ✅ **PREREQUISITE DONE 2026-09-01 (D-BATCH2), AND THE CONTROL EXISTS:
      `python3 scratchpad/batchcheck.py <make-target>`.** `_run_cases_impl`'s
      boot-per-case branch passed `reset=()`; it now passes the caller's `reset`,
      so a mode forced from outside is FAITHFUL instead of a third behaviour.
      🔴 **THAT ONE-LINE CHANGE HAD A 69-SITE BLAST RADIUS, AND A PROBE CAUGHT
      IT IMMEDIATELY.** `banner-acceptance` went red on the first spot-check: its
      subject IS the untouched boot screen, and the now-injected default `CLS`
      wiped the header it reads — *"the marker printed but 2 header line(s) are
      GONE ... no other gate in this tree would have noticed"*. The resets are
      all idempotent (`NEW`/`CLS`/`SCREEN 0`), but idempotent is not the same as
      HARMLESS when the screen is the subject.
      ➡️ Fixed by making the implicit explicit: **69 sites in 33 probes** now
      pass `reset=()` where they were relying on the mode's default. Behaviour-
      preserving by construction, and it means every probe now DECLARES its reset
      instead of inheriting one that differed by mode. 92/92 green after the
      sweep.
      🟢 **AND THE CONTROL DISCRIMINATES, WHICH IS THE ONLY THING THAT MAKES IT
      WORTH HAVING**: `runtail` 22/22 rows identical → CONVERTIBLE; `lptverb`
      rows DIFFER, and the difference is the exact accumulation D-EDITVERB
      predicted — the batched printer log reads
      `CTL\r\nX\r\n 5 \r\n-5 \r\nAB\r\nA B\r\n` where boot-per-case
      reads `A B\r\n`.
      🔴 **BOTH MODES REPORTED `ok` AND rc=0.** The suite PASSES while measuring
      a running total, so exit status could never have caught it — only the row
      diff does. That is what "silently wrong in the direction of a plausible-
      looking divergence" looks like when you finally point an instrument at it.
      🔴 **AND THE CONTROL'S FIRST SWEEP WAS A FALSE POSITIVE — GUARDED
      2026-09-01 (D-BATCH3).** It reported `screenerr`, `tmfp`, `stmtpend` and
      `penderr` all **CONVERTIBLE**, having compared two IDENTICAL runs: those
      probes loop in PYTHON and call `run_cases` once per case, so forcing
      `batch=True` on a ONE-CASE matrix batches nothing. Both modes booted per
      case, every row matched, and **the only tell was a 1.0x "speedup"**
      [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
      ➡️ `run_cases` now records the matrix width (`$ZB_BATCH_STAT`) and
      `batchcheck` **REFUSES with `NOT TESTED`** when the widest matrix a suite
      ever handed it is < 2, naming the remedy. Verified in all three
      directions: `strparen` CONVERTIBLE (4.3x, 16-case matrix), `lptverb`
      ROW(S) DIFFER (16-case, real state), `tmfp` NOT TESTED (1-case).
      📏 **SO THE REMAINING WORK IS BIGGER THAN "RUN A COMMAND 29 TIMES"**, and
      that is the useful part of this pass: **25 of the 35 boot-per-case probes
      call `run_cases` inside a for-loop** and need a `run_side` restructure
      before the control can say anything at all; only **10** hand it a
      multi-case list, and 3 of those are now judged (strparen converted,
      lptverb refused, runtail cleared).
      ✅ **THE TESTABLE SET IS NOW FULLY JUDGED (2026-09-01, D-BATCH4).** All
      ten multi-case candidates run through the control:
      | verdict | suites |
      |---|---|
      | **CONVERTIBLE → converted** | `strparen` (4.3x), `dskmsg` (4.6x), `msgexact` (2.2x), `runtail` (1.6x) |
      | **must stay boot-per-case, reason now IN THE SOURCE** | `lptverb`, `castail`, `editverb` |
      | **NOT TESTED (matrix=1, needs a restructure first)** | `banner`, `cassave` |
      | not run (no battery target) | `bload_fcb` |
      📏 Measured effect: `dskmsg` 11 s → 3 s, `runtail` 10 s → 2 s,
      `msgexact` → 2 s.
      🔴 **AND THE STATIC HEURISTIC OVER-COUNTED**: it called `banner` and
      `cassave` testable; the control's matrix-width guard says they are
      matrix=1. The guard is the authority, the grep was an estimate — worth
      remembering before trusting the "25 need restructuring" figure, which comes
      from the SAME grep.
      🟢 **EVERY REFUSAL NOW SAYS WHY, IN THE SOURCE**, which is what the item
      asked for: `lptverb`'s accumulating printer log (with the measured
      before/after strings), `castail`'s rc 2-vs-0, and `editverb`'s
      header-warning now backed by a measurement.
      🔴 **AND THE FOUR SLOWEST FOR-LOOP PROBES SHARE ONE BLOCKER, WHICH TURNED
      OUT TO BE A DEFECT (2026-09-01, D-BATCH5).** `screenerr`, `stmtpend`,
      `penderr` and `tmfp` all carry the same comment: *"A FRESH `so` PER CALL
      ... every boot indexes from 0, so one dict reused across the loop would
      hold a single entry and the tally would silently under-count."* **Seven
      probes use `probe_signal`; all seven are boot-per-case; none is batched.**
      🎯 **THE COMMENT IS A STATEMENT ABOUT `batch=False`, AND BATCHING FIXES
      WHAT IT FEARS.** `settle_out` keys by the case index the emulator emits, so
      a batched matrix of N cases writes N DISTINCT keys into ONE dict. The
      per-call dict was a boot-per-case workaround, not a barrier.
      📏 **`tmfp` CONVERTED AND MEASURED: 61.7 s → 15.1 s (4.1x), 58 of 59 rows
      IDENTICAL.** The one differing row is the instrument's own tally —
      **`capture-on-signal: 123 on signal` batched vs `3` boot-per-case.** 41
      signal cases x 3 sides = 123, so the batched figure is the arithmetically
      consistent one and **boot-per-case has been under-counting 40x**: exactly
      the failure the comment warned a shared dict would cause, happening all
      along in the mode it thought was safe.
      ⚠️ The tally is report-only, so no verdict was ever wrong — but it is the
      detector that reports FALLBACKS, so **40 of every 41 fallbacks were
      invisible**. The other six `probe_signal` probes are presumed to carry the
      same under-count; it is not measured for them yet.
      ⚠️ The conversion splits the matrix by `kind == "t"`, because
      `probe_signal.kwargs` is a whole-CALL setting and a mixed matrix would
      apply sentinel capture to the non-signal cases too. The disk is now one per
      GROUP, not per case — a real reduction in isolation, which is why this only
      lands with the control green.
      📏 **TWO MORE JUDGED 2026-09-02 (D-BATCH6), AND THEY SPLIT — WHICH IS THE
      POINT.** `screenerr` and `penderr` have **BYTE-IDENTICAL** `run_side`
      bodies (modulo the disk name), so the same transformation applied to both:
      | suite | verdict | |
      |---|---|---|
      | `penderr` | **CONVERTED** | 3.7x; the ONLY differing row is the tally, 165 vs 3 |
      | `screenerr` | **REVERTED** | a REAL leak: `a.sprskip` reads ` 99 , 2 ` batched, ` 0 , 2 ` fresh |
      🔴 **AND THE LEAKING ROW STILL SAYS `ok` IN BOTH MODES**, because all three
      sides agree on the polluted value too. Cross-side agreement cannot see it;
      only the both-ways diff can
      [[a-case-that-agrees-can-agree-for-the-wrong-reason]]. The file's own
      DENOMINATOR names sprite-size persistence as something it does NOT sweep —
      batching would have swept it accidentally and silently.
      🎯 **SAME SHAPE, DIFFERENT VERDICT: run the control on EACH ONE.** Two
      probes with identical bodies came out opposite ways, so an argument by
      analogy ("its twin converted, so this one will") would have been wrong half
      the time. `screenerr`'s reason is now in its own docstring.
      📏 **THE `probe_signal` FAMILY IS NOW SETTLED (2026-09-02, D-BATCH7).**
      | suite | verdict | |
      |---|---|---|
      | `tmfp` | CONVERTED | 4.1x (61.7 s → 15.1 s) |
      | `penderr` | CONVERTED | 3.7x (~170 s → 22 s) |
      | `stmtpend` | CONVERTED | 3.8x (73.5 s → 19.5 s); per-case `NO_CLS_RESET` variation preserved |
      | `screenerr` | REVERTED | `a.sprskip` leaks: ` 99 , 2 ` vs ` 0 , 2 ` |
      | **`lineerr`** | **REVERTED** | **30 of 220 rows leak** |
      | `graphics` | not attempted | 44 separate `run_cases` sites, a different job |
      | `deffn` | not attempted | imported by a dozen probes; wide blast radius |
      🔴 **THE BATTERY'S OWN PER-UNIT TIMES ARE INFLATED BY CONTENTION, AND
      THIS ITEM HAS BEEN PICKING TARGETS FROM THEM (2026-09-07, D-BATCHWALL).**
      `ctllim-acceptance` reads **411 s** in the battery's unit list and **156.6 s
      run alone** (`/usr/bin/time -p make ctllim-acceptance`, `CTLLIM: PASS`,
      3 rows, 0 red) — a 2.6x gap for that unit, because ~78 emulator units share
      ~8 workers and each one is measured while the others compete for CPU.
      ⚠️ **2.6x IS ONE UNIT'S FACTOR, NOT A GLOBAL ONE** — no other unit was
      timed both ways, so nothing here licenses scaling the whole list.
      🎯 **THE CONSEQUENCE IS METHODOLOGICAL: a ranking taken from the battery's
      unit times ranks CONTENTION, not work.** The three biggest entries today
      (`ramfree` 443 s, `ctllim` 411 s, `graphics` 404 s) are the ones a reader
      would attack first, and at least one of them is less than half that size in
      isolation. Time a candidate ALONE before pricing a conversion for it.
      🔴 **AND `ctllim` IS CONVERTIBLE BUT NOT WORTH CONVERTING** —
      `scratchpad/batchcheck.py ctllim-acceptance` reads **batched 153.0 s vs
      boot-per-case 155.4 s, every row identical, 1.0x**. Its cost is CASE
      RUNTIME (`step=180.0`; the cases exhaust the control-frame pool on purpose),
      not boots, so the whole boot-sharing idea cannot touch it. A CONVERTIBLE
      verdict is a statement about SAFETY, not about value, and this is the first
      row where the two come apart.
      ⚠️ **`ramfree` (the single biggest) CANNOT BE JUDGED YET**: it calls
      `run_cases` with a ONE-case matrix inside a Python loop, so the control
      refuses it as `NOT TESTED` until the `run_side` restructure. It is one of
      the "25 for-loop probes" — and that figure comes from the same grep this
      entry already records as having over-counted.
      🔴 **`lineerr` WAS THE BIGGEST PRIZE IN THE BATTERY (~210 boots, 3.2x on
      offer) AND IT IS NOT AVAILABLE.** Its `d.*` rows PEEK system variables
      (`GRPACX`/`GRPACY`, `GXPOS`/`GYPOS`) that survive a case, so a shared boot
      reads the PREVIOUS case's graphics accumulator: `d.defd40k` reads
      ` 0 , 7 , 7236 ` batched against ` 0 , 7 , 40004 ` fresh.
      ⚠️ **AND ALL 30 STILL SAY `ok` IN BOTH MODES** — all three sides agree on
      the polluted value too. Four suites in this family converted and two leak,
      which is why each gets the control rather than an argument from its
      siblings.
      ✅ **THREE MORE CONVERTED 2026-09-02 (D-BATCH8), ALL CLEAN — 0 DIFFERING
      ROWS EACH**: `width` 3.5x (134.1 s → 37.9 s, 94-case matrix, 103 rows),
      `locarg` 3.9x, `forvar` 3.2x. These have no `probe_signal` and no per-case
      `run_gap`, so the transformation is the plain one.
      🟢 **`width` IS THE INTERESTING PASS**: `WIDTH n` is exactly the kind of
      state that does not survive a shared boot, and it converts cleanly because
      each case's own `cfg["reset"]` is prepended to its lines and re-establishes
      the screen before it runs. Being stateful is not the same as leaking —
      which is why the control decides and not a reading of the subject.
      ✅ **THREE MORE 2026-09-02 (D-BATCH9), 0 DIFFERING ROWS EACH**: `nxary`
      4.6x, `nxlist` 3.3x, `readvar` 2.3x. **13 converted, 6 refused.**
      🔴 **AND "THE TRANSFORMATION IS NOW MECHANICAL" WAS WRONG.** Normalised
      against a converted template, **none of the ten remaining candidates is
      byte-identical** — a blind bulk transform would have been applied to
      shapes it does not fit. The differences turn out to be shallow (the disk is
      hoisted and shared rather than copied per case; the `CASES` tuple has 2 or
      3 fields), so `nxary`/`nxlist`/`readvar` are the `forvar` shape EXACTLY and
      converted from that template — but that had to be checked, not assumed.
      ➡️ Remaining, each needing its own read: `arylv` (per-case `responses`),
      `fldary`, `fldwidth`, `inputary`, `lrvar`, `lvfix`, `onerr0`, `cassave`,
      `namspc`/`tgtspc` (2 `run_cases` sites each), `sysvarsweep` (85-line
      `run_side`), `banner` (no single `run_side` at all), plus `graphics` (44
      sites) and `deffn` (shared harness).
