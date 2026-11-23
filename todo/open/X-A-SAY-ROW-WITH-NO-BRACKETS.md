- [ ] **A `--say` row with no brackets cannot have a reading.**
      Found 2026-08-01 in D-NAMBLANK. `result_span_after_echo`
      ([`probes/lib/omsx_repl.py:1212`](../../probes/lib/omsx_repl.py:1212)) returns the
      text between the last `[` and its `]`, so a `SAY_ONLY` payload that prints
      no brackets reads `<none>` on **every** side — and sides that all failed
      compare EQUAL and report *agrees*. `basic_probe_lnblank.py`'s `dir-print`
      had been in that state since it was written (dormant rather than green: the
      gate filters `--say` rows out). Both its payload and the new `dir-name` are
      bracketed now and locked.
      ⚠️ **The class is not closed** — this was found in one probe by accident.
      ~~Sweep every `SAY_ONLY`/`result_span` row in `probes/` for a payload that
      cannot produce a bracketed span~~ — **THE SWEEP IS NOT EXPRESSIBLE AS A TEXT
      SCAN, MEASURED 2026-09-06.** 36 files reach the span reader; scanning their
      string literals for a `PRINT` payload with no `[` returns **200 hits**, and
      nearly all are ERROR-FACE rows whose reading is the message, not a span —
      they never go through `result_span` at all. Payloads live in data tables
      and the reader is called elsewhere, so which payload reaches which call
      cannot be decided statically. A 200-hit advisory is one nobody reads
      [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
      ✅ **THE HELPER HALF SHIPPED INSTEAD (D-SPANWHY, 2026-09-06), AND IT IS THE
      HALF THAT GENERALISES.** `result_span` returns `None` for **FOUR** distinct
      situations — nothing captured, no `[` anywhere, a `[` with no `]`, and (in
      `result_span_after_echo`) no echo row to search after — so no caller could
      tell "this payload can never produce a reading" from "the machine aborted".
      Both now take an optional `why` dict and name which, using the same
      out-parameter idiom `run_cases` already has for `settle_out` and the same
      cure as `_why_missing`. **Additive: every existing caller passes no `why`
      and is untouched**, which a dedicated arm pins.
      🔬 Gated by [`tests/test_span_reader.py`](../../tests/test_span_reader.py), 8
      arms under `make unit-test` — including the one that matters, that a
      bracketless payload and an abort give DIFFERENT reasons. ⚠️ Deliberately
      NOT in `omsx_repl --selftest`: that entry takes a MACHINE and boots an
      emulator, and `tools/check_selftests.py` excuses it from the static gate
      for exactly that reason, so arms added there would be gated by nothing
      cheap.
      ~~➡️ **STILL OPEN: nothing yet PASSES `why`.** The channel exists and is
      tested; converting call sites is opportunistic, and the audit of which rows
      are in the bracketless state still has no mechanical route.~~
      🟢 **D-SAYBLIND (2026-09-27, loop): THE PROBE THIS ITEM WAS FOUND IN NOW
      PASSES `why` AND REFUSES A BLIND ROW.** `basic_probe_lnblank.py`'s
      SAY_ONLY reader (`say_span`) keeps the reason: no echo row → `<NO ECHO>`
      (refused), no bracket / an unterminated one → `<none: no bracket>` /
      `<none: aborted mid-PRINT>` (readings — one side aborting where the others
      print is a finding). A row where EVERY answered side has no reading is
      refused as BLIND instead of compared. 🔴 **AND THE SAME SHAPE WAS LIVE
      THROUGH A SECOND SENTINEL:** the TAIL_ONLY reader's `<NO ECHO>` was
      commented "(fatal)" but was not in `BAD`, so three sides that all lost
      the echo row would have AGREED. It is in `BAD` now.
      [`tests/test_lnblank_blind.py`](../../tests/test_lnblank_blind.py), 11 arms under
      `make unit-test`, NEGATIVE arms included (all-sides no-reading refused;
      one side only is NOT refused); it caught my first cut, which keyed on
      "aborted" — a word the no-`[` reason also contains. `make
      lnblank-say-acceptance` after: **208/208**, 0 BLIND (predicted — hit).
      ➡️ **STILL OPEN:** the other 35 files that reach the span reader pass no
      `why`; converting them stays opportunistic. Same shape as [`chancost` NOREAD](../../docs/chancost-cf3300-characterization.md):
      a sentinel that also means "no reading" is not a measurement.
      🎚️ APPARATUS — --say readout
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
