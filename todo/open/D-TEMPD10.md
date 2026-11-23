- [ ] 🔴 **D-TEMPD10 — TEN NESTED PENDING STRING TEMPORARIES ARE `String formula too
      complex` ON THE VG-8020 AND ANSWER HERE (found 2026-11-05 by the D-FNALIAS plan)**
      🎚️ TIER 6 — which of an error and a value a deep string expression gets.
      🤖 **AUTONOMOUS** — measured.
      📏 [`fnstrtemp_run.out`](scratchpad/fnstrtemp_run.out) `ctl` row: `X$=MID$("Z",1)+(` x k
      around `"19"` -- both answer k=0..9; at k=10 the VG-8020 is ERR 16 and zerobas prints
      `ZZZZZZZZZZ19`. D-ADDR29 TEMPST measured "10 pending, the 11th errs" with a different
      expression shape; this one errs one level earlier there. Read which temporaries the
      reference counts before moving zerobas's limit.
      📏 **MECHANISM MEASURED 2026-11-05** ([`tempd10_run.out`](scratchpad/tempd10_run.out),
      fnstrtemp_probe.py --inner, k = 9 / 10 nested around three innermost operands):
      VG-8020 `"19"` 9 ok / 10 ERR 16, `B$` 9 / 10 both ok, `B$+""` 9 ok / 10 ERR 16;
      zerobas `"19"` both ok, `B$` both ok, `B$+""` 9 ok / 10 ERR 16. 🔮 "a literal costs
      a slot there" HIT. **The reference gives a string LITERAL operand its own
      temp descriptor; zerobas's literal (D-LITREF, by reference into the program text)
      takes none.** Concatenation results count the same on both. ➡️ The fix charges a
      TEMPST slot per literal operand (a descriptor pointing into the text, released by
      the consumer as D-TEMPPOL's are) -- every string expression passes there, so it is
      FULL-gated, and D-FNSTR9 is to be re-measured after it (its `"1"+""` actuals are
      literals too).
      ⚠️ **READ BEFORE BUILDING (2026-11-05): A TEMP ENTRY IS ASSUMED TO OWN A HEAP BODY.**
      sub/strheap.asm says so outright (sh_src_is_temp: "UNIQUELY OWNED ... FIXED-ADDRESS"),
      and two users act on it: sh_append (op 2) extends a temp's body IN PLACE
      (D-CONCATPEAK), and she_snap_keep (op 16) hands a temp to str_set_key as-is. A temp
      whose ptr is the PROGRAM TEXT would let the first `"AB"+X$` append into the program
      itself. So the literal's slot needs either (a) every in-place mutator to refuse a
      text-backed temp (ptr outside [FRETOP, C)) and copy instead, or (b) a counted
      placeholder released by the literal's consumer -- which the release-by-STRPTR-identity
      rule (D-TEMPPOL) does not support today, and keeping it to the statement's end is the
      first-cut failure D-ADDR29 TEMPST already recorded. (a) is the shape; list every
      op that writes through a temp's ptr before touching str_eval_lit.
