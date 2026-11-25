# Goldfish review (test-writer role), 2026-11-25: docs/keywords/ERROR.md, ERR.md, ERL.md, RESUME.md (with ON ERROR GOTO)

**Records read.** I dumped all 40 `FX` screens of `scratchpad/KER_run1.out`, both `ref` and `zb`, and read each one. Only
KER FX 34 differs. I read `kerr.py`, `kerr_model.py`, `kerr_controls.py`, the four `*_rules.py`, all of `kstop_model.py`,
`kstop.py`'s `MACHINES` / `normalise` / `measure`, and the `batch=` docstring of `omsx_repl.run_cases`. I did **not** run
the model or the controls. Every model prediction below is my hand trace of `kstop_model.Basic`. I did not read
`docs/spec-method.md`, `spec-plan.md`, the `kwdoc_*.out` example runs, or any acceptance suite.

**Read this first.** Every rule's check is the same function, `kstop_model.ok`: the whole predicted screen against the
whole recorded screen. A rule is therefore only a selection of cases (`by(why…)`). A ✓ means "the interpreter predicted
these screens". It does not mean that each clause of the sentence was exercised. Several clauses below are ✓ with no
case able to fail them.

## 1. Rules and clauses not pinned by any case

1. **R-RESUME-HANDLER / ERL.md: `No RESUME` names "the last line that ran, not the handler's first line".** KER FX 27
   and 28 have a one-line handler (`100 PRINT "[H]"`), so the last line that ran *is* the handler's first line. This is
   the trap ERL.md's own "What we found" records for D-ERR21 ("the two answers could not be told apart"), set again. To
   separate the two readings: `10 ON ERROR GOTO 100` / `20 X=1/0` / `100 PRINT "[H]"` / `110 PRINT "[I]"` / `RUN` /
   `PRINT ERR;ERL`. That gives `No RESUME in 110`, `21  110`, against `in 100`.
2. **R-RESUME-ONERROR: "GOTO n there arms n and goes on".** In KER FX 33 the handler arms 200 and RESUMEs NEXT into
   `PRINT "[B]":END`. No second error ever happens, so `[I]` never prints. The rival "ON ERROR GOTO n inside a handler is
   ignored" gives the same screen (`[H]`, `[B]`). Add a second error:
   `20 X=1/0:Y=1/0:PRINT "[B]":END` (expect `[H]`, `[I]`, `[B]`).
3. **R-RESUME-ONERROR: GOTO 0 "re-raises", against "re-runs the failing statement".** In KER FX 30, re-running
   `X=1/0` with the trap off also prints `Division by zero in 20`. RESUME.md says the re-run reading "was rejected by a
   row", but KER has no such row. Make the cause fixable: `20 X=1/D:PRINT "[B]":END` / `100 D=1:ON ERROR GOTO 0`. A
   re-raise stops with the message; a re-run prints `[B]`.
4. **ERR.md / RESUME.md "every RESUME sets ERR back to 0, ERL kept".** Only RESUME NEXT reads ERR afterwards (FX 15,
   35). FX 19, 20 and 24 (bare RESUME, RESUME 0, RESUME n) never print ERR or ERL. The rival "only RESUME NEXT clears ERR"
   is unseparated. Pin it with `30 X=1/D:PRINT "[";ERR;ERL;"]":END` in FX 19/20 (expect `[ 0  30 ]`) and with
   `40 PRINT "[";ERR;ERL;"]":END` in FX 24 (expect `[ 0  20 ]`).
5. **ERR / ERL after RUN, CLEAR, NEW and an edit** (Open on all four pages). The model keeps `err`/`erl` through
   `reset()`, NEW and edits, which is an unstated law (2.2). Pin it with these lines:
   - `10 PRINT ERR;ERL` / `20 X=1/0` / `RUN` / `RUN`: the second run's first line shows whether RUN clears;
   - `10 X=1/0` / `RUN` / `CLEAR` / `PRINT ERR;ERL`;
   - the same with `NEW`;
   - the same with `20 REM`.
6. **The handler's state after an *untrapped* stop.** The model never clears `handler` after an error inside the handler
   (FX 29), after `No RESUME` (FX 27), after RESUME to a missing line (FX 25), or after the GOTO 0 re-raise (FX 30). So
   the model predicts that a typed RESUME afterwards **resumes the program**. No case types one. Append `RESUME NEXT` to
   FX 27 (model: `[C]`), to FX 29 (model: `[B]`) and to FX 25. Whichever way the reference answers, it is a law.
7. **Nested GOSUB / FOR and the handler.** The model's RESUME leaves `stack` untouched. Nothing pins that.
   - An error inside a GOSUB, then RESUME NEXT, then RETURN: `10 ON ERROR GOTO 100` / `20 GOSUB 50:PRINT "[R]":END` /
     `50 X=1/0:PRINT "[S]":RETURN` / `100 RESUME NEXT` / `RUN`.
   - A GOSUB *in* the handler whose subroutine RESUMEs, so a frame may leak: `20 X=1/0:PRINT "[B]"` / `30 RETURN` /
     `100 GOSUB 200:PRINT "[X]":END` / `200 RESUME NEXT`. The model predicts `[B]` and then `[X]` via the leaked frame;
     the rival predicts `RETURN without GOSUB in 30`.
   - A FOR opened in the handler and used after RESUME: `20 X=1/0` / `30 NEXT` / `100 FOR I=1 TO 2:RESUME NEXT`.
   - An error inside a FOR body, then RESUME NEXT, then NEXT: `20 FOR I=1 TO 3:X=1/0:PRINT I;:NEXT`.
8. **RESUME NEXT when the failing statement is the last of the program / of a typed line** (RESUME.md Details). No KER
   case covers it, because every failing statement has a successor. In program form the handler has to come first, or
   RESUME NEXT runs into the handler: `10 ON ERROR GOTO 30` / `20 GOTO 40` / `30 RESUME NEXT` / `40 X=1/0` / `RUN`.
   Typed form: FX 36's program, then `PRINT "[A]";:X=1/0`.
9. **RESUME (retry) and RESUME n for an error typed at the prompt.** Only RESUME NEXT is measured from a typed line
   (FX 36). Retry: `10 ON ERROR GOTO 100` / `20 END` / `100 D=1:RESUME` / `RUN` / `D=0:PRINT 1/D:PRINT "[T]"`.
   RESUME n jumping from a typed line into the program: `100 RESUME 30` with `30 PRINT "[C]":END`.
10. **ERROR in direct mode with a handler, then more statements.** FX 11 ends its handler with END. Use
    `100 PRINT ERR;ERL;:RESUME NEXT` and type `ERROR 7:PRINT "[T]"`.
11. **Errors in the handler's own RESUME line.** Measured so far: only `RESUME 99` (FX 25), and an error *before*
    RESUME (FX 29). Unmeasured:
    - `100 PRINT "[H]";:RESUME NEXT X` (is the syntax checked before or after the handler is left? If after, the error
      re-enters the handler and may loop: give it a counter);
    - `100 RESUME NEXT:PRINT "[Z]"` (statements after RESUME never run);
    - `100 RESUME A`.
12. **Trap interplay (ON KEY / ON INTERVAL)** (Open). The model has no traps. ON INTERVAL needs no keypress:
    `10 ON ERROR GOTO 100:ON INTERVAL=1 GOSUB 200:INTERVAL ON` / `20 X=1/0:PRINT "[B]":END` /
    `100 FOR I=1 TO 300:NEXT:PRINT "[H]";:INTERVAL OFF:RESUME NEXT` / `200 PRINT "[T]";:RETURN`. Does `[T]` appear
    inside the handler?
13. **ON ERROR GOTO A outside a handler, and a bare `ON ERROR GOTO`.** RESUME.md states both ("is the same as ON ERROR
    GOTO 0"). Only the in-handler variable form is measured (FX 34). Pin them with `10 ON ERROR GOTO 100` /
    `20 ON ERROR GOTO` / `30 X=1/0` / `100 PRINT "[H]":RESUME NEXT` / `RUN`, and the same with `20 ON ERROR GOTO A`.
14. **R-ERROR-CODE "past 65535 error 6".** Only 70000 is measured. See 4.3: 40000 and -32769 decide where the bound
    really is.
15. **ERR and ERL after the GOTO 0 re-raise, and CONT after it.** ERL.md says the re-raise keeps "its original line",
    but only the message is on the screen (FX 30). Append `PRINT ERR;ERL` / `CONT`. Under the model, the re-raise leaves
    no CONT point (`Can't CONTINUE`), where a plain untrapped error does leave one (2.4).

## 2. Model laws no rule states; rule clauses the model does not compute

1. **"RESUME's own error is never trapped" is coded as "error 22 is never trapped"** (`trap = e.n != 22`). The model
   therefore predicts that `ERROR 22` under an armed handler is **untrapped** (`RESUME without error in 20`). That
   contradicts R-ERROR-RAISE's own sentence ("a handler sees ERR = n"). Separating case: `10 ON ERROR GOTO 100` /
   `20 ERROR 22` / `100 PRINT "[";ERR;"]":END` / `RUN`. Under the rule sentence it prints `[ 22 ]`; under the model,
   the message. One of the two is wrong.
2. **ERR / ERL survive RUN, CLEAR, NEW and edits** (`reset()` does not touch them). No rule says so, and no page says
   so; it is an Open item (1.5).
3. **The handler point survives every untrapped stop** (1.6). It is cleared only by END, RESUME, RUN, CLEAR, NEW and an
   edit (`reset()`). That makes an edit while stopped in a handler end it: also unstated and unmeasured.
4. **The GOTO 0 re-raise sets no CONT point**, while the ordinary untrapped error sets `cont = pt`. The re-raise also
   prints the message alone when `erl == 65535` (a typed error re-raised), with no case. Both are unstated laws.
5. **`msg()` is a 15-entry table that defaults to `Unprintable error`.** The model therefore predicts
   `Unprintable error` for ERROR 4, 9, 12, 14, 15, 16, 18, 19, 20, 25 and others. That is wrong by ERROR.md's own claim
   (every message is the reference's text). The rule clause "a code with no message of its own prints `Unprintable
   error`" is computed by an incomplete table, and holds only because the cases use 200, 7 and 11. Either complete the
   table or narrow the clause.
6. **ERROR's argument order.** The model tests `","` first and returns error 2 before looking at the value. ERROR.md's
   table says `ERROR 300,1` and `ERROR -1,1` are **5** ("refused before anything else is looked at"); the model predicts
   2. The model contradicts the page on two rows that no KER case measures. Add `10 ERROR 300,1` / `RUN`.
7. **R-ERR-SYNTAX is computed by the parser's catch-all, not by an ERR law.** `value("ERR 1")` falls through every
   regex to `raise Err(2)` ("a form this BASIC does not read"). Any unparsed expression gives 2, so the rule can only
   fail if the reference gives something other than 2. The same catch-all yields ERROR.md's `ERROR 1 X` → 2. The rule
   has no control (3.1).
8. **"A `:` inside a string" is a `split()` law, not a RESUME law.** RESUME NEXT uses the same statement splitter as
   everything else, so the byte-scan rival behind D-RESNEXTOVF (stop at any `0x3A`) cannot be expressed as an `alt`.
9. **Rule clauses the model cannot compute.**
   - ERL.md: a line the editor refuses (`70 X=1E99`, `70000 X=1`) leaves ERL 65535. `type()` stores every numbered
     line.
   - RESUME.md: `MAXFILES` disarms. There is no MAXFILES.
   - ERROR.md: messages "letter for letter" (2.5).

   None of these is in a rule sentence, so no rule is wrong, but none is executable either.

## 3. Weak controls and unseparated rivals

1. **Rules with no control at all.**
   - **R-ERR-SYNTAX.** Rival: "ERR takes no argument; the rest is ignored".
   - **R-ERROR-RAISE's "Unprintable error" clause.** Rival: an unknown code prints nothing, or its number.
   - **R-ERR-VALUE's "0 before any error".**
   - **ERL in a program equals the failing line.** Rival: the handler's line, or the line of ON ERROR. This is under
     R-ERR-VALUE only via FX 12 and 15. ERL.md's own rule table has no program-ERL rule at all.
2. **Clauses with a separating case but no control.**
   - RESUME 0 = RESUME. Rival "RESUME 0 is RESUME line 0": FX 20 separates.
   - RESUME n. Rival "= RESUME NEXT": FX 24 separates.
   - The handler catches again after RESUME. Rival "RESUME leaves it disarmed": FX 35 separates.
   - RUN inside a handler ends it. Rival "the handler stays active": FX 37 separates.
   - GOTO 0 outside a handler disarms. Rival "ignored outside a handler": FX 32 separates.

   Each is a cheap `alt` and would make the clause shown able to fail.
3. **"RESUME to a missing line stops silently -- zerobas's" is mislabelled.** RESUME.md's own history (D-RESUMEMISS)
   says zerobas **hung** (the handler re-entered for ever). It did not stop silently. The control is a fine rival, but
   it is not zerobas's rule. The model cannot express a hang at all (5.2).
4. **Unseparated rivals in the current cases:**
   - FX 33: GOTO n in a handler arms, against is ignored (1.2);
   - FX 30: re-raise, against re-run (1.3);
   - FX 27/28: the last line that ran, against the handler's first line (1.1);
   - FX 19/20/24: every RESUME clears ERR, against only RESUME NEXT (1.4);
   - the error-22 law: RESUME's own error, against code 22 (2.1).
5. **"an error typed at the prompt never reaches a handler"** is listed twice, under R-ERROR-RAISE and
   R-RESUME-HANDLER. That is fine, but the second listing's "FALSE on 2" (FX 36, 38) and the first's FX 11 are the
   *only* three typed-with-handler cases. None of them retries or uses RESUME n (1.9).

## 4. Page claims with no case, or contradicted by the record

1. **RESUME.md Summary: "zerobas behaves like the Philips VG-8020 in every case we have measured".** The record
   contradicts it at KER FX 34 (`Syntax error in 100` against `Division by zero in 20`), and the page's own Differences
   section and rule table say so too.
2. **RESUME.md Differences: "the set of errors RESUME itself can raise has not been measured, because the tool … got
   no reading for any RESUME case on the VG-8020".** It is stale: KER FX 25 (8) and FX 26 (22) are VG-8020 readings of
   RESUME's errors. The Status line says "every error ✗ (D-ONERRVAR)", but this paragraph says "not yet proven". They
   cannot both be the reason.
3. **ERROR.md disagrees with itself about the overflow bound.** The rule R-ERROR-CODE (and the model, `<= 65535`) says
   "past 65535 error 6". "What we found" (D-ERRORARG) says "a value past 32767 is `Overflow`". FX 8 (70000) satisfies
   both. `10 ERROR 40000` / `RUN` separates them: 6 under "past 32767", 5 under "past 65535". Add `ERROR -32769` too.
4. **ERROR.md table rows with no KER case:** `ERROR 300,1`, `ERROR -1,1` (and the model contradicts them, 2.6),
   `ERROR 0,1`, `ERROR 1 X`. They rest on `errorarg_run.out`, not on this probe.
5. **ERROR.md "`ERROR 21` and `ERROR 22` print `No RESUME` and `RESUME without error`".** There is no case, and 2.1
   makes ERROR 22 under a handler a live question.
6. **ERROR.md "Measured on the VG-8020 for 23 and 26, and for 60 to 64".** KER measures only 200. These rest on
   msgexact / errtxt60 and are not KER cases.
7. **ERL.md, three claims with no KER case:**
   - the editor-refusal 65535 (`70 X=1E99`);
   - `A=ERL 1` is error 2 (only `A=ERR 1`, FX 18, is measured);
   - "ON ERROR GOTO 0 … re-raises … with its original line": only the message is read, never ERL (1.15).
8. **ERL.md "`No RESUME` sets ERL to the last line that ran".** FX 28 reads `21  100`, but cannot tell this rule from
   "the handler's line" (1.1).
9. **RESUME.md "The handler is disarmed whenever the variables are cleared: RUN, NEW, CLEAR (and MAXFILES), and
   editing".** KER measures none of these. RUN is in kstop's "RUN resets ON ERROR"; NEW, CLEAR, MAXFILES and edits are
   in neither probe. Example: `10 ON ERROR GOTO 100` / `20 CLEAR` / `30 X=1/0` / `100 PRINT "[H]":END` / `RUN`.
10. **RESUME.md "ON ERROR GOTO with nothing after it is the same as GOTO 0"** has no case (1.13).
11. **The Open line on all four pages** lists GOSUB/FOR in the handler, ERR/ERL after RUN and CLEAR, and ON KEY. It
    omits NEW, edits, ERROR 22 under a handler, typed RESUME after an untrapped stop, RESUME retry from a typed line,
    and the 32767/65535 bound.

## 5. Probe-apparatus risks

1. **One whole-screen check for every rule** (see the top of this file). The header's "every recorded output is read
   by one" holds by construction, because each case has one field. A zerobas ✗ cannot be attributed to a clause: FX 34
   fails R-RESUME-ONERROR as a whole. The `by(why…)` selectors key on prose strings. A reworded `why` drops a case from
   its rule, and only the "0 unread" count would catch it.
2. **A hang cannot be predicted.** `run_from` has `budget=400`, and when it runs out `type()` still appends
   `<prompt>`. A rival that loops (`handler-traps-own`, zerobas's old RESUME 99) is therefore modelled as a clean stop
   with a prompt, while the machine shows no prompt. The control is FALSE for the wrong reason (the screen differs, but
   not because of a modelled hang). 1.11's `RESUME NEXT X` could hang either machine; give such cases a counter.
3. **"Before any error" (FX 14) depends on boot-per-case.** `measure()` passes `batch=False`, but `omsx_repl.run_cases`
   lets `$ZB_BATCH=1` force batching. Under batching, ERR/ERL would leak from the previous case (unless NEW clears them,
   which is exactly the unmeasured 1.5), and FX 14 would read the earlier case's values. That is a plausible-looking
   divergence. Assert the mode in `kerr.measure`, or make FX 14 independent of it.
4. **Normalisation.**
   - Any screen line equal to `Ok` or `ZB` becomes `<prompt>`, so a case PRINTing those would be misread. None does
     today.
   - Program output is not wrapped by the model (`WIDTH=37` applies only to the echo; the machine wraps at 40). An
     output line over 37–40 characters (FX 35's line is 19) would break the prediction. That is a limit to respect when
     adding the cases above.
5. **The model's grammar is narrow** (regexes for `X/Y`, `X+n`, `FOR v=a TO b`, `IF v[=n] THEN`). Several of the
   section-1 cases (`PRINT ERR;ERL;` with a trailing `;`, `GOSUB` in a handler, `INTERVAL`, `ERROR 300,1`) need parser
   additions first. Without them they would hit the catch-all error 2, a plausible *wrong* prediction (2.7). Grow the
   parser before reading a ✗ on a new case.

**Finding count: 15 + 9 + 5 + 11 + 5 = 45** (sections 1–5). The most load-bearing: 1.1 (the D-ERR21 trap repeated),
1.2, 1.3, 2.1 (error 22 against R-ERROR-RAISE), 2.6 and 4.3 (ERROR argument order and bound), 4.1/4.2 (stale RESUME.md
statements).
