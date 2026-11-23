- [x] ⚠️ **`CSAVE` AND `CLOAD` STILL TAKE A LITERAL FILENAME ONLY, AND THAT IS
      ✅ **CLOSED 2026-09-05 (D-CSAVEEXPR).** 5 divergences → 0 across 10 rows on 3 machines, `cassave-acceptance` 20/20 and `castail-acceptance` green off the DECODED WAV, and the edit RECOVERED 9 B of main page 1. Nothing outstanding.
      NOW A DIVERGENCE OF ITS OWN RATHER THAN PART OF A FAMILY.** Filed
      2026-08-21 by D-FNEXPR2. Every OTHER filename verb — `OPEN`, `KILL`,
      `NAME`, `SAVE`, `BSAVE`, `LOAD`, `BLOAD`, `FILES` — takes a string
      EXPRESSION as of `cffb34d` + this slice; `do_cload`
      ([`basic/cload.asm`](../../basic/cload.asm)) and `do_csave`
      ([`basic/save.asm`](../../basic/save.asm)) keep their `cp '"'` gates, and
      `basic/PROVENANCE.md` now says so explicitly instead of describing both
      halves with one sentence.
      ✅ **MEASURED 2026-09-04 — D-CSAVEEXPR
      ([`scratchpad/csaveexpr_probe.py`](../../scratchpad/csaveexpr_probe.py)), on a
      fresh recording tape per row (the `basic_probe_cassave.py` fixture). Both
      references agree on every row; **SEVEN divergences, not one**:

          CSAVE A$        refs accepted (silent)   zb `load error`
          CSAVE A$+""     refs accepted            zb `load error`
          CSAVE           refs `Missing operand`   zb SILENT -- accepted
          CSAVE 5         refs `Type mismatch`     zb `load error`
          CSAVE"P"        silent on all three      (control)

      🔴 **AND `CSAVE`'s NAME IS NOT OPTIONAL AT ALL.** `csav_noname` serves three
      forms and the reference **errors on every one**, with TWO different faces:

          CSAVE       refs `Missing operand`   zb SILENT
          CSAVE:      refs `Missing operand`   zb SILENT
          CSAVE,2     refs `Syntax error`      zb SILENT
          CSAVE"P",2  accepted on all three    (control)

      So the entry's "optional argument … the `FILES`-style *is there an argument
      at all* question" is answered and the premise is wrong: there is no
      no-name form. **Seven divergences**, and the three above are all SILENT
      ACCEPTANCE — this tree runs a `CSAVE` the reference refuses. The face
      depends only on whether a `,` follows, which fully specifies the fix.
      🔴 **EVERY ZEROBAS REFUSAL HERE IS NON-RAISING.** `do_csave`'s `cp '"'`
      gate goes to `load_error`, which PRINTS and carries on, so `ON ERROR`
      cannot trap any of them — exactly the class D-FNEXPR2 closed for the other
      eight filename verbs and did not close here.
      ⚠️ **THE INSTRUMENT TOOK THREE CUTS AND EACH FAILED DIFFERENTLY**, which is
      why the probe reports TWO channels: an `ERR`-reading probe scores a
      non-raising `load error` as **accepted**; a screen-reading one that maps an
      EMPTY capture to "accepted" scores an error the same way; and a `<...>`
      fence matches the `PRINT` statement in the SOURCE IT ECHOES. The trap
      channel currently reads `<NO READING>` on every row and says so rather than
      agreeing — the screen channel carries the result, corroborated by the first
      cut's ERR codes (24 = Missing operand, 13 = Type mismatch).
      The original framing, for the record: these
      are CASSETTE verbs: `CSAVE A$` on the CF-3300 needs a tape, and the
      `namspc` battery has none. `cassave-acceptance` / `castail-acceptance` are
      the batteries that CAN drive tape — the reading belongs there, and it
      should come before any byte. 💰 The edit itself is the same shape as the
      five this slice did and would likely RECOVER bytes (each gate is longer
      than the `call fname_expr` that replaces it); what is not free is knowing
      what the reference does with `CSAVE`'s OPTIONAL argument, which has the
      `FILES`-style "is there an argument at all" question in it.
      🟢 **FIXED 2026-09-05 (D-CSAVEEXPR) — AND IT RECOVERED 9 BYTES OF MAIN
      PAGE 1.** `do_csave` and `do_cload` now `call fname_expr`, the same route
      the other eight verbs took. **These were the last two `cp '"'` filename
      gates in the tree.**

          row        refs                zb before     zb after
          s.var      accepted (silent)   load error    silent
          s.expr     accepted            load error    silent
          s.num      Type mismatch       load error    Type mismatch
          s.unterm   accepted            load error    silent
          l.num      Type mismatch       load error    Type mismatch

      10 rows, 3 machines, **all agree after; 5 divergences → 0.**
      🔴 **TWO OF THE FIVE ARE NEW, AND BOTH CAME FROM ASKING WHAT THE EDIT WOULD
      TOUCH RATHER THAN WHAT IT WAS FOR.**
      • `s.unterm` (`CSAVE"P`, no closing quote) is the row the fix would have
      MOVED unasked: the hand-rolled parse demanded the closing quote, `str_eval`
      follows MSX BASIC and auto-terminates at end of line. **Measured BEFORE the
      edit**, so *"the fix closes it rather than changing it"* is a reading, not a
      guess [[a-fix-falsifies-the-justification-beside-it]].
      • `l.num` is **CLOAD**, which this entry names beside `CSAVE` and the
      2026-09-04 run never measured — half the filed claim had never been read
      [[a-justification-parenthesis-is-an-unrun-claim]].
      ⚠️ **THE CLOAD SCOPE IS STATED, NOT ASSUMED.** `CLOAD A$` and `CLOAD"P"`
      reach the tape, and a tape search that finds nothing is the `LOAD"CAS:"`
      class this file records as NOT RETURNING (*"no row can carry this"*) — each
      would be a 300 s timeout on three machines and two channels for a
      `<NO READING>`. `CLOAD 5` errors in the PARSE, before any tape access, and
      says the reference EVALUATES the operand. The verb is changed on that face
      plus the eight already on `fname_expr`, and
      [`basic/cload.asm`](../../basic/cload.asm) says so at the site.
      💰 **MAIN PAGE 1: 6 B → 15 B FREE** (`make basic-reloc`, before and after —
      re-run it, never quote this). Each hand-rolled gate was longer than the
      `call fname_expr` replacing it, exactly as the price note above predicted.
      🎯 **THAT IS A CARVE**, and it is the one the unary-plus entry needs: filed
      at 10 B against 6 B free, it now fits.
      🟢 `cassave-acceptance` 20/20 and `castail-acceptance` green — those read
      the **decoded WAV**, not the screen, so a `silent` row is corroborated by a
      tape that actually contains the right bytes.
      🔧 One stale review entry retired with the site it described:
      `tape_parse_name` in
      [`tools/redundant-load-reviewed.txt`](../../tools/redundant-load-reviewed.txt),
      caught by `redundant-load-check` going red — an entry that asserts nothing
      is how that control goes blind, and the gate says so itself.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
