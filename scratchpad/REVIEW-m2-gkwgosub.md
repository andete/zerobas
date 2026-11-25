# Goldfish review (test-writer role), 2026-11-25: docs/keywords/GOTO.md, GOSUB.md, RETURN.md

**Run-file records decoded.** I decoded all 30 six-byte records of `scratchpad/KGS_run1.out` (FX, ref and zb) myself,
by slicing the hex at `1 + 6*i` with a Python one-liner. Then I compared each one with `kgosub_model.T`. The two
captures are byte-identical, and every record equals its T entry. I also decoded the pre-fix capture from git
(`dc78e1990:scratchpad/KGS_run1.out`). Its ref side is identical to today's. zb differs only on KGS FX 7 and FX 28:
`02 02 00 00 00 00` against the reference's `00 00 00 00 04 00`.

I took the statements of each case from `FX` in `kgosub.py`. I did not print the typed program (`--lines`), so the
typed line numbers are my arithmetic: base n = 2000 + 30·i. I did not read `ramrec.measure`, any `kwdoc_*.out`,
`gosubedge_*.out`, or the D-RETLN / D-FORRET / lnref documents. Claims below that cite those documents are judged only
on whether a KGS case is behind them.

## 1. Rules not pinned by any measured case

1. **R-RETURN-BACK, "RETURN n … dropping the GOSUB".** In KGS FX 17, line n+10 falls straight into the record line,
   so nothing after the jump looks at the frame. Under "RETURN n is a plain GOTO that keeps the frame", the record is
   the same `(0,0,0,0b1100)`. Case: sub line n+5 `WP%=WP% OR 4:RETURN {L10}`, line n+10
   `WP%=WP% OR 8:RETURN`. If the frame is dropped, the record is error 3 with p=0b1100. If it is kept, the record is
   p=0b1110 with no error.
2. **R-RETURN-ERRORS, "RETURN n to a line that does not exist is error 8".** The page's Details adds "the subroutine
   has already been closed", and KGS FX 18 cannot see that. After RESUME NEXT, the end of line n+5 falls into n+25.
   Case: sub line `WP%=WP% OR 4:RETURN 65000:WN%=WN%+1:RETURN`. If the frame was closed, the record is e=8, f=3,
   WN=1. If it was kept, it is e=f=8, WN=1, p=0b0110.
3. **R-RETURN-ERRORS, "RETURN with no GOSUB pending is error 3".** Only the bare form was measured (FX 16). RETURN.md
   says the no-GOSUB check comes before the line number is read. Case: line n `RETURN 65000` with nothing open gives
   3 under "checked first" and 8 under "line first". Also measure `RETURN WK` with nothing open (3 against 2).
4. **R-GOTO-ERRORS, "a number followed by more text (`GOTO n 7`, read as one number)".** The joined number 22457 is
   not a line, so FX 8 gives error 8 under "one number" and under any "a tail makes it undefined" reading alike. No
   case has a joined number that exists. Case (FX 8's block, base 2240): `GOTO 224 5`. Under "one number" it reaches
   line 2245, p=0b100, no error. See 5.3.
5. **R-GOTO-ERRORS, "also a number past 65529".** One value was measured (65530). The page's own Details give a
   different mechanism: the number is split at 65529, so `GOTO 70000` is `GOTO 7000` plus a stray `0`. Both rules
   give 8 on 65530, because there is no line 6553. Case: a line 6553 (free; the case blocks end at 2900) that sets a
   bit, then `GOTO 65530`. A split jumps to 6553; "too big is undefined" gives 8. `GOTO 70000` with a line 7000 does
   the same for the Details example.
6. **R-GOTO-GOTO, "`GO TO` … is GOTO -- also after THEN".** Only statement start and after `THEN` were measured. The
   D-GOTOSPACE commit says the form is a tokenizer synonym. If so it applies everywhere a GOTO token is legal, and
   also where it is not: the commit's own example, `FOR I=GO TO 3`, becomes a Syntax error. None of these is a KGS
   case. Cases:
   - `IF 1 GO TO {L5}` (IF without THEN, which GOTO.md's Syntax lists);
   - `ON 1 GO TO {L5}`;
   - `ON ERROR GO TO 800` inside a case;
   - `GO=1:FOR WK=GO TO 3:WN%=WN%+1:NEXT`, where a variable `GO` is broken by the synonym. GO alone (FX 29) does not
     show that.
7. **R-RETURN-FRAMES, "drops EVERY FOR frame opened since its GOSUB".** FX 22 opens one FOR. A sub with two (`FOR
   I=1 TO 3:FOR J=1 TO 2:RETURN`, then `NEXT J` or `NEXT I` after the GOSUB) separates "drop all" from "drop the
   innermost". The rule also says only "a NEXT": every NEXT here is bare. `NEXT I` searches by variable, so the
   second clause needs `NEXT I` in FX 24's sub as well: error 1 against reaching the outer loop.
8. **R-GOSUB-CALL, "RETURN continues after the GOSUB, on its own line".** A GOSUB inside a THEN clause with a
   statement after it was never measured. FX 11's GOSUB is the last thing on its line. Case: `IF 1 THEN GOSUB
   {L5}:WP%=WP% OR 2` (sub `RETURN`). It shows whether the rest of the THEN clause runs after the return.
9. **R-GOSUB-ERRORS, "a line that does not exist is error 8".** Whether a frame is pushed before the error is not
   pinned. FX 12 resumes straight into `GOTO n+25`. Case: `GOSUB 65000:WN%=WN%+1:RETURN`. With no frame the record
   is e=8, f=3, WN=1. With a frame it is WN=2.

## 2. Model special-cases that hide a rule

`expect()` returns `T[c.why]`, a constant tuple per case title. It never reads the case's statement, so every check is
"this case has this record". The rules' sentences generalize from single tuples as follows.

1. **R-GOTO-ERRORS, "a number followed by more text" is error 8.** T has one digit tail, `(8,8,0,0)`. GOTO.md's
   Details says `GOTO 100 ZZ` is accepted and jumps. So the rule's general wording is false by the page's own
   account for a non-digit tail, and the table cannot show it. The sentence should say "a DIGIT after a space".
2. **R-GOTO-ERRORS, "a number past 65529".** T has one value. The check is the constant `(8,8,0,0)`, so changing
   the probe to `GOTO 99999` (stored as 34463 before D-LNREF) would leave the check unchanged. A constant answer is
   not the rule's answer (see 1.5).
3. **R-GOSUB-CALL, "GOSUBs nest and recurse (five deep, each level falling through to the RETURN)".** T's
   `(0,0,5,0)` for FX 11 is also the record under "the first RETURN unwinds every GOSUB". That RETURN lands back on
   line n after `WN%=5` and runs `GOTO n+25`: WN=5, p=0, no error. So the "five deep" clause is pinned only by FX 10
   (two deep). Nothing in the record counts the levels on the way out.
4. **R-GOSUB-CALL, "recursion without a RETURN runs on".** T holds `GUARD`=21. The sentence reads as "unbounded",
   but GOSUB.md's Details and Errors say it ends in error 7 (see 4.5 and 5.2).
5. **R-RETURN-BACK, "dropping the GOSUB".** FX 17's tuple is the same whether the frame is dropped (1.1).
6. **Shared keys.** "a line that does not exist" and "no line number" are one T entry each. GOTO's case and GOSUB's
   case both read them. The table cannot state that GOTO 65000 and GOSUB 65000 differ without renaming a case. A
   future one-sided divergence would surface, but the rule could not be rewritten to fit it.
7. **Coverage "52 / 32 / 36 read by a rule's check, 0 unread"** is automatic. Each check reads all four fields as one
   tuple, so full field coverage says nothing about which field a sentence actually explains. For example, the
   p=0b10 of FX 26 (`GO SUB`: RESUME NEXT ran the rest of line n) appears in no rule sentence.

## 3. Controls that are too weak

1. **Three rules have no control at all:**
   - R-GOSUB-CALL and R-GOSUB-ERRORS. GOSUB.md says "none yet … each rule here states measured values the model
     reproduces exactly". That is the defect spec-method §3a's controls exist to catch, not a reason to skip them.
   - R-GOTO-JUMP. A rival "GOTO to its own line continues after the GOTO" would be false on FX 2 (WN=1 instead of 21),
     but nobody wrote it.
   - R-RETURN-ERRORS.
2. **Five of six controls are false on exactly ONE case.** Only `no-goto-space` reaches two (FX 7, FX 28).
3. **The rival tuples are typed by hand, not derived.** "FALSE on 1" is therefore guaranteed by writing any tuple
   other than T's. `return-keeps-for` predicts `(0,0,3,0b10)` for FX 22. The rival it names (zerobas's pre-D-FORRET
   separate stacks) gives something else:
   1. RETURN pops the GOSUB.
   2. `WP% OR 2`.
   3. NEXT jumps back into line n+5, so WN=2.
   4. RETURN finds no GOSUB, so error 3.
   5. RESUME NEXT falls into n+25, giving `(3,3,2,0b10)`.

   The control passes, but against a straw rival. I checked the other five against the rule they name:
   - `no-goto-space` matches the pre-fix zb record of FX 7 and FX 28 exactly;
   - `next-crosses-gosub`'s `(0,0,2,0)` and `return-line-ignored`'s `(0,0,0,0b0110)` match my hand trace;
   - `big-line-syntax` and `trailing-syntax` are plausible.
4. **Plausible rivals that NO case separates** (each from section 1):
   - RETURN n keeps the frame (1.1);
   - RETURN n to a missing line keeps the frame (1.2);
   - RETURN n with nothing open checks the line first (1.3);
   - digits joined vs. "a tail makes it undefined" (1.4);
   - split at 65529 vs. "past 65529 is undefined" (1.5): the page states the first and the rule the second;
   - `GO TO` as a tokenizer synonym vs. a statement-level form (1.6);
   - drop all inner FORs vs. drop the innermost (1.7);
   - GOSUB to a missing line pushes a frame (1.9);
   - RETURN unwinds all GOSUBs, which only FX 10 separates and which has no control written (2.3).

## 4. Page claims with no case behind them, or that contradict the record

**GOTO.md**
1. **Status (line 14-16): "No recorded difference since the `IF … GOTO` form was fixed on 2026-10-24".** The first
   KGS run (`dc78e1990`) recorded one. FX 7 and FX 28 were `(2,2,0,0)` on zerobas against `(0,0,0,0b100)`. Differences
   (line 150) itself names D-GOTOSPACE. "What we found" has no D-GOTOSPACE entry, and the before-record is reachable
   only through git, because `KGS_run1.out` was overwritten.
2. **Details (line 38-39): "Anything after the line number is never reached, so `GOTO 100 ZZ` is accepted".** FX 8
   contradicts it for a digit tail: the `7` is reached and joined, and the result is error 8, not a jump (p=0). The ZZ
   example itself has no KGS case.
3. **Details and Errors, `GOTO 70000` → read as 7000.** There is no KGS case for it, and the rule states a different
   mechanism (1.5).
4. **Errors table, `GOTO "A"` and `GOTO -1` → 2.** No KGS case. Syntax's `IF <condition> GOTO <line>` form has no
   case either (1.6).
5. **Evidence paragraph, "1 line n" as a WP% bit.** Only FX 0 sets bit 1. Every other case leaves it clear, so the
   bit legend says more than the probe writes (see 5.6).

**GOSUB.md**

6. **Errors table vs. its own sentence and the rule.** The table lists 7 `Out of memory`, yet "the whole set …
   is {2, 8}". R-GOSUB-CALL says unbounded recursion "runs on … no error". The Details sentence "ends in
   `Out of memory`" rests on no KGS case: the guard stops FX 15 at 21 (5.2). Open admits the limit is unmeasured, but
   the Status line still says "every error ✓".
7. **Details, "Anything after the line number in the same statement is ignored … `GOSUB 100 ZZ` … a `:` statement
   after it still runs".** No KGS case. If GOSUB reads its number as GOTO does, `GOSUB {L5} 7` is joined (FX 8's
   rule), so "anything" is too broad. Cases: `GOSUB {L5} 7` and `GOSUB {L5} ZZ:WP%=WP% OR 2`.
8. **Errors table, `GOSUB 70000`, `GOSUB "A"`, `GOSUB -1`.** No KGS case. R-GOSUB-ERRORS has no line past 65529, no
   variable, and no tail for GOSUB at all.
9. **Details, the `ON n GOSUB` paragraph** (truncation, `ON 0`, error 5, error 6). No KGS case, and unlike GOTO.md the
   Open list does not name ON … GOSUB.
10. **Status date (2026-10-16) predates the spec (2026-11-25).**

**RETURN.md**

11. **Details, "`RETURN <line>` is a `GOTO` with the subroutine closed first".** No case separates closed from kept
    (1.1).
12. **Details, "checked before the line number is even read, so `RETURN 99` and `RETURN B` with nothing open are
    error 3".** Only the bare form was measured (1.3).
13. **Details, "the subroutine has already been closed, and the error is reported against the `RETURN`'s own line".**
    FX 18 can see neither: the frame is not observed (1.2), and ERL is not recorded (5.4).
14. **Details and Errors, `RETURN "A"` → 2, and `RETURN B` closes the subroutine.** No KGS case. The line form's error
    set {2, 3, 8} has no measured 2.
15. **Details, "cannot be used to leave an `ON ERROR` handler … error 3 on both".** It is stated as fact, while Open
    lists "RETURN inside an ON ERROR handler" as [A] not measured. One of the two is wrong for this spec's evidence.
16. **Details, "`RETURN` at the end of an `ON KEY`/`ON INTERVAL` handler switches that trap back on".** No KGS case and
    no Open entry.

## 5. Probe-apparatus risks

1. **The frame uses the keyword under test** (spec-plan §1: "the readout must not use the keyword under test, nor
   its family"):
   - every case ends `:GOTO n+25`;
   - the guard is `ON … GOTO`;
   - line 10 is `GOTO 2000`;
   - every GOSUB case's return lands on that `GOTO`.

   FX 0's "the rest of the line is skipped" is the same mechanism the frame relies on to reach its record. Today both
   machines agree, but a GOTO that fell through would corrupt the frame and the subject together.
2. **The `WN%>20` guard masks the recursion limit.** FX 15 can only ever record WN=21. Error 7 (GOSUB.md's Details and
   Errors) lies thousands of levels deeper, so the guard turns "ends in Out of memory" into "runs on, no error"
   (4.6). The guard in FX 23 and FX 24 is harmless: WN stays at 3 and 1.
3. **Two geometries cannot reach their claim:**
   - **FX 8.** Every joined number of the form `n+5` followed by a digit is 5 digits from 20057 to 28757. No line
     exists there, so "read as one number" can never show a jump (1.4).
   - **FX 4.** The split prefix of 65530 is line 6553, which the program does not have (1.5).
4. **No ERL.** spec-plan §1 lists ERL "where the line matters" as an output. RETURN.md's "reported against the
   RETURN's own line" and GOTO's "split" have no witness.
5. **Fall-through into the record hides state after an error or a jump.** Cases 12, 17, 18 and 24 end on the line
   before n+25, or resume into `GOTO n+25`. The GOSUB/FOR frames are never examined afterward (1.1, 1.2, 1.9).

   Only the first and last error are kept. Every recorded error case has e = f, so a middle error between two equal
   ones (for example 1, 3, 1) would be invisible. An error count byte would close that.
6. **No sentinels.** WE, WF, WN% and WP% all start at 0, the "nothing happened" value (spec-plan §1: "every case starts
   with its output holding a sentinel"). Bit 1 ("line n ran") is written only by FX 0. So for the other 29 cases, "line
   n never ran" is not told apart from "line n ran and set nothing" by a bit. Errors or WN% witness it only
   indirectly, and a record like FX 11's `(0,0,5,0)` relies on WN% alone.
7. **One positive witness.** FX 16 (bare RETURN gives 3) directly follows FX 15, which leaves 21 GOSUB frames open.
   That shows each case's `CLEAR` drops pending frames on both machines, so the cases are independent.

**Findings: 44** (section 1: 9, section 2: 7, section 3: 4, section 4: 16, section 5: 8; this counts each named
sub-claim of 5.3 and 5.5 separately, and leaves out 5.7, which is not a defect). The most important are:
- 1.1, 1.2 and 4.11 to 4.13: RETURN n's frame handling is stated but never observed;
- 1.4, 1.5 and 5.3: GOTO's tail and 65529 rules sit on geometry that cannot separate the rivals;
- 4.1: GOTO's Status line denies the difference this very probe found;
- 4.6 and 5.2: GOSUB's error 7 is contradicted by the error set and masked by the guard;
- 3.1: GOSUB has no control.
