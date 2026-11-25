# Goldfish review (test-writer role), 2026-11-25: docs/keywords/FOR.md, NEXT.md

**Run-file records decoded.** I decoded all 43 records of `scratchpad/KFR_run1.out` (section FX), ref and zb, with a
one-line Python split of the CAP hex on the 13-byte layout in `kfor.py`'s docstring (E, F, N lo/hi, T, value bytes). The
two sides differ on exactly three cases: KFR FX 6 (zb n=1), FX 16 (zb 0,0,n=21, I% 21) and FX 36 (zb T=$EE). The
reference has **no** record with T=$EE. I compared every decoded record with the tuple in `kfor_model.expect` by reading
it. I did **not** run `spec_rules.py` or `kfor_controls.py`. The selection lists, the "FALSE on k of n" counts and the
generated tables come from reading the model, the controls and the pages; I recomputed the control counts by hand from
the tuples. I did not read `kwdoc_for.out`, `kwdoc_next.out`, `forfloat_*` or `letnew_run.out`.

## 1. Rules not pinned by any measured case

1. **FOR.md, R-FOR-ERRORS, "a shape error ends the line there (no body runs)".** The four cases behind it have nothing
   after the error on their line: FX 27 `FOR I=1`, FX 28 `FOR I=1 TO`, FX 29 `FOR I TO 3`, FX 30 `FOR 1=1 TO 3`. Their
   n=0 is the geometry, not the rule. The only Syntax-error case that has a body, FX 31 `FOR Q(1)=1 TO 3:...`, reads E=2,
   F=1, n=1: the body ran and its NEXT failed. That is the opposite of the clause, and the rule's own text lists the
   array element among the Syntax errors. To pin the clause:
   - `FOR I=1:WN%=WN%+1:NEXT`
   - `FOR I TO 3:WN%=WN%+1:NEXT`
   - `FOR 1=1 TO 3:WN%=WN%+1:NEXT`
   - `FOR I=1 TO:WN%=WN%+1:NEXT`
2. **FOR.md, R-FOR-STEP0, "STEP 0 never ends".** It was measured only with the start away from the limit (FX 5, FX 6).
   A Microsoft sign-compare NEXT ends the loop when compare(var, limit) equals sign(step). With STEP 0 that happens when
   the variable EQUALS the limit. That is a plausible rival, and the rule's universal wording claims more than the data
   shows. Open lists start = limit but the rule does not hedge it. To separate:
   - `FOR I=1 TO 1 STEP 0:WN%=WN%+1:{g}:NEXT` (sign-compare: 1 run, I 1; the rule: 21);
   - `FOR I=1 TO 3 STEP 0:WN%=WN%+1:{g}:I=3:NEXT`.
3. **FOR.md, R-FOR-INT, "TRUNCATES".** Every fractional input is positive: 1.6, 3.7, .5. spec-plan §1 names
   "truncation vs `INT` (`-.9`)" as a required separating value. Separating cases:
   - `FOR I%=-1.6 TO 0:WN%=WN%+1:{g}:NEXT`: truncation gives start -1, 2 runs; INT gives -2, 3 runs.
   - `FOR I%=1 TO 5 STEP 1.5:...`: truncation gives step 1, 5 runs, I% 6; rounding gives step 2, 3 runs, I% 7.

   FX 13's STEP .5 reads 0 under round-half-even too, so it does not separate truncation from rounding for the step.
4. **FOR.md, R-FOR-OVERFLOW, "a LIMIT an integer variable cannot hold is error 6 at the FOR".** Only +40000 (FX 16) was
   measured. Unmeasured:
   - a negative limit: `FOR I%=1 TO -40000 STEP -1`;
   - a START out of range: `FOR I%=40000 TO 1`;
   - a STEP out of range: `FOR I%=1 TO 3 STEP 40000`;
   - the range test before vs after truncation (spec-plan §1's `32767.9`): `FOR I%=32766 TO 32767.9:WN%=WN%+1:{g}:NEXT`.
     A limit truncated to 32767 gives 2 runs, then Overflow at NEXT (6,6,2). A limit rounded and range-checked gives
     6 at the FOR (6,1,1).
5. **FOR.md, R-FOR-FRACTION, "a fractional STEP adds in the variable's own type".** `.1` and every multiple up to 1.1 are
   exact in BCD at both precisions. FX 7 (`STEP .1`) and FX 9 (`STEP .1#`) are therefore identical by construction, and
   no case can show which precision the addition or the end test uses. To pin it, use a step that is not exact in
   single and record the final bytes:
   - `FOR I!=0 TO 1 STEP 1/3:...` against `FOR I#=0 TO 1 STEP 1/3:...`;
   - `FOR I#=0 TO 1 STEP 1!/3:...`, to see whether a single STEP is widened or kept.
6. **FOR.md, R-FOR-ERRORS, "an error in the start or the limit is that error".** No case puts the error in the STEP
   expression, and no case has a string START, although the Errors table cites `FOR I="A" TO 2`. Add
   `FOR I=1 TO 3 STEP 1/0:WN%=WN%+1:{g}:NEXT` and `FOR I="A" TO 3:WN%=WN%+1:{g}:NEXT`.
7. **NEXT.md, R-NEXT-CLOSE, "drops J's frame".** FX 22 cannot witness the drop: every pass re-runs `FOR J`, which
   replaces J's frame anyway, and nothing after the loop looks for J. To pin it:
   `FOR I=1 TO 2:FOR J=1 TO 3:WN%=WN%+1:{g}:NEXT I:NEXT J`. If the frame was dropped, the second NEXT is error 1.
8. **NEXT.md, R-NEXT-ERRORS, "(NEXT J inside FOR I: I 1, its frame unused)".** Whether I's frame survives the failed
   NEXT J is never tested; FX 37's line ends there. To test it: `FOR I=1 TO 2:WN%=WN%+1:{g}:NEXT J:NEXT`. If the frame
   survives: E=1, F=1, n=2, I 3. If it is dropped: n=1.
9. **NEXT.md, R-NEXT-ERRORS, "a number after NEXT error 2".** Only the first position was measured (FX 39 `NEXT 5`,
   where I is not stepped: n=1). The page claims `NEXT J,1`, a number later in the list. For the trailing comma (FX 38)
   the loop ran out BEFORE the error (n=2). Measure `FOR I=1 TO 2:WN%=WN%+1:{g}:NEXT I,5` to see whether the same
   happens here.

## 2. Model special-cases that hide a rule

1. **`kfor_model.expect` is one lookup table keyed on the case's `why` string.** All 43 tuples are written by hand. No
   rule's general clause is computed:
   - R-FOR-RUNS: start, add STEP, test "not passed the limit in STEP's direction";
   - R-FOR-ONCE: limit and step evaluated once;
   - R-FOR-INT: truncation;
   - R-FOR-FRACTION: the variable's own type;
   - R-FOR-OVERFLOW: the integer range.

   So each rule's sentence states a law, but its check is equality with 1–5 hand values. A wrong law with right table
   entries would still read ✓, and the controls compare against hand tuples too (3.1). A short loop simulator, driven
   by (start, limit, step, type, body mutation) parsed from the case text, would make R-FOR-RUNS, ONCE, INT, FRACTION
   and the integer half of OVERFLOW executable. The 1.x cases could then be added without new tuples.
2. **R-FOR-NOFRAME's "the variable as the failed FOR left it" hides an ordering law that the records pin.** The decoded
   values are:

   | case | statement | loop variable afterwards |
   |---|---|---|
   | FX 33 | `FOR I=1/0` | 0: created, start not stored |
   | FX 27 | `FOR I=1` (no TO) | 1: start stored before the TO check |
   | FX 34 | limit 1/0 | 1 |
   | FX 26 | string limit | 1 |
   | FX 32 | STEP with nothing | 1 |
   | FX 42 | string STEP | 1 |
   | FX 16 | `FOR I%=1 TO 40000` | I% 1: start stored before the limit's range test |

   The model writes these as per-case constants (`ZERO`, `D(1)`, `I(1)`). No rule states the order "create → store start
   → TO → limit → STEP". FOR.md's Details states only the "create first" half, and cites the 2026-10-19 letnew run
   rather than FX 33, which witnesses it here.
3. **FX 29 `FOR I TO 3` → `ZERO`.** The model encodes "the name is parsed and I created before the missing `=` is
   found" as a value; no rule says it. The claim also depends on VARPTR not creating I on the reference, which this run
   never shows (5.2).

## 3. Controls that are too weak, and rivals no case separates

1. **The "an integer variable keeps a fractional STEP" control (R-FOR-INT) is false only because of its hand tuple.**
   It predicts 5 runs and I% 3, which assumes I% can hold 1.5. Written out, the rival is "the step is kept as .5 and
   the sum is truncated on store". That gives 1+.5 → 1 for ever: 21 runs, I% 1, which is the measured record. So the
   rival is NOT separated by FX 13. A case that separates them is `FOR I%=3 TO 1 STEP -.5:WN%=WN%+1:{g}:NEXT`: a
   truncated step loops for ever (21, I% 3), while a kept step with a truncating store runs 3 times (3, 2, 1) and
   leaves I% 0.
2. **The "a failed FOR keeps its frame" control (R-FOR-NOFRAME) is defined on only 3 of the 8 cases it is run over.**
   Those are the string limit, the string step and STEP with nothing. On FX 25, 31, 33, 34 and 16, `expect` ignores
   `alt`, so the rival gives the rule's own tuple, and "FALSE on 3 of 8" reads stronger than it is. Under the rival,
   FX 33 would loop 0→3 (n=4, F=0). FX 16 is zerobas's actual failure, and the control does not reach it.
3. **R-FOR-NEST, "a second FOR on the same variable replaces the first's frame (3 runs, not 6)".** The rival "the second
   FOR pushes a new frame on top" also gives 3 runs and I 4 on FX 23: the inner NEXT I matches the top frame and the
   line ends. The page's "not 6" is nobody's prediction. To separate them:
   - `FOR I=1 TO 2:FOR I=1 TO 3:WN%=WN%+1:{g}:NEXT I:NEXT I`. Replace gives error 1 at the second NEXT. Stack gives
     e=0 and I 5.
   - For the Microsoft "pop everything above it" variant:
     `FOR I=1 TO 2:FOR J=1 TO 2:FOR I=1 TO 3:WN%=WN%+1:{g}:NEXT I:NEXT J`.
4. **R-NEXT-ERRORS, "two names without a comma error 1 at once" (FX 40 `NEXT I J`).** This is a case description, not a
   law. Two readings fit E=1, n=1, I 1:
   - spaces inside a name are skipped, so `NEXT I J` is `NEXT IJ`, a name with no loop (compare NEXT.md's `NEXT A (1)`
     space claim);
   - the junk after the name is rejected before stepping.

   `FOR IJ=1 TO 2:WN%=WN%+1:{g}:NEXT I J` separates them. The first reading runs 2 times with no error.
5. **Single-case controls, and laws with no control at all.**
   - Each of these controls is FALSE on exactly one case: STEP 0 (FX 6), limit-live (FX 18), step-live (FX 19), int-step-kept
     (FX 13, and that one is hollow, 3.1) and next-no-create (FX 36). A second value would make each robust, for
     example a limit RAISED in the body: `WL=1:FOR I=1 TO WL:...:WL=3:NEXT`.
   - Six rules have no control: R-FOR-FRACTION, R-FOR-NEST, R-FOR-OVERFLOW, R-FOR-ERRORS, R-NEXT-CLOSE and R-NEXT-ERRORS.
     Among them are rivals the data does separate but no control states:
     - "NEXT counts a private copy in the frame" (FX 17 separates it);
     - "32767+1 wraps to -32768 and the loop ends" (FX 11 separates it);
     - "the trailing comma is checked before stepping" (FX 38 separates it).
6. **Rivals in section 1 that are also unseparated.** STEP 0 ending at var = limit (1.2), truncation vs INT and
   rounding vs truncation of the step (1.3), and range-before-truncation (1.4) all need a control as well as a case.

## 4. Page claims with no case behind them, or that contradict the record

1. **The Summary of both pages: "zerobas behaves like the Philips VG-8020 in every case we have measured, errors
   included."** The record has three differences: FX 6, FX 16 (FOR) and FX 36 (NEXT). Both pages' own Differences
   sections and rule tables list them.
2. **FOR.md, "The whole set of errors FOR raises … is {2, 13, 24} … the Overflow belongs to NEXT."** This contradicts
   FX 16: E=6 at the FOR itself (F=1, n=1 show that no frame was pushed), as R-FOR-OVERFLOW states. It also leaves out
   FX 33 and FX 34, where FOR raises the error of its own expression (11). The Errors table has no row for the FOR-time
   Overflow.
3. **FOR.md Details, "After the loop, the variable is one step past the limit."** The record contradicts it:
   - FX 2 `FOR I=3 TO 1` leaves I 4, not 2;
   - FX 4 `FOR I=1 TO 3 STEP -1` leaves I 0, not 2;
   - FX 17 leaves I 6.

   The law the data supports is "one step past the last value the body saw".
4. **FOR.md Errors table rows with no KFR case.**
   - `FOR I="A" TO 2` (see 1.6) and `FOR I=1 TO 2 STEP 1,2` were not measured.
   - `FOR A$=1 TO 2` was not measured either; the case is `FOR A$="A" TO "B"`, FX 25.
   - `FOR I=1:NEXT` and `FOR I=1 TO:NEXT` were measured WITHOUT the `:NEXT` (FX 27, 28), which is the shape that hides
     1.1.
5. **NEXT.md Details and Errors claims with no KFR case.** They rest on the 2026-08-08 characterizations and the
   2026-10-09 example run:
   - `NEXT A` after `FOR A%`;
   - `NEXT A` after `FOR AB`;
   - `NEXT AB` abandoning `CD` (FX 22 is the nearest case, and see 1.7);
   - `NEXT A$`, `NEXT A(1)` creating A, and `NEXT A (1)`;
   - `NEXT J,1` (see 1.9);
   - `NEXT J,K` with K not open (FX 41 is `J,I,K`);
   - RETURN discarding loops.

   None of these is in NEXT.md's Open list.
6. **FOR.md Details values with no KFR case.** `STEP .25`, `56700`/`-40000`, `FOR A=.5 TO 3` → 3.5, `A=A+.5` in the
   body, and FOR/GOSUB mixing. Open covers 56700 and GOSUB; the others rest on forfloat and the example run. The
   `FRE(0)` creation-order claim does have a KFR witness (FX 33, I 0 after `FOR I=1/0`), but the page does not cite it.
7. **The Evidence paragraph on both pages: "Three probe faults … each by a run that read wrong on both machines."**
   `kfor.py` says otherwise:
   - its docstring says the guard on every body was added because "a FOR that FAILED left a half-built frame on
     zerobas", a zerobas-only fault and a fourth one the paragraph does not list;
   - `_read`'s comment says the VARPTR fault stopped zerobas's third run ("creates I on the VG-8020 but not on
     zerobas").

## 5. Probe-apparatus risks

1. **The readout uses the keyword under test.** Every record line zeroes bytes 4–12 with `FOR WK=4 TO 12:…:NEXT`, and
   `_read` copies the value with `FOR WK=0 TO nb-1:…:NEXT`. spec-plan §1 says "the readout must not use the keyword under
   test, nor its family". These loops run on top of the case's own open frame in FX 5, 6, 13 and 24 (ref), and in FX 16
   on zb, where the guard's GOTO or the line end left I's frame open. They rely on the bare NEXT finding WK innermost, on
   the machine whose FOR/NEXT is being tested. Unrolled POKEs would remove the dependency (9 + at most 8 statements).
2. **VARPTR of a variable that does not exist ($EE) is never witnessed on the reference in this run.** No reference
   record has T=$EE. R-NEXT-CREATE's "NEXT I creates I" (FX 36: ref I = 0) is therefore indistinguishable from "VARPTR
   creates I on the reference". That the reference's VARPTR refuses is asserted only in a comment about an earlier run.
   A control case would fix this: read I after the bare `NEXT` (FX 35), or after `FOR 1=1 TO 3` (FX 30), and expect $EE
   on both machines. FX 37 should also read J. The same doubt covers FX 29 and FX 33's I 0 (2.2, 2.3).
3. **The loop variable has no sentinel.** spec-plan §1 says "every case starts with its output holding a sentinel". CLEAR
   leaves I absent, so "the failed FOR stored nothing" cannot be told from "the failed FOR zeroed I". Add a twin of the
   error cases with I preset, for example `I=7:FOR I=1/0 TO 3:…` and `I=7:FOR I TO 3`. The absent-variable cases still
   carry the creation-order claim.
4. **The guard's 21 means "more than 20", not "for ever".**
   - FOR.md's Differences says zerobas "loops" on `FOR I%=1 TO 40000` (FX 16 zb: n=21, I% 21). The guard cannot tell
     that from "runs to 32767, then Overflow at NEXT".
   - R-FOR-STEP0's "never ends" and R-FOR-INT's "never ends" are the same extrapolation, though STEP0 at least says so
     in its text.
5. **ERL is not recorded, and FOR, the body and NEXT share one line.** So FOR.md's "Overflow … raised on the NEXT line"
   (and NEXT.md's "on the `NEXT` line") cannot be reached. "At NEXT" and "at the FOR itself" are inferred from n and F,
   which is sound for FX 11/12/16 but is not a location.
6. **Only the first and last errors are recorded, and no error count.** A middle error, or a repeated one, is lost. For
   example, R-FOR-NOFRAME's "the body runs once and its NEXT is error 1" cannot exclude a second error between the two.
   One count byte (incremented in line 800) would close this.
7. **Two cases whose geometry hides part of what they test.**
   - FX 20 (`NEXT J,I`) reads J only. I after the comma list's second step is unrecorded; it shows only in n.
   - FX 7 and FX 9 cannot differ (1.5).

**Finding count: 32** (§1: 9, §2: 3, §3: 6, §4: 7, §5: 7). The three with the most weight:
- 1.1: "a shape error ends the line" has no reachable case, and the one reachable case (FX 31) contradicts it.
- 4.2: FOR's error set {2, 13, 24} is contradicted by FX 16 (6 at the FOR) and FX 33/34 (11).
- 5.2: R-NEXT-CREATE rests on a VARPTR behaviour this run never shows on the reference.
