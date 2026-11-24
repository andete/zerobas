# Goldfish review (test-writer role), 2026-11-23: docs/keywords/ABS.md docs/keywords/SGN.md docs/keywords/INT.md docs/keywords/FIX.md docs/keywords/SQR.md

**Records decoded:** none. `scratchpad/KMA_run1.out` was opened but its hex sections were too large to read whole and
cannot be decoded by hand at 27 bytes x 774 cases per machine, so no recorded byte was checked directly. What I did:
read the probe (`probes/basic/spec/kmath.py`), the model and rule builder (`kmath_model.py`), `abs_rules.py`, and the
controls (`kmath_controls.py`). I re-derived every rule's case count, every FX index the pages cite, and the
controls' selection counts from the probe's argument lists and FX enumeration (per keyword FX offsets: 0-7
errors, 8-20 forms, 21/22 the POKEd singles; ABS 0-22, SGN 23-45, INT 46-68, FIX 69-91, SQR 92-114, LET 115-118). The
counts below are derived, not read from the run.

## 1. Rules not pinned by any measured case

1. **All five pages: "reads as 0 everywhere" for an exponent-0 zero with digit bytes is never measured here.**
   FIX.md (R-FIX-SMALL, Details "0 to every calculation and to PRINT"), INT.md ("INT(.5) is 0 to every
   calculation"), and the ASSIGN rules (R holds 00 50 00 00 ...) only record bytes. No case adds, compares, PRINTs
   or STR$s such a value; R-FIX-SMALL points to STR$'s page instead. To pin it: `R=FIX(.5!)` then record
   `R+1`, `R=0`, `SGN(R)` and `STR$(R)` on both machines.
2. **All five pages: the result is only ever stored in a DOUBLE `R` or passed to `USR`.** Storing into `A%` or `A!`
   is not measured. Examples: `A%=ABS(-32768%)` (Overflow, or not?), `A%=INT(-.5)`, and `A!=FIX(.5!)`. That last
   one is the D-ZEROLET path for a single target, which the pages call "the assignment of a single". To pin it:
   add FX rows that assign each function's edge results to `%` and `!` variables and record those variables' bytes.
3. **SQR.md R-SQR-NEAR pins only a ±3-unit bound, not the reference's digits.** The run records the reference's
   exact bytes for all 61 non-exact roots, but no rule reads them. So an implementation that differs from both the
   VG-8020 and correct rounding by up to 3 units passes. This is the 2026-07-13 decision. Even so, the page should
   say that this rule cannot tell such an implementation from zerobas. To pin it: a byte-exact rule per case, or a
   rule that holds zerobas to correct rounding (≤0.5 unit, with 99.99998 as the declared exception).
4. **SQR.md D-SQRZERO's mechanism claim is carried by no rule.** The page says R ends up as
   `00 12 34 50 00 00 00 00`, the sentinel's own digits. The rows that would separate "R's previous digits left in
   place" from "digits from elsewhere" are LET rows 117 (`R=0:R=SQR(0%)`) and 118. No page loads them; `kmath.py`
   says "no page loads fn LET". To pin it: load rows 115-118 in a LET/ASSIGN rule on SQR's page (or LET's), or drop
   the mechanism sentence.
5. **ABS.md, SGN.md, INT.md, FIX.md, SQR.md Details: forms quoted in prose are not the forms measured.** The prose
   quotes `PRINT ABS`, `ABS(1,2)`, `FIX(1,1)`, `SQR(1,2)`, `ABS(-1E38)`, `INT(-1E38)`, `FIX(-1E38)` and `SGN(-1E38)`.
   The KMA cases are `R=F`, `R=F(5,1)` and ±9.99999E62. Those claims rest on older runs (t6enum, kwsweep), not on this
   spec's rules. To pin them: add `PRINT F` and `F(-1E38)` to FX, or reword the prose to the measured forms.
6. **ABS.md "What we found": parity at 32-deep nesting is claimed, but only one level of nesting is measured**
   (`F(F(2.25))`). To pin it: an FX row with 16 and 32 nested calls.

## 2. Rules the cases could also explain with a different rule

1. **All five pages: every rule is checked against each machine's OWN `READ` bytes, never against the DATA text.**
   `check_apparatus` compares USR's bytes and R's value with the recorded argument. It never compares that argument
   with the text, and never compares one machine's argument with the other's. So "zerobas agrees" is also explained
   by "zerobas READs the text to different bytes and the function is right on those bytes". The same blind spot
   covers a function that changes its argument variable: line 40 re-records `N` before each of the six calls, and the
   next case is judged on the changed value. Two cases separate the rules: `enc(text, type)` against the recorded
   argument (both machines), and the argument being equal across a text's six rows (ID, ABS, SGN, INT, FIX, SQR).
   As things stand, a case id such as "KMA MI SQR 2" names a value that no check confirms.
2. **SQR.md R-SQR-NEAR: the bound is sized from the RESULT's decade, not the exact root's** (`near()` in
   `kmath_model.py`). Take a root just below a power of ten, such as `SQR(.99999999999999#)` ≈ 0.999999999999995.
   A result of `1` gets a ulp of 1E-13, so the rule accepts up to about 30 units of the root's own 14th digit. The
   rival rule is "within 3 units of the exact root's 14th digit". A result that rounds across the decade separates
   the two. The check should size the ulp from the exact root.
3. **SQR.md control "a single argument gives a single result": the reported FALSE on 66 of 66 is inflated.** Of
   those 66, 26 are negative arguments that raise error 5 and 2 are zeros. The control's check (`e1==0 and vt==4`)
   fails on the error cases under any type rule. So only 38-40 cases actually separate "double" from "single". The
   control should select cases with no error.
4. **SGN.md Details: "`SGN(2.5)+0.5` is 1.5, not 3" separates nothing.** 1+0.5 is 1.5 whether the result is an
   integer or a single. The integer type is pinned only by the USR type cell. Either drop the example or replace it
   with one that separates the two types.
5. **INT.md, FIX.md, ABS.md, SGN.md, SQR.md R-*-FORMS: the literal types are inputs to the model, not measurements.**
   `FX_ARG` asserts them, and its comment says "measured through USR on the matrix-free forms". No FX row passes the
   bare literal to USR (there are no ID rows in FX). The types are pinned only indirectly, where the function keeps
   its type: FIX/INT separate `-32768` single from `-32768` integer. ABS and SGN cannot tell them apart (both give
   45 32 76 80 / FF FF), and SQR cannot tell `-0` integer from `-0` single. To pin them: add `Q=USR(<literal>)`
   apparatus rows to FX.

## 3. Citations that do not match the tables

1. **SQR.md Differences: "35 of the 160 measured cases" cannot be reproduced from the tables.** The control
   "correctly rounded" is FALSE on 30 matrix cases, and the page lists 6 FX cases (100, 102, 103, 105, 106, 112),
   which makes 36. Reaching 35 needs one excluded case, apparently `SQR(99.99998)`, where per "What we found" the
   two machines agree. The page should say so. Its Summary ("zerobas is the one that is correctly rounded") also
   contradicts that exception.
2. **ABS.md, SGN.md, INT.md, SQR.md R-*-ASSIGN: the example "FIX(.5!)'s exponent-0 result keeps its digit bytes in
   R" is not a case of those pages.** It comes from FIX's cases (or LET row 116). On SGN and SQR the rule never
   meets a single with exponent 0 in R.
3. **SQR.md: the rule table's case counts add to 168, not 160.** R-SQR-FORMS's 13 FX cases are also counted in
   NEG, ZERO, EXACT or NEAR. The other four pages partition their cases. This is not wrong, but the per-rule counts
   do not add up to the stated total, unlike the sibling pages.
4. **SQR.md R-SQR-NEAR / "What we found": the extremes are attributed inconsistently.** The rule says
   "SQR(.4!) 2.4 units high", with a range up to +2.5. "What we found" names (.4!, .999999!) as the bounds. Neither
   says which case is the +2.5 (presumably .999999!), so the bound's witness is not cited.

## 4. Gaps in the open lists

1. **All five pages: argument READ parity and argument preservation across calls** (item 2.1) are not listed as
   open or assumed.
2. **All five pages: error precedence is not listed.** No case pits the argument's own error or type against a
   syntax error: `F(1/0` (11 or 2?), `F("A"` (13 or 2?), `F(1/0,2)`. These cases separate "evaluate, then check
   `)`/`,`" from "parse first".
3. **All five pages: assignment to integer and single variables, and PRINT/arithmetic of exponent-0 zeros**
   (items 1.1 and 1.2), are not listed.
4. **SQR.md: the four LET rows (115-118) are measured but loaded by no page.** They are neither listed as
   unread evidence nor as open. The pages' "800 read, 0 unread" counts only the keyword's own 160 cases.
5. **All five pages: nesting deeper than one level, and `PRINT F` / `F(-1E38)` in the spec probe** (items 1.5 and
   1.6), are not listed.
6. **SQR.md: the open list should also say that R-SQR-NEAR does not constrain zerobas toward the reference**
   (item 1.3). Its last bullet covers only whether the reference ever exceeds 3 units.
