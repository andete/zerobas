- [ ] ⚠️ **DEF FN's knife roster is EIGHT, and eight is a candidate roster, not a
      verdict.** Filed 2026-08-23 by D-DEFFNKNIFE,
      [`docs/spec-basic-deffnknife.md`](../../docs/spec-basic-deffnknife.md) §9.
      `scratchpad/deffn_knives.py` (+ `scratchpad/deffn_de_knife.py`'s K-DE1)
      now cut the ceiling in BOTH directions, `fn_leave`'s DE, PRINT's item
      classification, the result-type coercion, the frame reset and the stack
      floor. **Unknifed and named**: the phase discriminator (`dfn_is_result`'s
      `inc a` — what reddens if the body and actual phases are confused?),
      `fn_enter`'s "only the live part" copy length, the `$FFFF` result-slot
      **key** (K-RT1 cuts the TYPE it writes, not the key), `dfn_delim`'s
      two-cursor swap, and `dfn_a_x`'s grow-never-shrink `FN_FEND` rule. Each was
      skipped because its predicted set is wide (most of the successful-call
      rows) and a wide prediction scored EXACTLY is worth less than a narrow one
      — but "wide" is a guess until it is measured
      [[a-hand-listed-denominator-is-a-scope-claim]].
      ✅ **THREE OF THE FIVE KNIFED 2026-08-26 — ROSTER 9 → 12, ALL EXACT**
      ([`scratchpad/deffn_knives.py`](../../scratchpad/deffn_knives.py)). *"Wide" was
      a guess until measured; it is now three different numbers.*
      ```
      K-IR1  dfn_is_result `inc a` -> `or a`        42 of 71 rows
      K-DL1  dfn_delim `cp c` -> `cp a`              2 rows
      K-GS1  dfn_a_x grow-never-shrink guard removed 0 rows
      ```
      🔴 **K-DL1 FALSIFIED THE COMMENT ABOVE ITS OWN SITE.** `dfn_delim`'s header
      claimed the compare *"is the WHOLE of the arity rule, and it is why ERR 2
      comes out of `FNA(1,2)` on a one-formal FN (o.toomany)"*. With the two
      delimiters forced to agree, `o.toofew` and `o.aryformal` go red and
      **`o.toomany` does NOT** — too many actuals is still ERR 2, decided
      somewhere else. A comment naming three rows owned two. **Corrected in
      place**, 0 ROM bytes (hashes unchanged)
      [[a-fix-falsifies-the-justification-beside-it]].
      🔴 **K-GS1 REDDENED NOTHING — 0 of 71.** `deffn-strict` cannot witness the
      grow-never-shrink rule at all, so the 2 B `jr c,dfn_a_x` guard is
      **unobservable by this row set**. Encoded EXACT with an empty prediction,
      because the emptiness IS the result
      [[knife-that-reddens-nothing-is-the-finding]]. ⚠️ That is not a licence to
      delete it — D-RESUME's withdrawal had a row that CONTRADICTED the rule;
      this has none either way. What it says is that nothing here would notice
      if the guard were wrong.
      🟢 **AND K-IR1 VINDICATES THE ITEM'S OWN REASON FOR SKIPPING IT**: 42 of 71
      rows scored exactly says very little about the one line cut, which is
      precisely why a wide prediction is worth less than a narrow one.
      ~~➡️ **TWO REMAIN**: `fn_enter`'s "only the live part" copy length and the
      `$FFFF` result-slot **key** (K-RT1 cuts the TYPE it writes, not the key).
      Neither has a label this sweep could site precisely; they need reading
      before cutting.~~
      ✅ **BOTH KNIFED 2026-09-27 (loop) — ROSTER 12 → 14.** Read first: the
      live-prefix copy moved into the sub-ROM's `fnf_save` (D-FNPOOL), and the
      re-key is the two `ld (hl),$FF` in `dfn_bodydone`.
      ```
      K-LP1  fnf_save copies the fixed cells only   4 DIFF + b.recurse BLANK
      K-RK1  the re-key writes a LETTER key          0 of 73
      ```
      🔮 K-LP1 predicted "nested-call rows only" — HIT, bar the recursion row
      (`b.recurse`: ref ERR 7, zb `<NO OUTPUT>`), not named. K-RK1 predicted
      "the numeric successful calls move" — **MISS: nothing moved.** Only one
      slot is live at the re-key, so no formal can collide whatever the key
      says; the "`$FF` is a key no formal can carry" argument does its work in
      `dfn_is_result`'s PHASE test (K-IR1), not in the coercion. Both source
      comments that leaned on it are corrected in place, 0 ROM bytes (sub and
      main hashes unchanged). ⚠️ That makes the re-key's two `ld (hl),$FF`
      UNOBSERVABLE by this row set — like K-GS1, not a licence to delete them.
      🎚️ APPARATUS — knife roster
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (3 of 5 knifed 2026-08-26; 2 remain, unsited).
