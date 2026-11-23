- [x] ✅ **D-USING (2026-09-09): PRINT USING'S FORMAT VOCABULARY HAS THREE
      REFERENCE SPLITS, AND ZEROBAS FOLLOWS A DIFFERENT REFERENCE ON DIFFERENT
      ROWS — CLOSED 2026-09-09 (D-PUDOLLAR): THE VERB HAS ONE ORACLE, AND ALL
      THREE SPLITS ARE NOW GATED — 14 rows × 3 machines, 0 DIFF but 3 REFS-SPLIT**
      ([`scratchpad/using_probe.py`](../../scratchpad/using_probe.py),
      [`.out`](../../scratchpad/using_run.out),
      [codes](../../scratchpad/using_err.out)).
      `ex_print_using` is the largest thinly-commented handler in the tree — 251
      lines at 0.49 comments per line — which is what the density ranking picked it
      out for. The vocabulary is a DENOMINATOR, so the rows enumerate it rather than
      hunting corners: `#`, `.`, `+`, trailing `-`, `**`, `$$`, `,`, `^^^^`, literal
      text, `!`, `&`, `\ \`.
      ✅ **ELEVEN OF FOURTEEN AGREE ON ALL THREE MACHINES**, including the `%`
      overflow marker, rounding at the last place, asterisk fill, comma grouping and
      the exponential form. The implementation is broadly right.
      | row | vg8020 | cf3300 | zb |
      |---|---|---|---|
      | `USING"&";"ABC"` | `ABC` | **ERR 5** | `ABC` — follows **VG** |
      | `USING"\   \";"ABCDE"` | `ABCDE` | **ERR 5** | `ABCDE` — follows **VG** |
      | `USING"$$###";42` | `[  $42]` | `[$$ 42]` | `[$$ 42]` — follows **CF** |
      🎯 **THE INCONSISTENCY IS THE FINDING.** Two string specifiers the CF-3300
      REFUSES are implemented here (matching the VG-8020), while the one
      presentational split is resolved the CF-3300's way. That is an outcome, not an
      intent — nothing chose it — but it means the verb currently has no single
      oracle.
      ➡️ **JOOST'S STANDING RULING APPEARS TO SETTLE `$$`** — *"a purely
      presentational reference split ships the VG value on BOTH targets"*
      [[oracle-split-prefer-vg8020]] — and where the `$` lands in a fixed-width
      field is presentational. That would make `$$###`;42 render `  $42`. **Not done
      here**: the ruling is his, floating-`$` is a real change to the renderer
      rather than a constant, and applying a ruling by analogy at 3am is how a
      decision gets made by accident. Flagged for him with the measurement attached.
      ⚠️ **AND THE TWO `ERR 5` ROWS ARE PROBABLY NOT A STYLE SPLIT AT ALL** — a
      Japanese machine renders `\` as the yen sign, so the CF-3300 may not
      recognise the string-field delimiter. That is a HYPOTHESIS from one
      observation and is NOT the basis of anything here; the measured fact is only
      that the CF-3300 raises ERR 5 where the VG-8020 renders
      [[a-mechanism-inferred-from-one-observation]].
      📏 **A SECOND OBSERVATION (2026-10-29, the program ladder's L5 draft):**
      `LPRINT USING "## \          \ ####";1;N$;Q` on the CF-3300 printed
      `` 1 \          \ `` LITERALLY, then handed N$ to `####`: ERR 13. So the
      backslash pair is not a string field there -- the hypothesis above, now seen
      directly. zerobas's DISK target renders the field, as the VG-8020 does.
      🔴 **AND THE FRAMING ABOVE IS WRONG — THIS IS NOT A PRESENTATIONAL
      SPLIT AT ALL (2026-09-09, answering Joost's *"what makes the most sense
      given the intent of the format string?"*).** The row is `$$###`, the
      **floating-dollar** specifier, not a literal `$` in a fixed field. Read the
      two faces again: the VG-8020 gives `[  $42]` — five columns, the two `$$`
      positions reserved, one of them spent on a `$` that FLOATS to sit against
      the number. The CF-3300 gives `[$$ 42]` — the two dollars echoed
      **literally** and the number right-justified in the remaining three. The
      CF-3300 does not implement the specifier.
      🎯 **AND THE PROOF IS ONE ROW UP, IN THIS PROBE'S OWN TABLE.** `u.star`,
      `USING"**###";42`, reads `***42` on **all three machines**. `**` and `$$`
      are the same grammatical construct — a two-character prefix that reserves
      its own positions and then fills or floats — and the CF-3300 implements
      `**` correctly while echoing `$$`. That is not a house style; it is a
      **missing case in the CF-3300's own vocabulary**, and its own `**` row is
      what says so.
      ➡️ **SO THE 09-04 STYLISTIC RULING IS THE WRONG INSTRUMENT AND WAS NOT
      NEEDED.** This is a CAPABILITY split, which that ruling explicitly does not
      cover, and it resolves the same way the other two rows already did: follow
      the reference that IMPLEMENTS the specifier. `&` and `\   \` follow the
      VG-8020 for exactly this reason; `$$` should too. The verb then has ONE
      oracle, which was this item's actual finding.
      ⚠️ **AND THAT MEANS ZEROBAS DOES NOT IMPLEMENT `$$` EITHER** — it emits
      `$$ 42`, matching the CF-3300's gap rather than choosing a style. The work
      is a real renderer change (reserve two, emit one, float it), not a constant,
      so it is NOT inside the 20 B standing budget until it is priced.
      ✅ **BUILT 2026-09-09 — D-PUDOLLAR, [`docs/spec-basic-pudollar.md`](../../docs/spec-basic-pudollar.md).
      8 of 8 in-scope rows now read the VG-8020's answer exactly**
      ([`scratchpad/dollar_probe.py`](../../scratchpad/dollar_probe.py),
      [before](../../scratchpad/dollar_run.out), [after](../../scratchpad/dollar_after.out)).
      💰 **PRICED AND IT DISSOLVED: main page 1 130 → 129 B — ONE byte**, well
      inside the standing 20 B budget. The whole specifier is a sub-ROM change
      (1313 → 1184 B, 129 B) because `basic/pu-render.inc` is a page-0 tenant and
      D-PUEMIT had already moved the pad+emit sub-side; the single resident byte
      is `or a` → `and $03`. ⚠️ The pre-build estimate was ~60 sub-ROM bytes and
      the measurement is 129 — short, and recorded as short.
      🎯 **THE RULE IS ONE SENTENCE: the `$` is CONTENT, not padding.** It takes a
      column from the VALUE, sits immediately before the digits and after any
      sign, and the pair adds 2 to the width exactly as `**` does. `s.full`
      (`$$###`;12345 → `%$12345`) is the row that proves the first half: the `$`
      pushes six characters into a five-column field, so the ordinary overflow
      branch fires and the `%` marker costs no code at all.
      🔴 **AND THE FLAG HAS NO HOME — `PU_FLAGS` IS FULL** (bit0 trailing
      separator, bit1 wrapped, bit2 `**`, bits3-5 the sign specifier, bit6 `.`,
      bit7 `,` and D-PUEXP). It rides **`PU_TYPE` bit 2**, whose four field types
      need only bits 0-1: the floating dollar is a MODIFIER on the numeric type,
      not a type. Every reader masks — `and $03` for the type, `and $04` for the
      flag. **No new page-3 RAM**, which is what kept this inside the budget.
      🔬 **ONE PREDICTION MISS, CAUGHT BY A COLUMN COUNT.** `+$$###`;42 read
      `+  $42` where the VG-8020 reads `  +$42` — the same six characters in the
      wrong order, invisible to any error code. `ptf_plus` only accepted `#`
      after the sign, so the `+` fell through to its literal path; it now accepts
      the `$` prefix too. **This is why the witness is bracketed text and not a
      code** [[an-unnamed-outcome-reads-as-no-outcome]].
      🔬 **KNIVES 3/3 EXACT, FIRST ROUND**
      ([`scratchpad/pudollar_knives.py`](../../scratchpad/pudollar_knives.py),
      [`.out`](../../scratchpad/pudollar_knives.out)) — and the asymmetry is what makes
      the three claims separable. K-PD1 (the pair stops counting toward the
      width) moves 7 rows and **NOT `s.full`, NOT `s.ovf`**; K-PD2 (the emitted
      character becomes a space) moves 9, **including both of them**; K-PD3 (the
      `$` goes before the sign) moves exactly `s.neg` and `s.plus`. The two
      overflow rows are the discriminator: already over the field, they cannot
      notice it narrowing, but they do notice the `$` leaving.
      🟢 **THE GATE NEEDED A CATEGORY IT DID NOT HAVE, AND ITS ABSENCE WAS
      ALREADY COSTING TWO ROWS.** `basic_probe_pusing.py` scored only rows where
      the two references AGREE; splits went to `NO_ORACLE`, printed and never
      scored. Every `$$` row is a split, so pinning them needed a third category,
      `CHOSEN`, naming the reference a documented call selected. 🔴 **`x.amp`
      (`&`) and `x.slash` (`\   \`) have followed the VG-8020 since the verb was
      written, on this same capability argument, and BOTH sat in `NO_ORACLE` —
      shipped, deliberate behaviour no gate could redden.** They are `CHOSEN` now
      too, so the extension pins **nine** rows, not the seven this change is
      about. ⚠️ A row may join only if the choice is written where a person can
      read it; a split resolved in a commit message is not resolved.
      ⚠️ **TWO ROWS ARE OUT OF SCOPE AND ARE CARRIED, NOT DROPPED**
      [[a-row-written-off-as-out-of-scope-leaves-the-bookkeeping]]. Both were
      divergent before this change and neither is regressed by it:
      • `s.trail` `###$$`;42 — vg ` 42`, cf/zb ` 42$$`. The reference CONSUMES a
        trailing pair. This is why `ptf_dollar` requires a following `#` where
        `ptf_star` requires nothing: without that test the row would move to a
        third answer matching nobody.
      • `s.stardol` `**$$###`;42 — vg `$42$`, cf `42$$`, zb `****$42`. Three
        machines, three answers, and the VG's is FOUR columns where the two
        prefixes reserve four. ➡️ **The next row to run is `**$###`** —
        MS-BASIC's documented combined fill-and-float form is the only reading
        offered so far that yields four columns, and it is a hypothesis from one
        observation until that row exists
        [[a-mechanism-inferred-from-one-observation]].
