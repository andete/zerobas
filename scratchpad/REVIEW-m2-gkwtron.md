# Goldfish review (test-writer role), 2026-11-25: docs/keywords/TRON.md, TROFF.md, REM.md

**Records read.** I decoded all 25 cases of `scratchpad/KTN_run1.out` (group FX, ref and zb) and compared them with the
typed lines in `ktron.py`. The two sides are identical in every case. I also read the head of
`scratchpad/kwdoc_tron.out`, which holds the TRON example on both machines. I did **not** read `kwdoc_troff.out`,
`kwdoc_rem.out`, `officialcell_probe.out`, or kstop's and kerr's run files (`KSP_run1.out`, `KER_run1.out`). Model
behaviour below was traced by hand through `kstop_model.py`; nothing was run.

**One structural fact that the sections below depend on.** Every rule in `ktron_model.py` has the same check, `ok`:
does the whole predicted screen equal the recorded one? Rules differ only in which cases they select (by the `why`
string). So a rule's ✓ does not attest its own sentence; it attests the whole interpreter on the cases it selects. A
zerobas difference would be blamed on whichever rule selected the case, not on the clause that was wrong. (This is the
same shape as R-VAL-END in the gkwnum review.)

## 1. Rules not pinned by any measured case

Each item gives typed lines in the probe's form (after `NEW` / `CLS`) and the model's current prediction where it can
compute one. Items marked **(model cannot compute)** also need work on the model first: see 2.6.

1. **R-TRON-TRACE, "entered from its top", for a line that jumps to itself.** "Traced each time the line is entered
   from its top" and "traced when the current line number changes" agree on all 13 cases. Case:
   `10 I=I+1:IF I=1 THEN GOTO 10` / `20 PRINT I` / `TRON` / `RUN`. The rule predicts `[10][10][20] 2`; the rival
   predicts `[10][20] 2`.
2. **TRON.md Details, "after a FOR that NEXT sends back to" (back into the middle of a line).** Every FOR in the
   cases (KTN FX 3, and the 10-09 example) is the last statement of its line, so NEXT always lands at the start of the
   next line. Cases: `10 FOR I=1 TO 2:PRINT I;:NEXT` / `TRON` / `RUN` (predicted `[10] 1  2`), and
   `10 FOR I=1 TO 2` / `20 PRINT I;:NEXT` / `TRON` / `RUN` (predicted `[10][20] 1 [20] 2`).
3. **A RETURN to the start of a line.** KTN FX 2 returns into the middle of line 10. When the GOSUB is the last
   statement of its line, the return falls into the next line. Case: `10 GOSUB 40` / `20 PRINT "R"` / `30 END` /
   `40 RETURN` / `TRON` / `RUN`. The model predicts `[10][40][20]R` then `[30]`. This separates the rule from the
   rival "nothing reached by a RETURN is traced".
4. **The trace inside an error handler, and after RESUME** (in Open, but the model already predicts it).
   - `10 ON ERROR GOTO 40` / `20 ERROR 5` / `30 PRINT "N":END` / `40 RESUME NEXT` / `TRON` / `RUN`. The model predicts
     that the handler line is traced and that line 30 is traced after RESUME NEXT: `[10][20][40][30]N`.
   - A RESUME back into the middle of a line: `10 ON ERROR GOTO 40` / `20 PRINT "A";:X=1/Y` / `30 END` /
     `40 Y=1:RESUME` / `TRON` / `RUN`. The model predicts no trace when line 20 is re-entered at its second statement.
   - `RESUME 0` on a first statement, which the model traces again.
5. **CONT after STOP with the trace on.** `10 STOP:PRINT "A"` / `20 PRINT "B"` / `TRON` / `RUN` / `CONT`. The model
   predicts `[10]`, `Break in 10`, then `A` untraced (mid-line) and `[20]B`. Also a STOP that is last on its line, so
   that CONT enters the next line from its top, and CONT after an error, which the model re-enters at `(line, 0)` and
   so traces again.
6. **A typed GOTO / GOSUB / `RUN n` into the program.** R-TRON-ONOFF says "a statement typed at the prompt is never
   traced", but a typed `GOTO 10` enters a program line. Case: `10 PRINT "A"` / `TRON` / `GOTO 10`. The model
   predicts `[10]A`. No case types anything but `RUN`.
7. **A trace that wraps the screen** (in Open). Case: `10 FOR I=1 TO 9` / `20 NEXT` / `TRON` / `RUN`. That is 40
   characters of trace on a 37-column screen. Also `10 PRINT "<33 characters>";` / `30000 END`, to see whether
   `[30000]` is split at the edge or moved whole to the next row. The model cannot predict either (see 2.2).
8. **`ON n GOTO` / `ON n GOSUB` / `IF … THEN n` targets (model cannot compute).** "Traced as a GOTO or GOSUB target"
   is measured only for a plain `GOTO` and `GOSUB`. Cases: `10 ON 2 GOTO 20,30` / `20 PRINT "X"` / `30 PRINT "Y"`;
   `10 IF 1 THEN 30` / … ; `10 IF 0 THEN 20 ELSE 30` / … .
9. **"It stays on through … END" (TRON.md Details; TROFF.md Details, "RUN and END do not").** KTN FX 7 ends in END but
   never runs again. KTN FX 6 keeps the trace on across a program that ran off its end, not one that ended with END.
   Case: `10 PRINT "A":END` / `TRON` / `RUN` / `RUN`. Also run again after an error stopped the program, and after
   `CLEAR`, which no page mentions.
10. **TRON in the middle of a line, then a jump.** "Starts the trace at the NEXT line entered" is measured only for
    falling into the next line (KTN FX 4). Cases: `10 TRON:GOSUB 30:PRINT "R":END` / `30 PRINT "S":RETURN`, where the
    model predicts `[30]S` then `R`; and `10 TRON:GOTO 30` / `20 …` / `30 …`.
11. **TROFF inside a subroutine or a handler, then a RETURN / RESUME into a traced line.**
    `10 GOSUB 30:PRINT "R"` / `20 PRINT "Q"` / `30 TROFF:RETURN` / `TRON` / `RUN`. The model predicts `[10][30]R`, then
    `Q` untraced.
12. **REM inside DATA (model cannot compute).** `10 READ A$,B$:PRINT A$;B$` / `20 DATA REM,X'Y`. The question is
    whether the tokeniser treats `'` or `REM` as a comment in DATA. The model's `split` cuts at any `'` outside quotes,
    so it would read `X`. Its `READ` only reads integers.
13. **`'` and REM inside a string.** `10 PRINT "A'B:REM C"` checks that quote tracking hides both. The model's `q`
    flag predicts `A'B:REM C`, but no case puts either inside quotes.
14. **`'` after THEN (model cannot compute).** `10 B=9:IF 0 THEN 'X ELSE B=1` / `20 PRINT B`. TRON.md lists
    ifsem-acceptance as covering `'` swallowing an `ELSE`, but no KTN case does. The model crashes here (2.6).
15. **REM after THEN with a line number, and REM without a colon after a statement other than PRINT.**
    `10 IF 1 THEN 30 REM X`, `10 GOTO 30 REM X`, `10 A=1 REM X`, `10 IF 0 THEN 20 ELSE REM`. R-REM-LINE says "REM
    itself does [need a colon]", but that is measured only after a PRINT literal (KTN FX 22). After `GOTO n` the rest
    of the statement may never be examined, which would mean no error.
16. **A REM line with the trace on.** `10 GOTO 20` / `20 REM X` / `30 PRINT "Z"` / `TRON` / `RUN`, predicted
    `[10][20][30]Z`. Without the trace, KTN FX 21 cannot tell "the GOTO lands on line 20" from "it lands on line 30".
17. **TRCFLG ($F7C4) is not an output of any case.** TRON.md cites 175 / 0 from another probe. A screen case pins it:
    `TRON` / `PRINT PEEK(&HF7C4)` / `TROFF` / `PRINT PEEK(&HF7C4)`. Without that case, the bug fixed on 2026-10-13 (the
    flag kept in zerobas's own memory) would pass every KTN case.

## 2. Model laws no rule states; rule clauses the model does not compute

1. **The PRINT law behind R-REM-LINE's error clause is not a REM law, and it is wrong for MSX.** In `stmt`, a PRINT
   whose body is a string literal followed by anything that does not start with `;` raises error 2. That law produces
   KTN FX 22's `Syntax error in 10`, and the `rem-after-stmt-ok` rival is wired into that PRINT path alone. No rule
   states the law. It is also false for ordinary MSX BASIC:
   - `PRINT "A","B"` (a comma) would be error 2 under it;
   - `PRINT "X="X` (two items side by side) would be error 2 under it.

   So the clause "REM itself needs a colon" is computed only as "PRINT junk", and the model would mispredict the first
   kstop / kerr / ktron case that uses a comma.
2. **Program output never wraps.** `type()` wraps the echo at 37 columns, but `out()` and `newline()` keep each output
   row as one unbroken string. Any trace or PRINT longer than 37 characters is mispredicted. No rule states the width,
   yet TRON's trace is exactly where a long row is easy to produce (1.7).
3. **"The prompt and an error message start on a fresh row"** is a law of `newline()` and `message()`. KTN FX 3 and 7
   (prompt after `[20]`) and FX 22 (`A`, then the message) depend on it. Only TRON.md's history ("What we found")
   states it, and no rule does.
4. **The model already commits to handler entry, RESUME, CONT and a typed GOTO**, all predictions of where the trace
   appears (1.4–1.6). No rule states them, and the pages put the handler case under Open ("not measured"). That is
   consistent with Open, but the first measurement will be scored against laws nobody wrote down. State them as
   predictions before running.
5. **Where REM is recognised.** `split` sees REM only at the start of a statement, and `'` anywhere outside quotes,
   DATA included. `X=1 REM` gives error 2 only because the value parser fails, and `GOTO 20 REM X` crashes
   (`int("20 REM X")`). Neither is a stated law.
6. **Crashes, not predictions.** The model raises a Python exception on `IF … THEN 'X` (split leaves `IF 0 THEN`,
   the IF regex returns None, then AttributeError), on `GOTO n REM`, on `THEN n` (`stmt("30")` becomes error 2, not a
   jump), on `ON n GOTO` (error 2), and on `READ A$` (`int()`). `tools/spec_rules.py` has no `try`. So a case added for
   1.8, 1.12, 1.14 or 1.15 stops the checker instead of reading FALSE.
7. **Special-casing check.** The trace itself is generic: `[n]` when `i == 0` on a program line, with no case-specific
   branch. The REM / `'` handling is generic in `split` and `IF`. The exceptions are the PRINT-only REM path (2.1) and
   two controls that edit the screen (3.3).

## 3. Weak controls, and rivals the cases do not separate

1. **The `apostrophe-needs-colon` control is mislabelled.** The flip makes `'` not a comment at all. KTN FX 24
   (`PRINT "A":'B:PRINT "C"`) has a colon before the `'`, so the stated rival ("needs a colon") predicts the
   reference's `A` there. The control is FALSE on FX 24 only because the flip goes further than its label. The honest
   count for the stated rival is 1 of 8 (FX 18). Either relabel it ("`'` is not a comment") or make the flip require a
   colon.
2. **Laws with no control at all:**
   - the trace stays on through RUN (FX 6; rival "RUN switches it off");
   - a GOTO target is traced (FX 12; rival "only falling in is traced");
   - an END line is traced (FX 7);
   - no padding (FX 11; rival `[ 10]`, or padding to 5 digits);
   - error 2 after TRON / TROFF (FX 9, 15; rival "the rest is ignored");
   - TROFF when off does nothing (FX 14; rivals "it toggles", "it is an error");
   - a typed TROFF (FX 16);
   - a REM line is a GOTO target (FX 21; rival "a REM line is not stored", which gives error 8);
   - a typed REM (FX 23).

   R-TROFF-OFF has one control for its four clauses.
3. **Two controls edit the screen instead of flipping a law.** `troff-line-untraced` deletes the text `[n]` from the
   current row. It does nothing if that row has already been flushed (`20 PRINT "X":TROFF`), and it would also delete
   a `[20]` the program printed itself. `tron-line-traced` appends an extra `[n]`. A single natural rival, "the trace
   is printed after the line runs", flips both, and FX 0 separates it (`A[10]` against `[10]A`).
4. **`trace-on-return` is FALSE on one case only (FX 2).** With 1.1 and 1.3 added, it would also face a self-jump
   and a return to the start of a line.
5. **"REM needs a colon" against "a PRINT literal followed by any non-item is error 2"** (2.1). FX 22 cannot tell
   them apart, because the model implements the second. `GOTO 30 REM X`, `A=1 REM X` and `PRINT "A" B` separate them.
6. **KTN FX 19 uses `B=0`, which is also the default value.** The rival "the whole of line 10 is skipped" gives
   `[ 0 ]` as well. The page's example uses `B=9`, and spec-plan §1 asks for a sentinel. Use `B=9`.
7. **TRON only becomes effective at a line reached by falling in (FX 4).** Nothing separates "the next line entered"
   from "the next line in program order" (1.10).

## 4. Page claims with no KTN case, or contradicted by the record

1. **TRON.md Details, "after a FOR that NEXT sends back to"** (mid-line). No case (1.2).
2. **TRON.md and TROFF.md, "stays on through … END" / "END do[es] not".** No case (1.9).
3. **TRON.md and TROFF.md, "`TRON 1` … the only error the VG-8020 raises".** This universal rests on one case each.
4. **TRON.md "What we found": TRCFLG 175 / 0.** Not a KTN output (1.17). Also, "Where it lives" names the flag
   `TRACEFLAG` while the paragraph above says zerobas now uses TRCFLG. They are the same cell
   (`basic/sysvars.inc:1602`, `TRACEFLAG equ $F7C4`), but the page never says so, so a reader sees a contradiction.
5. **All three pages, "the two machines write different cells of the documented work area".** No record is cited.
6. **REM.md, "`IF 0 THEN REM ELSE B=1` … on both reference machines".** KTN ran one reference (the VG-8020).
7. **REM.md, uncited behaviour.** "LIST and LLIST show it", "RENUM does not touch numbers inside a comment", and
   "LIST turns the stored `'` back into `'`" have no case. Open lists only LIST.
8. **REM.md, "There is no error to make with REM" (and "common errors: not applicable").** The page's own R-REM-LINE
   states an error 2 for `PRINT "A" REM X` (FX 22). Either that error belongs to PRINT, and the rule should say so, or
   REM has a common error.
9. **REM.md Details, "`'` … can follow a statement without a colon".** This is pinned only after a PRINT literal. The
   `ELSE`-swallowing claim for `'` (Tests: ifsem) has no KTN case (1.14).
10. **The three Open lists are one copied paragraph.** Each names the other pages' gaps (TROFF.md lists "LIST of a
    REM's text"), and none names its own:
    - TRON.md: a self-jump, a mid-line FOR, CONT, a typed GOTO, END then RUN, ON / THEN targets;
    - TROFF.md: TROFF in a subroutine or handler;
    - REM.md: DATA, strings, `'` after THEN, `GOTO n REM`, RENUM.
11. **Status lines dated 2026-10-09 ("every error ✓", "No known divergence") sit above the DRAFT 1 header.** That
    agrees with the record (0 of 25 differ), but "every error ✓" for TRON / TROFF rests on one case each.

The counts check out: TRON 13 cases, TROFF 4, REM 8; 11 controls; the control FALSE-counts 2, 1, 4, 1, 3, 1, 1, 1,
2 (see 3.1), 1 match the cases as I traced them; and the page-quoted ref screens match the run file.

## 5. Probe-apparatus risks

1. **The screen geometry hides the wrap.** `kstop.normalise` slices the capture into 40-column rows, strips each row
   and drops empty ones, while the model uses 37 for the echo and no width for output (2.2). A wrapping trace will
   fail the model, and the failure will look like a trace difference.
2. **Blank rows and leading or trailing spaces are invisible.** A trace that emits an extra newline at column 0, or
   a padded `[ 10]` that strips to the same row edge, can agree for the wrong reason. Only `trace-newline`'s non-empty
   rows are seen.
3. **24 rows, last screen only.** A loop case for 1.2 or 1.7 that scrolls loses its first rows silently. Keep the
   cases short, or assert the row count.
4. **The model crashes on the new forms (2.6)**, and `spec_rules.py` does not catch the exception. Extend the model
   before adding those cases, or they will read as a broken checker, not as findings.
5. **The work area is not recorded.** spec-plan §1 lists work-area cells as outputs. TRCFLG is the one TRON writes,
   and the probe reads only the screen (1.17).
6. **Boot per case (`batch=False`).** The cases are independent, which is good, but every "off" state is the boot
   state. "TROFF when off" (FX 14) never meets a trace switched off by an earlier TROFF, or by NEW, in the same
   session.
7. **`ok` reads `c.scr or []`.** A missing reading (`None`) is compared as an empty screen, so it reads FALSE, not
   "no reading". That is harmless while every case has a reading.
8. **The shared interpreter.** The trace, REM and IF laws were added to `kstop_model.py`, which also predicts kstop's
   and kerr's screens. A wrong PRINT law (2.1) found here affects all three probes. I did not re-run them; spec-plan
   says they are still predicted.

**Findings: 17 + 7 + 7 + 11 + 8 = 50.**
