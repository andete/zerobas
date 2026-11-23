- [x] **README "Limitations (this slice)" IS STALE** — pre-existing doc debt, FLAGGED
      ✅ **REWRITTEN AND CLOSED 2026-09-05 (D-READMESTALE) — AGAINST MEASUREMENTS,
      NOT CLAIM-BY-CLAIM**, which is what the entry asked for.
      📏 **THE NEW SECTION'S FIGURES ARE RE-RUN, NOT REMEMBERED**: `make kwsweep`
      today reads **0 MISSING**, 35 SUPPORTED, 1 DIVERGENT (37 of 55 executed,
      18 crunch-only with reasons), and the battery is **114 units**. The section
      says so and tells the reader to re-run rather than trust it.
      ⚠️ **The one DIVERGENT is named as NOT a defect** — `CSRLIN` in a row with
      no `CLS`, where the reference disagrees with itself across differently
      scrolled batches.
      🔴 **AND THE "CHECK THE NEIGHBOURING PROSE" INSTRUCTION PAID OFF TWICE.**
      • *"(Decimal ≥ 32768 … plus `&O`/`&B` and line-number references are out of
      scope for now; use `&H` for 16-bit values.)"* — measured today: `PRINT
      40000` reads `40000`, `PRINT &O17` reads `15`, `PRINT 1/4` reads `.25`, and
      `$0E` line-number references are emitted. ⚠️ **`&B` stays out ON PURPOSE**
      and the correction says so, because "not implemented" and "deliberately not
      fabricated" are different claims — the oracle emits no `&B` token.
      • *"dispatching each on its leading token: `POKE`, a `<letter> = <expr>`
      assignment, `REM`, `BLOAD`"* — a FOUR-STATEMENT interpreter, in the
      description of today's dispatcher.
      🎯 Both struck beside their replacements rather than deleted: the point of
      the entry was that the old text misleads a reader, and showing what it said
      is what stops the next reader wondering whether it was ever true.      2026-07-29 by S3 of the lean-cart retirement, which deliberately did not fix it
      (out of scope; S3 was a byte-identical mechanical edit plus its own doc sweep).
      [`README.md:291`](README.md:291) describes an early game-loader-scoped slice, not
      today's BASIC. Measured false claims: it lists **`ON … GOTO` as "still out"**
      (it is implemented — `ON_TOKEN` → `ex_on` in `stmt_table`, gated by
      `tests/test_stmt_dispatch.py`, and `tests/test_control_flow.py` exercises the
      branch), and it says **"variables are single-letter integers (`A`–`Z`); no
      strings, arrays, or multi-character names"** and "no `/`, no string ops", all of
      which predate the string engine, the float pack and the array engine.
      A warning banner is in place so a reader is not misled, but the section needs
      rewriting against the CHARTER (faithful full MSX1 BASIC), not patching
      claim-by-claim. **Check the neighbouring prose too** — the same slice-era framing
      likely leaks into the sections around it.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (hand-corrected: the charter it contradicts is already settled).
