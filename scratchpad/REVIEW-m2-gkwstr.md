# Goldfish review (test-writer role), 2026-11-23: docs/keywords/LEN.md, ASC.md, CHR$.md, SPACE$.md, STRING$.md, INSTR.md

Read: the six pages; `probes/basic/spec/kstr.py`, `kstr_model.py`, `kstr_controls.py`, `ramrec.py`, the six `*_rules.py`
modules; `scratchpad/KST_run1.out`. Nothing was run.

**Run-file records decoded (by hand, from the hex):** every record of the `OS` group (20 cases) and the `FX` group
(115 cases), reference AND zerobas, each mapped to its `FX` index; the first 1 to 5 records of `SRC`, `NUM`, `STRN`,
`STRS`, `INS1` to `INS4` on both machines (including `KST INS2 HE TE P-`: reference R = 0, zerobas R = 1).
**Not decoded:** the remaining records of the matrix groups `SRC`, `NUM`, `STRN`, `STRS`, `INS1` to `INS4`. Their
tallies (the per-rule case counts, the 34 R-INSTR-EMPTY failures, every Controls count) were checked against the
probe's matrices and the model by arithmetic, not against the records. Everything decoded agrees with the pages: the
divergent FX cases are exactly 83, 84, 101, 113 (INSTR) and 114 (STRING$), and every case count and output count in
the six headers adds up.

## 1. Rules NOT pinned by any measured case

1. **STRING$.md: no case uses a fill string written in the program text.** Every string-fill case uses `S$`, `T$+S$`
   or a `DATA`-built string, but the Details examples (`STRING$(3,"*")`, `STRING$(3,"xyz")`, `STRING$(2, "AB")`,
   `STRING$(2,"AB" )`) are all literals. LEN, ASC and INSTR each have a literal row; STRING$ has none. In particular,
   the D-CLOSESPACE divergence is unmeasured for a literal fill. Measurement: `R$=STRING$(2,"AB")`,
   `R$=STRING$(2,"AB" )` and `R$=STRING$(2, "AB")` as FX rows.
2. **INSTR.md R-INSTR-START: where error 5 changes to error 6 is not pinned for INSTR.** The starts measured are
   -32769, -1, 256 and 32768. The values that fix the boundary (-32768, 32767) and the values that show truncation
   happens before the range test (-32768.5, 32767.9) are all missing, although CHR$, SPACE$ and STRING$ measure them.
   Measurement: add -32768.5, -32768, -32767, 32767 and 32767.9 to `STARTS`.
3. **SPACE$.md / STRING$.md: no case pins the Details claim about the string space "a program starts with".** Every
   room case runs after an explicit `CLEAR 200`. That the default string space equals `CLEAR 200` is assumed.
   Measurement: an OS-style group with no `CLEAR`.
4. **STRING$.md R-STRING-ROOM: measured with a code fill only.** `KST OS STRING$` is `STRING$(N,65)`, so the room rule
   is not measured for `STRING$(N,a$)`. Measurement: the same counts with `STRING$(N,S$)`.
5. **STRING$.md R-STRING-TYPE / R-STRING-ORDER: the order between the count's TYPE and evaluating the fill is not
   measured.** `STRING$("A",256)` is the only such case, and its fill evaluates cleanly. Measurement:
   `STRING$("A",1/0)`, which gives 13 if the count's type is checked first and 11 otherwise.
6. **STRING$.md: a fill that fails on type with a valid count is not measured.** `5+"A"` appears only with count -1.
   Measurement: `STRING$(2,5+"A")`.
7. **INSTR.md R-INSTR-OWNERR: the sentence says "1/0 as any argument", but only three positions are measured**: the
   start, the second argument of the two-string form, and the third argument. The haystack of the three-argument form
   has no case. Measurement: `INSTR(1,1/0,T$)`.
8. **CHR$.md / SPACE$.md / STRING$.md, "the whole set of errors": error 14 for CHR$ (a one-byte result with no string
   space left) is not measured, and no page lists it.** Measurement: CHR$ after string space is filled to 0 bytes
   free.

## 2. Rules the measured cases could ALSO explain with a different rule

1. **All six pages, R-*-KEEP ("the source strings are left as they were"): the check reads only each source's length
   and byte sum.** A rival rule, "S$ and T$ keep their length and sum", fits every case, so a keyword that reorders,
   swaps or offsetting-corrupts bytes in `S$` passes. The descriptor pointer is not read either, so a copy that
   re-points `S$` also passes. In most matrix groups `T$` is empty, which makes T$'s half trivially true. To separate
   them, record `S$`'s first and last byte and its weighted sum: `STR_DIGEST` already computes them, but the record
   does not store them.
2. **SPACE$.md / STRING$.md R-SPACE-ROOM / R-STRING-ROOM: the 199/200 boundary fits more than one rule.** Rule A: the
   result must fit in the free space left beside the one-character old `R$` (the page's rule). Rule B: a fixed
   reserve of 1 byte, or a limit of CLEAR size - 1, whatever else is live. Both give 199 fits and 200 is error 14.
   Case that separates them: the same boundary with a longer previous `R$` (say 10 characters) or a non-empty `S$`.
   Rule A moves the boundary and Rule B does not. SPACE$'s open list names "other strings"; STRING$'s does not
   (see 4.3).
3. **INSTR.md R-INSTR-START: "below -32768 or above 32767 is error 6" fits the data no better than a rival.** The
   rival is: error 6 for anything below -1 that is not -1, or above 256 that is not 256, for example "6 when the
   absolute value is over 32767.5", or "6 when the value is outside -256 to 32767". The rival also gives -32769 as 6,
   -1 as 5, 256 as 5 and 32768 as 6. The separating cases are -32768, 32767, -32768.5 and 32767.9 (same as 1.2).
4. **STRING$.md R-STRING-FORMS / the Differences section: "a space before the closing parenthesis after a string fill"
   and "after a string VARIABLE" fit the one failing case equally well.** FX 114 is `S$ )`. INSTR shows the failure
   with literals too (FX 113), but STRING$ has no literal case. The separating case is `STRING$(2,"AB" )` (1.1).

## 3. Citations that do not match the tables

1. **INSTR.md Differences: "`INSTR(200,"ABCABC","")` 0 there and 7 here" names a start that is not in the matrix.**
   `STARTS` has 129, 130, 131, 254 and 255, but not 200. The value is extrapolated from zerobas's min(start, LEN+1)
   rule, not measured. Cite a measured start (for example 129) instead.
2. **SPACE$.md R-SPACE-FORMS: the sentence says "an integer, a hex and a single argument" are allowed, but the probe
   has no SPACE$ single-precision case.** Only `CHR$(65.9!)` exists. The rule's 5 cases are plain, a space before the
   parenthesis, spaces around the argument, `3%` and `&H3`. Its own open list also says only `3%` and `&H3` were
   measured.
3. **SPACE$.md and STRING$.md, the error-set sentences ("{2, 5, 13}" plus the Overflow) leave out error 14**, which
   R-SPACE-ROOM and R-STRING-ROOM measured on both machines (10 cases each). They also leave out error 11 from the
   argument. LEN.md says why 11 is excluded; these two pages give no reason for leaving out 14.
4. **STRING$.md Details: "`STRING$ (2,65)`, `STRING$(2, "AB")` and `STRING$(2,"AB" )` are all "AA"".** None of the
   two literal forms is measured; the measured cases use `S$`. The last one, with the space before the closing
   parenthesis, is a known zerobas divergence, yet the sentence sits under rules that also present zerobas. Mark it as
   a reference-only behaviour, or cite FX 61 and FX 114 for the `S$` forms.
5. **SPACE$.md / STRING$.md / CHR$.md R-*-FORMS: the selector includes "a space after the parenthesis", but no
   CHR$, SPACE$ or STRING$ case has that label.** Only LEN and ASC have it; STRING$ has "a space after the
   parenthesis, a string fill". The tables are correct, but "spaces around the argument" is the only test of
   "after the parenthesis" for CHR$ and SPACE$.

## 4. Gaps in the open lists

1. **INSTR.md**: missing are the 5/6 boundary and the truncate-before-range test for the start (1.2), the haystack's
   own error in the three-argument form (1.7), and that the `200` example in Differences is not measured (3.1).
2. **STRING$.md**: missing are that no literal fill was measured, including the D-CLOSESPACE divergence (1.1); that
   the room rule was measured with a code fill only (1.4); the count's type against the fill's own error (1.5); and a
   fill type mismatch with a valid count (1.6).
3. **STRING$.md**: "String space at other `CLEAR` sizes" leaves out "and with other strings in it", which SPACE$.md
   has. The boundary depends on it (2.2).
4. **SPACE$.md / STRING$.md**: missing is that "the string space a program starts with" equals `CLEAR 200` is
   assumed (1.3).
5. **All six pages**: missing is that "the sources are kept" is checked by length and sum only, and not by content or
   location (2.1).
6. **CHR$.md**: missing is error 14 (a one-character result with no string space left), which is unmeasured and also
   absent from the "whole set of errors" (1.8).
