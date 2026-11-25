# Goldfish review (test-writer role), 2026-11-25: docs/keywords/IF.md, the specification section

**Run-file records decoded.** I decoded all 32 records of the `FX` section of `scratchpad/KIF_run1.out` on the reference
side with a python one-liner (6 bytes per case from byte 1: E, F, N lo/hi, P lo/hi; lead byte $5A, end byte $C3), and
checked that the zb capture string is byte-for-byte identical to the ref one. So every ✓ in both columns rests on the
same 192 bytes. Each decoded record equals the model's `T` entry for its case. The case texts below come from
`kif.py`'s `FX` list and `_lines()`. The controls' counts come from `kif_controls.py`/`expect()` and were checked against
the decoded records. I did not read `kwdoc_if.out`, `ifgoto_run.out`, `t6enum_b6.out` or the ifsem/kwsweep outputs, so
any page claim that rests on those counts as "no KIF case" here.

`m k` below means `WP%=WP% OR k`. Each case line n ends in `:GOTO n+25`, which `_lines()` appends.

## 1. Rules not pinned by any measured case

1. **R-IF-ELSE, "its statements and every statement after them on the line".** Read literally, this says an inner
   ELSE's part runs on through a following outer ELSE. No case has the outer IF true and the inner one false with two
   ELSEs: case 17 has the outer false, case 18 has both true. Pin it with
   `WP%=1:IF 1 THEN IF 0 THEN m 2 ELSE m 4 ELSE m 8`. The literal rule predicts 0b1101; "a reached ELSE ends the
   statement like REM" predicts 0b101.
2. **R-IF-ELSE, "nearest unmatched IF" for an IF that is not directly after THEN.** Every nested IF measured follows
   `THEN` directly. Pin it with an IF after a colon inside the THEN part, `WP%=1:IF 0 THEN m 2:IF 1 THEN m 4 ELSE m 8`
   (nearest-unmatched gives 0b1; "only IFs directly after THEN nest" gives 0b1001). Also measure an IF inside the ELSE
   part, `WP%=1:IF 0 THEN m 2 ELSE IF 0 THEN m 4 ELSE m 8` (0b1001).
3. **R-IF-ELSE / the zerobas scan: an operand byte that equals a token.** `if_skip_to_else` says it steps over operand
   bytes, so a constant equal to $A1 (ELSE) or $8B (IF) is not taken as a delimiter. No case puts such a byte on a false
   IF's line. Pin it with `WP%=1:IF 0 THEN WK=139 ELSE m 4` (0F 8B: if that byte counted as a nested IF, it would claim
   the ELSE, giving 0b1 instead of 0b101) and `WP%=1:IF 0 THEN WK=161:m 2 ELSE m 4` (0F A1: if that byte counted as an
   ELSE, `:m 2` would run). The reference's answer here is not obvious, so this is a measurement, not a formality.
4. **R-IF-EMPTY, "THEN followed by nothing".** No case has THEN at the end of the line; see 5.1. Pin it with a case
   whose line n has nothing after THEN (the frame has to stop appending `:GOTO n+25` for this case).
5. **R-IF-EMPTY, a false IF with an empty THEN.** Case 31 (`IF 1 THEN:m 2`) is true only. Pin it with
   `WP%=1:IF 0 THEN:m 2`. "The part runs to the end of the line" predicts 0b1. The rival "an empty THEN ends the IF at
   the colon" predicts 0b11.
6. **R-IF-JUMP, "IF ... GOTO n ... missing line error 8" and ELSE n with a missing line, taken.** The only missing-line
   case that is taken is `THEN 65000` (case 25). Pin the other forms with `WP%=1:IF 1 GOTO 65000` (8),
   `WP%=1:IF 0 GOTO 65000:m 2` (0b1, no error) and `WP%=1:IF 0 THEN m 2 ELSE 65000` (8).
7. **R-IF-TRUTH, "a string comparison is a number like any other".** Only a true comparison is measured (case 19). The
   rival "a string comparison is always true" is not excluded. Pin it with `WP%=1:IF "B"<"A" THEN m 2` (0b1).
8. **R-IF-TRUTH, "0 false".** Every 0 measured is a canonical zero in a single. Two rules fit every case: "true iff the
   exponent byte is non-zero" (zerobas reads FAC's lead byte) and "true iff any byte is non-zero". The value that
   separates them is the one the STR$ review found `READ` produces on the reference (00 10 00 00). Pin it with
   `WP%=1:WK=1:POKE VARPTR(WK),0:IF WK THEN m 2`. Also untested: an integer (`WK%=0`) and a double (`IF .1# THEN`,
   `IF 1D-60 THEN`).
9. **R-IF-ERRORS, "RESUME NEXT then carries on after THEN's statement".** Only case 24 (`IF 1/0 THEN m 2:m 4`, 0b101)
   is measured. "Resume at the next colon after the error" and "resume after THEN's first statement" agree on it. They
   are separated by `WP%=1:IF 1/0 THEN m 2 ELSE m 4:m 8` (next colon: 0b1001; after the IF statement, which runs to the
   end of the line: 0b1). The same split also needs `WP%=1:IF "A"<5 THEN m 2 ELSE m 4:m 8`.

## 2. Model special-cases that hide a rule

1. **The model is a transcription, not a prediction.** `kif_model.T` is a 32-entry table keyed by each case's `why`
   string. Each value is the full (E, F, N, P) record, and it equals the decoded run record for record. `ok()` compares
   against `T[why]`, and every rule's check is that same `ok`. A rule's sentence therefore never reaches its check: the
   six sentences could say anything, and as long as each rule selects some rows, the ✓ marks would be identical. The
   module docstring says the record is "PREDICTED from the rules", and the page says "every rule is executable" and
   "a sentence here cannot say more than the data does". Neither holds. Write the rules as functions of the case's
   inputs: the condition's value, which parts exist, whether a part is a line number or statements.
2. **Case 28's label contradicts its own entry.** `"NEXT after a true IF on the same line": (0,0,0,0b1)`. The IF is
   never true (see 5.2). The entry was copied from the record, and R-IF-LINE cites it as a witness for the TRUE half of
   its sentence. A predicting model would have given 0b11 and gone red.
3. **The controls' rivals are hand overrides of chosen rows, too** (`expect()`'s `alt` branches). A rival changes only
   the rows the author listed; on every other row it reverts to `T`, so it "agrees". `false-skips-then-only`, for
   example, overrides cases 1, 9 and 29 but not case 28. Under that rival, case 28 would run its NEXT and set 2, so
   computed honestly the control would be false on 4 of 5. The page's "FALSE on k of n" counts measure what the author
   typed, not what the rival rule implies.

## 3. Controls too weak, or missing

1. **R-IF-JUMP and R-IF-ERRORS have no control.** Plausible rivals the cases already separate:
   - "a missing line number is error 8 even when not taken": cases 26 and 30 refute it;
   - "a THEN back to its own line resumes at the IF, not the line start": case 27 refutes it (WN% would stay 1, and
     the probe would hang, see 5.5);
   - "an errored condition counts as false after RESUME NEXT": case 24 refutes it (0b1 against 0b101).

   Each should be a written control.
2. **"An ELSE part ends at the next ELSE" against "it runs to the end of the line" (1.1).** No case separates them, and
   the rule text commits to the second.
3. **"An empty THEN ends the IF at the colon" (1.5).** Cases 21 and 31 are both true, and both are `THEN:` (5.1). The
   R-IF-EMPTY control (`then-empty-syntax`) only tests the error code.
4. **"Every IF token on the line nests" against "only an IF directly after THEN nests" (1.2).** It is unseparated,
   although the IFSEM history on this very page says two coinciding rules are how the wrong fix nearly shipped.
5. **"A string comparison is always true" (1.7)** and **"exponent byte decides truth" (1.8)** are unseparated.
6. **`kif_controls.py`'s docstring runs `kgosub_controls.py`.** It is copy-pasted, and it is the wrong file to run.

## 4. Page claims with no KIF case behind them, or that contradict the record

1. **The Summary, "zerobas behaves like the Philips VG-8020 in every case we have measured but one".** Status says "No
   recorded difference", Differences says "None known", and the two captures are identical. The Summary is the odd one
   out.
2. **The Errors sentence, "the whole set of errors IF raises is {2, 8, 13}".** The record contradicts it: case 24
   raises 11 (`IF 1/0`), and R-IF-ERRORS itself states that the condition's own error propagates. The set needs "plus
   any error the condition raises". "{8, 13} for ELSE" has no case; 13 cannot plausibly come from ELSE, and 2 surely can
   (`IF 0 THEN m 2 ELSE ,`).
3. **Error table rows with no KIF case:**
   - `IF 1 GOTO "A"` (2);
   - `IF 0 THEN 30 ELSE 99` (8);
   - `IF 1 GOTO 99` (8);
   - `IF "A" THEN 30` and `IF "A" GOTO 30` (13). The only string case is a variable `WK$` with a THEN statement, not a
     literal and not a line number, and no case uses GOTO;
   - `IF 1 GOTO` "accepted";
   - `IF THEN 30`. The measured case is `IF THEN m 2`, a statement and not a line number.
4. **Details with no KIF case:**
   - `IF -.5 THEN` (only -1 and .5 are measured);
   - `IF "X" THEN` (a literal);
   - `IF 0 THEN 30 ELSE` (an empty ELSE: no case has ELSE at the end, or ELSE followed by a colon);
   - the Syntax line's `IF <c> GOTO <n> ELSE ...` (no case combines GOTO with ELSE: measure `WP%=1:IF 0 GOTO n+5 ELSE m 4`);
   - "What we found", `IF 1 GOTO PRINT "X"` (GOTO followed by a statement). Measure `WP%=1:IF 1 GOTO m 2`.
5. **Open, third item, "`IF 0 THEN 100 ELSE 200` measured".** No KIF case has a line number after THEN and an ELSE.
   Case 12 has a statement after THEN, and case 26 has no ELSE. Add `WP%=1:IF 0 THEN n+5 ELSE n+10` and
   `WP%=1:IF 1 THEN n+5 ELSE m 2`, or move the item's "measured" claim to wherever it was measured.
6. **R-IF-LINE's "a NEXT included (a loop on one line ends there)"** is pinned only by case 29 (WN%=1). R-IF-LINE also
   cites case 28 for the true half, and case 28 never makes the IF true (5.2).
7. **The Evidence paragraph says line n+1 is "reached only by FALLING THROUGH line n".** That is true, but in every
   case with an ELSE (10, 14, 18, 30) the appended `GOTO n+25` sits inside the ELSE part. A true IF there also reaches
   the record by falling through. Nothing is lost, because both routes land on the same record, but the paragraph
   implies that the route tells you something.

## 5. Probe-apparatus risks

1. **The appended `:GOTO n+25` gives every case a non-empty tail, so "THEN followed by nothing" is unreachable.** Case
   21 is really `IF 1 THEN:GOTO n+25`, the same shape as case 31 (`THEN:`). R-IF-EMPTY's first clause and its control
   rest on a case that cannot reach it.
2. **Case 28 cannot reach its subject.** In `FOR I=1 TO 3:IF I=2 THEN m 2:NEXT`, the IF is false at I=1 and skips the
   NEXT, so the line ends and I=2 never comes. The record (0b1, WN% 0) duplicates case 29's finding. To test a NEXT after
   a TRUE IF: `FOR I=1 TO 3:WN%=WN%+1:IF I<9 THEN m 2:NEXT` (WN%=3, 0b11).
3. **The error handler uses the keyword under test.** Line 800 is `IF WE=0 THEN WE=ERR`, and spec-plan §1 says "the
   readout must not use the keyword under test". A zerobas IF fault in a false single-statement IF would corrupt E in
   every error case. It is harmless today only because the machines agree. Use a branch-free form, for example
   `WE=WE-(WE=0)*ERR`.
4. **Errors are recorded only as first and last, and nothing counts them.** In all four error cases E=F, which cannot
   tell "one error" from "the same error N times". WN% is free in those cases (0 in each). `WN%=WN%+1` in line 810
   would count errors at no cost.
5. **The hang guard is defined but never used.** `G = "ON -(WN%>20) GOTO {R}"` is dead. Case 27 loops on its own line.
   A zerobas that resumed at the IF instead of the line start would loop forever, and lose every later case to the
   capture timeout instead of recording one wrong WN%. Put `G` on line n+5 of case 27.
6. **Every case sets `CLEAR 300,&HBF00` on line n.** That is fine, but case 28 and case 29 leave an open FOR frame
   when the false IF skips the NEXT. Only the next case's CLEAR removes it. If the record line (n+25) is ever made to
   use FOR, these two cases will interfere with it.

**Count: 30 findings.** §1: 9 (1.1–1.9). §2: 3. §3: 6 (3.1 counts as one, 3.6 is a docstring). §4: 7. §5: 6. One
underlying fault surfaces in several sections: case 28 (2.2, 4.6, 5.2) and the appended GOTO (1.4, 3.3, 5.1). Counting
those as one each gives **26 distinct**.
