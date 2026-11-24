# Goldfish review (test-writer role), 2026-11-23: docs/keywords/LEFT$.md, docs/keywords/RIGHT$.md, docs/keywords/MID$.md

**Records decoded.** From `scratchpad/KSL_run1.out`, by splitting the hex by hand (the only tools used were read-only text
tools — `awk`/`fold`/`cut` to split the hex; no probe, rule module or `tools/spec_rules.py` was run):
- FX: all 44 reference records decoded and checked against every FX-selecting rule of the three pages; all match.
- LR: reference records 168-223 (all of L5, both functions, all 28 N) and 252-279 (L255, N=2 .. 1E10); all match the model.
- MID: reference records 450-464 (L5 P=-1), 525-539 (L5 P=2, every M), 645-659 (L5 P=32768), 840-854 (L255 P=255.9); all match.
- Reference vs zerobas: the two CAP strings are byte-identical in all three sections (FX 972, LR 6164, MID 19804 hex chars =
  44 / 280 / 900 records + done flag + `$C3`), so every zerobas column ✓ is consistent.
- NOT decoded: the remaining LR (L0, L1, L2, L255 N below 2) and MID records (775 of 900).
- NOT read: `probes/lib/ramrec.py` (not cited by the pages), so the meaning of `ERRLINE`, `STR_DIGEST`, `HEAD`, `TAIL` comes from
  `kslice.py`'s docstring. Also not read: `sliceoom_run.out`, `argspace_run.out`, `argspace_after.out`,
  `fnspace_after2.out`, `kwram_full.out`, `t6enum_b4.out`, `midextra_run.out`, `midextra_probe.py`, `midspace_after.out`,
  `kwdoc_examples.py`, and the linked `.md` docs. Read and matched to the pages: `kwdoc_left_s.out`, `kwdoc_right_s.out`,
  `kwdoc_mid_s.out`.

## 1. Rules not pinned by any measured case

1. **MID$.md, R-MID-COUNT.** "error 6 outside -32768 to 32767" for the count is measured on the high side only (M=32768).
   No count below -32768, and none at -32768, 32767, -32768.5 or 32767.9, is in `MID_M`. So neither the lower overflow, the
   5/6 edges, nor truncation-before-the-overflow-test is pinned for MID$'s count; "as LEFT$'s" is assumed. To pin it, add M in
   {-1E10, -32769, -32768.5, -32768, 32767, 32767.9, 70000} with a valid P.
2. **MID$.md, R-MID-POS.** For the position, the only cases around the 5/6 edges are -1 and 256 (giving 5), 32768 and 70000
   (giving 6), and FX `MID$(S$,-32769,1)` (giving 6). Nothing measures P=-32768, P=32767, P=-32768.5 or P=32767.9. "Below
   -32768 / above 32767", and truncation happening before the overflow test, are unpinned for the position. Add those four P
   values.
3. **MID$.md, Details "The statement" and the statement rows of the Errors table** (past-the-end gives 5, numeric target
   13, `=5` 13, empty right side 24, `MID$(5,1)="X"` 2, array target, READ copy, space before `=`). There is no rule and no
   KSL case for any of them. Only the example (`kwdoc_mid_s.out`) witnesses two overwrites and one past-the-end 5. Open
   admits the statement as a whole, but the Errors table mixes these rows with the measured function rows and does not mark
   them.
4. **MID$.md, Details "Spaces are allowed … around the commas".** FX 41 is `MID$( S$ ,2 ,2 )`, which has spaces before the
   commas and never after one. A space after a comma is unmeasured for MID$. Add `MID$(S$, 2, 2)`.
5. **LEFT$.md / RIGHT$.md / MID$.md: an empty operand.** `LEFT$(S$,)`, `MID$(S$,,1)` and `MID$(S$,1,)` are unmeasured. The
   Details' "a missing argument is Syntax error" could be 24 (Missing operand) here, and 24 already exists in this family
   (the MID$ statement's `=` with nothing after it). Measure all three.
6. **LEFT$.md / RIGHT$.md / MID$.md: when the range check runs compared with the closing parenthesis.** `LEFT$(S$,256,1)`,
   `LEFT$(S$,256` with no `)`, and `MID$(S$,0,1,1)` are unmeasured. Error 5 there would mean the count is checked as soon
   as it is evaluated; error 2 would mean the syntax is parsed first. None of the pages says which happens.
7. **RIGHT$.md, count forms.** The integer (`2%`), hex (`&H2`) and single counts are unmeasured for RIGHT$; Open admits it.
   Add the two FX rows that LEFT$ has.
8. **LEFT$.md / RIGHT$.md / MID$.md: the result never used as a temporary.** Every matrix and FX case assigns to `R$`. The
   result as an unassigned temporary is pinned only by the example's `PRINT`/`LEN` (in a comparison, concatenation or
   another function's argument, it is not pinned at all). Add `R$=LEFT$(S$,2)+"X"` and `IF LEFT$(S$,2)=…`.

## 2. Rules the cases could also explain with a different rule

1. **LEFT$.md R-LEFT-EXPR and RIGHT$.md R-RIGHT-EXPR, the nested case.** `LEFT$(LEFT$(S$,4),2)` = `LEFT$(S$,2)` and
   `RIGHT$(RIGHT$(S$,4),2)` = `RIGHT$(S$,2)`. Rule A says the outer call works on the inner result. Rule B says the inner
   call is ignored or the outer call reads the original source, and it gives the same bytes. `LEFT$(RIGHT$(S$,4),2)`
   (2,3) or `LEFT$(LEFT$(S$,2),4)` (1,2 against 1..4) separates them.
2. **LEFT$.md / RIGHT$.md / MID$.md, R-*-TYPE: when the string's type is checked.** Rule A checks the first argument's type
   as soon as it is evaluated, before the count is evaluated. Rule B evaluates every argument and then checks types before
   ranges. `LEFT$(5,-1)`=13 fits both. `LEFT$(5,1/0)` and `MID$(5,1/0)` separate them (13 under A, 11 under B). The LEFT$
   Details sentence "If the wrong-typed argument fails to compute on its own, that error wins" covers only `LEFT$(1/0,1)`.
3. **LEFT$.md / RIGHT$.md / MID$.md, R-*-SRC.** The check reads only the source's length and byte sum. "Left as it was" and
   "same length and same sum" (for example a permutation, or +1 on one byte and -1 on another) are the same rule as far as
   the check can tell. Within a length group the next cases' W checksums would catch a mutation indirectly, since `S$` is
   rebuilt only per L, but the last case of each L and the FX tail have no such witness. Record W (or FB/LB) of `S$` too.
4. **MID$.md R-MID-ORDER vs R-MID-POS.** `MID$(S$,-32769,1)` is a case under ORDER, but its count is valid and correctly
   typed, so it tells nothing about order. It equally fits "position overflow" alone (R-MID-POS's content). For the lower
   side, the ORDER rule is in fact unwitnessed. `MID$(S$,-32769,"A")` or `MID$(S$,-32769,1/0)` would make it an ORDER case.

## 3. Citations that do not match the tables

1. **MID$.md Summary** says zerobas behaves like the VG-8020 "in every case we have measured except one error code". The
   rules table has 10/10 ✓ on zerobas, "Differences from the reference" says "No known difference", and the What-we-found
   section records D-MIDEXTRA as fixed on 2026-10-27. The Summary sentence is stale.
2. **MID$.md "Differences from the reference"** says the extra-argument error 2 "has no sweep row … covered by the gate row
   below instead". No gate row follows in that section (it is presumably `missing-acceptance me-extra` under Tests).
   R-MID-SYNTAX now measures `MID$(S$,1,1,1)` = 2 on both machines (FX 30, decoded), so the paragraph and the Status line
   "every error not yet proven" are stale or need reconciling with that rule.
3. **LEFT$.md and RIGHT$.md**: "The whole set of errors LEFT$ [RIGHT$] can raise is {2, 5, 6, 13}" conflicts with
   R-LEFT-OWNERR / R-RIGHT-OWNERR, which measure error 11 from the same expression. An argument such as `S$+S$` at L>127
   would also raise 15. Either qualify the sentence ("raised by the function itself") or widen the set.
4. **MID$.md Errors table**, first row: "count negative … 5". R-MID-SLICE measures count -.9 → "" with no error (decoded:
   L5 P=2 M=-.9 gives RL 0, E 0). The row needs "truncated count negative", which is how LEFT$.md phrases it.
5. **MID$.md Details "Spaces are allowed … around the commas"** cites more than FX 40/41 measure (no space after a comma);
   see 1.4.
6. **MID$.md Details** gives `MID$(a$,99999,-1)` → 6 and `MID$(a$,0,99999)` → 5. Neither value is in the matrix. The rule
   text uses `MID$(S$,70000,-1)` and `MID$(S$,0,32768)`, which are measured (decoded L5 P=32768 → all 6). The Details
   examples should use the measured values.
7. **LEFT$.md / RIGHT$.md Details tables** use string literals (`LEFT$("AB",-1)`, `LEFT$("AB","A")`). Every KSL case uses
   the variable `S$`, and Open lists "a source string that points into the program text (a literal …)" as unmeasured. So the
   table rows cite a form the evidence does not cover. That matters for errors only weakly, but `LEFT$("ABC",9)` → "ABC" is
   exactly the unmeasured literal source.

## 4. Gaps in the open lists

1. **All three pages**: the empty-operand forms (1.5) and the range-vs-closing-parenthesis order (1.6) are in no Open list.
2. **All three pages**: the type-before-evaluation question (`LEFT$(5,1/0)`, `MID$(5,1/0)`; 2.2) is in no Open list. "That
   any error of the argument wins is assumed" covers a different question.
3. **All three pages**: assigning the result to its own source (`S$=LEFT$(S$,2)`, `S$=MID$(S$,2)`) is not listed. That is
   the aliasing case a slice implementation which shares the source's bytes would get wrong.
4. **All three pages**: errors 14 (Out of string space) and 15 (String too long) are neither measured nor listed, and that
   bears on the "whole set of errors" sentence (3.3).
5. **All three pages**: the result used without assignment (1.8) and an array element as the source or the result are not
   listed.
6. **MID$.md**: the missing MID-count edges and lower overflow (1.1) and the position edges (1.2) are not listed. Open's
   "integer or single variables" item does not cover double values at these edges.
7. **MID$.md**: a space after a comma (1.4) is not listed.
8. **LEFT$.md / RIGHT$.md / MID$.md, R-*-SRC**: that the source check reads length and sum only (2.3) is not recorded
   anywhere as a limit of the evidence.
