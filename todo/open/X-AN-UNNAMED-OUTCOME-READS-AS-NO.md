- [ ] ⚠️ **AN UNNAMED OUTCOME READS AS NO OUTCOME, AND THE FIX MOVES THE HOLE
      ONE MESSAGE ALONG.** Filed 2026-08-23, D-CLRTRAP §5 — a probe-design
      residual, not a BASIC one. `face()` knew only about a numeric fence, so an
      untrapped `Missing operand in 30` scored `<NO OUTPUT>`; naming
      `UNTRAPPED <msg> in <line>` fixed it, and **within the hour `t.after`
      scored `<NO OUTPUT>` on ALL THREE machines because "Division by zero" was
      missing from the new alternation.** 🎯 Every probe in this tree that
      buckets an unmodelled result as *"nothing"* has this shape. The standing
      question: **what might the machine legitimately DO that this readout has
      no name for — and when you add one name, what is the next one?** No gate
      covers it; `scratchpad/circmiss_sib2.py` carries the widened list.
      📏 **THE STANDING QUESTION NOW HAS A NUMBER — SWEPT 2026-08-26**
      ([`scratchpad/unnamed_outcome_sweep.py`](../../scratchpad/unnamed_outcome_sweep.py),
      [`scratchpad/unnamed_outcome_sweep.out`](../../scratchpad/unnamed_outcome_sweep.out)).
      Denominator is the ROM's OWN table — every `db "…",0 ; ERR n` in
      [`sub/errmsg.asm`](../../sub/errmsg.asm), **30 messages** — so it cannot drift
      from what the machine can print.
      ```
      probes with a <NO OUTPUT> bucket            53
        classify by MESSAGE TEXT  (the subject)   31
        classify by ERR code / span / VRAM        22
      coverage of the canon      min 1   median 6   max 15
      COMPLETE readouts                            0 of 31
      sentinels that do NOT carry the text        52 of 53
      ```
      📏 **RE-SWEPT 2026-09-02 (D-CARRYTEXT), AND THE THESIS IS ACTED ON RATHER
      THAN RE-STATED.** The corpus is bigger than the 2026-08-26 numbers above
      (82 probes with the bucket, 34 classifying by message text):

          COMPLETE readouts                    0 of 31  ->  1 of 34
          sentinels NOT carrying the text     52 of 53  ->  68 of 82
          the widest readout                     15/30  ->  30/30

      🎯 **CARRYING THE TEXT IS THE BOUNDED FIX, AND IT IS THIS ITEM'S OWN LOGIC
      FOLLOWED THROUGH.** If "add the next name" is unbounded, stop adding names:
      make the readout say WHAT IT COULD NOT NAME. Twelve probes now do
      (`lrvar`, `fldwidth`, and ten more sharing one exact `for e in ERRORS`
      shape — `readvar inputary arylv forvar nxary nxlist lvsites lvfix fldary
      tgtspc`). `<NO OUTPUT>` now means the screen was genuinely EMPTY;
      `<UNREADABLE: …>` means it had text this probe cannot spell — a sentence
      about the PROBE, where the old one was a sentence about the MACHINE.
      ✅ **WITNESSED, BECAUSE THE BATTERY MOVED ZERO ROWS** (92/92 green, as it
      should be — every currently-named reading is still named). A change that
      moves nothing is unwitnessed, so K-CT1/K-CT2 EMPTY a probe's alphabet
      entirely: `fldary` then reads 4 rows and `forvar` 30 rows as
      `<UNREADABLE: Subscript out of range in 30>` / `<UNREADABLE: NEXT without
      FOR in 20>`, with **zero** `<NO OUTPUT>`. The path is live and carries the
      line suffix too.
      🔴 **AND THE SWEEP COULD NOT SEE ITS OWN SUBJECT.** After all twelve edits
      it still reported `80 of 82`, because its predicate matched the SPELLING —
      `<NO OUTPUT` followed by a `{` — rather than the PROPERTY. A separate
      `<UNREADABLE:` sentinel is strictly MORE informative (it separates "nothing
      printed" from "something I cannot spell") and scored as no fix at all.
      Widened to accept both shapes; the count then moved 80 → 68, exactly the
      twelve. **The instrument said the fix had not happened, and a planted
      knife said it had.** [[readout-blind-to-its-own-subject]]
      ➡️ **REMAINING: 68**, of which 48 classify by code/span/VRAM rather than by
      message text and may not want this shape at all — check before assuming
      the number is a to-do list.
      🎯 ~~**SO "ADD THE NEXT NAME" IS PROVABLY UNBOUNDED, WHICH IS THE ITEM'S OWN
      THESIS MEASURED.** Not one readout in the tree can name even half the
      canon; the widest — `basic_probe_fldwidth.py`, 15/30 — is still blind to
      `Bad FAT`, `Bad drive name`, `Bad file name`, `Bad sector number`,
      `Can't CONTINUE` and ten more.~~
      🔴 **RE-SWEPT 2026-09-05 AND THAT SENTENCE IS FALSIFIED IN BOTH HALVES.**
      `basic_probe_fldwidth.py` is **30/30 — a COMPLETE readout** — and
      `basic_probe_lrvar.py` is **29/30**. "Not one can name even half" and "the
      widest is 15/30" were both true when written and are not now.
      📏 **TODAY'S FIGURES: 102 probes with the bucket, 38 classifying by message
      text, 84 sentinels not carrying the text, coverage min 1 / median 5 /
      max 30.** The filed line above reads 82 / 34 / 68. ⚠️ The corpus is
      `git ls-files`, so it grows as probes are TRACKED — and **only 2 of the
      +21 were added today** (`errmsg_alphabet.py`, now excluded, and
      `ntwall_sep.py`), measured with `git log --diff-filter=A`, not assumed.
      🔴 **AND THE SWEEP WAS COUNTING THE CANON ITSELF.**
      [`probes/lib/errmsg_alphabet.py`](../../probes/lib/errmsg_alphabet.py) **IS** the
      30-message table this sweep measures coverage against; its `<NO OUTPUT>`
      sits in a docstring explaining the very class, and it scored **5/30** as
      though it were a probe with a narrow alphabet. Excluded — a sweep that
      includes its own denominator is reporting on itself
      [[readout-blind-to-its-own-subject]].
      🟢 **AND "CONVERSION IS OPPORTUNISTIC" IS NO LONGER THE WHOLE STORY**:
      `make error-alphabet-check` (D-ALPHAGATE, 2026-09-05) makes an
      `<UNREADABLE>` arm **mandatory** for any classifier that iterates an error
      alphabet and can return a bare sentinel. Four more were converted under it
      (`namspc`'s `bracket`/`errface`/`listface`, `strparen`'s `face`), and the
      16 such classifiers in the tree now read **0 without the arm**. The
      remaining 84 are sentinels of OTHER shapes, which that gate does not
      claim. The file this item names as carrying the
      widened list, `scratchpad/circmiss_sib2.py`, reaches **11/30**: genuinely
      widened, still less than half.
      ➡️ **THE DURABLE FIX IS THE SELF-DESCRIBING SENTINEL, NOT A LONGER
      ALTERNATION** — emit the unrecognised screen text INSIDE the sentinel, so
      an unmodelled outcome names itself and the hole cannot move one message
      along. **52 of 53 sentinels are bare literals**; exactly one already does
      this. It is the same cure as `omsx_repl._why_missing` and D-PASMOSAY, both
      of which turned a silent `<NO CAPTURE>` into a diagnosis.
      ⚠️ **NOT MASS-EDITED, DELIBERATELY.** It is ~52 sites whose printed output
      IS the evidence for shipped slices, and today's lesson is that a mechanical
      sweep whose blast radius cannot be verified breaks invariants its own rule
      cannot see [[a-mechanical-fix-can-break-a-different-invariant]]. Convert
      opportunistically, when touching a probe anyway — and the sweep above is
      the standing measure of how far that has got.
      🔴 **MY OWN FIRST DETECTOR MEASURED THE SPELLING, NOT THE LIST**: it looked
      for quoted literals and scored `circmiss_sib2.py` at **1/30**, because that
      file spells its list as a regex alternation. It was the anomaly — the item
      names that file as the remedy — that exposed it, not the tally.
      🎚️ APPARATUS — readout
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (measured 2026-08-26; conversion is opportunistic, the sweep is the standing measure).
