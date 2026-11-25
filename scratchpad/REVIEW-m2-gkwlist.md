# Goldfish review (test-writer role), 2026-11-25: docs/keywords/NEW.md, LIST.md, DELETE.md, RENUM.md

**Records read.** I decoded all 39 `FX` screens of `scratchpad/KNL_run1.out`, ref and zb. Ref and zb are identical in
every case. Model `ok()` holds on all 39 ref and all 39 zb screens. `klist_controls.py` runs green: 17 controls, each
FALSE on 1–3 cases. I also ran `kstop_model.run()` on typed lines that the probe never measured. Those runs say what
the MODEL would predict, not what either machine does; I quote them below as "model: ...". I did not read the
`kwdoc_*.out`, `listflt_probe2.out` or `*-characterization.md` records the pages cite. Every claim below that rests
on them is unchecked by me.

Most findings come from one structural fact: kstop_model's small BASIC now carries LIST / DELETE / RENUM laws
(`range()`, `spell()`, `renum()`, `rerefs()`). Several of these laws are not the ones the pages' Details state, and the
39 cases do not reach the places where they differ.

## 1. Rules (and page claims) not pinned by any measured case

1. **LIST.md, R-LIST-RANGE `.` = "the last line LIST printed".** Case FX 15 runs `LIST 20` / `LIST .`, and `LIST 20`
   prints ONE line. So "last printed", "first printed" and "LIST's own argument" all agree there. Separate them with
   P4 / `LIST 15-35` / `LIST .`: last printed gives 30, first printed gives 20, the argument (15) gives nothing.
   - "A LIST that printed nothing leaves `.` alone" (Details) has no case. Run P4 / `LIST 20` / `LIST 25` / `LIST .`.
   - "`.` is the line the editor last touched" (Syntax) has no case either. Run P4 / `LIST .` before any LIST. If the
     page is right this prints 40. The model prints nothing (see 2.1).
2. **LIST.md, R-LIST-SPELL and the Details paragraph.** Only one case exists (FX 16: `.5`, `1500#`, `.123456789#`).
   Details states `40000!`, `2E-05`, `1.5E+20` (a double losing its `#`) and "below .01 in `E` form". No KNL case covers
   any of these, and the model predicts every one of them differently (2.2). Cases that would pin them:
   - `10 A=40000:B=1E3:C=1.0:D=1.:E=2E-5:F=1.5D20:G=.005` / `LIST`.
   - The digit threshold: `0.1234567` (7 digits) against `0.123456` (6 digits). The rival thresholds "more than 7" and
     "more than 8" agree on the one 9-digit case.
   - `1.000000` (trailing zeros counted?), `&H10` / `&O17` / `&B101` (must stay as typed), and `1E+3` (a signed
     exponent).
3. **RENUM.md, R-RENUM-REFS: THEN, ELSE, RUN, and references in lines left alone.** These are stated in Details and in
   the model's docstring, but only GOTO, GOSUB, RESTORE and an ON GOTO list were measured (FX 35, 30–32). FX 32's
   kept line 10 contains no reference.
   - Run `1 IF A THEN 2 ELSE 3` / `2 RUN 3` / `3 RESUME 2:RETURN 2` / `RENUM` / `LIST`. (Use 1, 2, 3, not 10, 20, 30.
     On a program already numbered 10, 20, 30, RENUM changes nothing, which is the editverb lesson again.)
   - Run `10 GOTO 30` / `20 PRINT` / `30 PRINT` / `RENUM 100,20` / `LIST` (the kept line's reference must become 110).
4. **RENUM.md, "only real references": REM, DATA and `&H`.** FX 35's REM is `REM 9`, with no keyword before the 9,
   so no plausible rival rewrites it, and the REM clause is witnessed by nothing. Run
   `5 REM GOTO 7` / `6 DATA GOTO 7` / `7 A=&H0007:GOTO 7` / `RENUM` / `LIST`.
5. **RENUM.md, the error rows.** No KNL case covers "new numbers that would pass 65529 → error 5", "`RENUM 65530` →
   error 2" or "four arguments → error 2", and the model computes none of them (2.4). Run
   `10 PRINT 1` / `20 PRINT 2` / `RENUM 65529` / `LIST`, plus `RENUM 1,,65529`, `RENUM 65530` and `RENUM 10,1,10,7`
   (each followed by `LIST`). Also the one-line edge the page tells as a story: `10 PRINT 1` / `RENUM 65529`.
6. **RENUM.md, `Undefined line … in …` "once per such reference".** Only one missing reference was measured (FX 34).
   Run `1 GOTO 30:GOSUB 40` / `2 ON 1 GOTO 50,1` / `RENUM` to pin the count, the order (per line, then per position),
   and that a list reports each missing member. The claims "not an error: ERR stays 0, ON ERROR does not catch it" have
   no case. Run `1 ON ERROR GOTO 2` / `2 GOTO 77` / `RENUM` / `PRINT ERR`.
7. **RENUM.md, R-RENUM-CHECK: which overlap rule.**
   - Rule A (the model's): the new start must be above the last kept line.
   - Rule B: the new start must be ≥ the old start.
   - Rule C: no new number may equal a kept one.

   The measured cases (FX 32: 100,20; FX 37: 20,30) cannot separate A from B. Run P4 / `RENUM 25,30` / `LIST`: A gives
   10, 20, 25, 35 and B gives error 5. Run P4 / `RENUM 15,30` / `LIST`: A gives error 5 and C accepts it. Also untested:
   an old start that names no line (`RENUM 100,25` on P4), and an old start above the last line (`RENUM 100,50`).
8. **RENUM.md, `.` for either number, `RENUM:B=9` ending the line, and RENUM inside a running program stopping it.**
   None has a case. Run `10 PRINT 1` / `LIST 10` / `RENUM 100,.` / `LIST`, and `RENUM:PRINT "Z"`, and
   `10 RENUM 100` / `20 PRINT "B"` / `RUN` / `LIST`.
9. **DELETE.md, the Details table rows `DELETE 25` and `DELETE 10-65529`.** Neither is in KNL. The second is the case
   the page's own history calls decisive. FX 21 (`20-35` with a line 40) does already separate "must exist" from
   "not past the last line", so `10-65529` is a cheap second witness, not a missing pin.
10. **DELETE.md, "A refused DELETE ... keeps the variables and keeps the CONT point".** Every refused case (FX 21,
    23–26) runs on P4 without RUN, so there are no variables and no CONT point to lose. Run `10 A=5:STOP` / `20 PRINT A`
    / `30 REM` / `RUN` / `DELETE 20-35` / `CONT` (expect 5), and the same with `PRINT A`. The model predicts 5 (it raises
    before `reset`), but nothing measured it.
11. **DELETE.md, "a missing number counts as 0".** This is the page's EXPLANATION for why `DELETE 20-` and a bare
    `DELETE` are error 5. The model does not compute it (2.6). It separates only on a program with a line 0. Run
    `0 REM Z` / `10 PRINT "A"` / `DELETE 0-` / `LIST`, and the same with a bare `DELETE`. Under "counts as 0" both
    delete line 0; under the model's rule both are error 5. Also `DELETE -35` (a missing high end in the `-m` form).
12. **DELETE.md, inside a running program.** The Details claim that DELETE deletes and the program stops has no case.
    The Open item "DELETE of the line that is running" is right to be open. Run `10 X=1:DELETE 10` / `20 PRINT "Z"` /
    `RUN` / `LIST`, and `10 DELETE 20` / `20 PRINT "Z"` / `30 PRINT "Y"` / `RUN` / `LIST`.
13. **NEW.md, "arrays and strings included", "inside a program ... the variables go", `NEW "A"`.** FX 1 clears one
    numeric scalar, typed. FX 3 never reads a variable after the program's NEW. Run `10 A=5:A$="X":DIM B(3):B(1)=7:NEW`
    / `RUN` / `PRINT A;A$;B(1)`, and `NEW "A"`.
14. **NEW.md, a typed `NEW` followed by more statements.** "Anything after NEW is error 2" is pinned only by `NEW 1`.
    Run `NEW:PRINT "Z"`, `NEW:` and `NEW'X`. The model prints Z for the first, erases and then says Syntax error for the
    second, and accepts the third (2.7).
15. **LIST.md: a range entirely above the program (`LIST 50-60`), `LIST 20-35` (a table row), and `LIST 65530` /
    `LIST A` / a bare `LIST -`.** The Details say "there is no range error" without bounding the claim. The model lists
    nothing for 65530, everything for `-`, and crashes on `A` (2.5). "`ERR` stays 0" is stated but never read: no LIST
    case prints ERR.

## 2. Model laws no rule states, and rule clauses the model does not compute

1. **`.` (kstop_model `range()`).** `getattr(self, "dot", 0)` defaults to 0. Only LIST sets `dot`: typing a line,
   DELETE and RENUM never do, and NEW does not clear it. Only a whole argument of `.` is understood: `.-30` or `20-.`
   reads FALSE through an AttributeError. The page says `.` is "the line the editor last touched". The model's law is
   narrower, and no case can tell the two apart (1.1).
2. **`spell()` disagrees with LIST.md's Details in five places.** Model outputs, from `kstop_model.run`:
   - `40000` lists as `40000`; the page says `40000!`. Integers are never matched, and there is no `!` law at all.
   - `1E3` lists as `1000`, and `1.0` as `1`; under the page's "type mark where the text would read back as a
     different type", these should be `1000!` and `1!`.
   - `2E-5` lists as typed, because the regex `\d+[DE]\d+` has no exponent sign; the page says `2E-05`. `1E+3` also
     lists as typed.
   - `1.5D20` lists as `150000000000000000000#`, because an integral value takes `str(int(v))`; the page says
     `1.5E+20`.
   - `.005` lists as `.005`; the page says "below .01 lists in E form". Python's `.14g` switches to E form only below
     1e-4, and then writes a lowercase `e`.

   Unstated parts of the law:
   - The digit count includes trailing zeros (`1.000000` lists as `1#`).
   - Any `D` adds `#` whatever the digit count.
   - A number right after a letter or digit is skipped (this is what keeps `&H10` intact: right by accident, not by an
     `&` law).
   - `1.` (no digits after the point) is copied as typed.
3. **`spell()` and `rerefs()` find REM / DATA by substring.** `text.startswith("REM", i)` outside quotes ends the
   rewrite and the relisting for the rest of the line. So `1 PREMIUM=1:GOTO 1` / `RENUM` lists `10 PREMIUM=1:GOTO 1`
   (model), with the reference not rewritten, and `DATAX` does the same. This may agree with MSX's keyword crunching,
   which also tokenises REM inside a name, but no rule states it and no case measures it.
4. **`renum()` has none of the page's argument errors.**
   - The fourth argument is sliced away silently: `RENUM 10,1,10,7` is accepted, where the page says error 2.
   - `RENUM 65530` renumbers to 65530, and LIST then hides the line because `top = 65529`; the page says error 2.
   - There is no 65529 overflow check. `RENUM 1,,65529` on two lines makes a line 65530 that LIST never shows; the page
     says error 5.
   - `.` raises a ValueError.

   These are three Details table rows that the model contradicts. The pages' "every rule is executable" holds only
   because none of them is a rule.
5. **`rerefs()`'s keyword set is GOTO | GOSUB | THEN | ELSE | RESTORE | RUN.**
   - RESUME n, RETURN n and `ERL=n` are not rewritten. Model: `3 RESUME 2:RETURN 2` stays as typed after RENUM.
   - Neither are LIST / DELETE / LLIST arguments inside a program. Model: `LIST 1-1:DELETE 1` stays.

   RENUM.md says "every line reference". Either the sentence or the model is wrong, and only a measurement decides
   (1.3).
6. **Spacing in a rewritten reference is normalised.** `" " in m.group(0)` keeps ONE space after the keyword, and a
   list is re-joined with `,` and no spaces. Model: `10 GOTO  20` becomes `100 GOTO 110`, and `ON 1 GOTO 10, 20`
   becomes `110 ON 1 GOTO 100,110`. The real machine stores a line number as a token and the typed spaces as text, so
   the spaces probably survive. No rule states the model's law, and every measured case was typed with exactly one
   space and none after commas: the model is right on FX 30–35 by the typing, not by a law.
7. **DELETE's open top and bare form are a separate branch** (`if not arg or (dash and not b): raise Err(5)`), not
   the page's "missing number counts as 0". The two agree on all P4 cases and disagree only on a program with a line 0
   (1.11). Two rules coincide on every row there is.
8. **A typed NEW does not end its line.** In the direct branch NEW returns None, so `NEW:PRINT "Z"` prints Z. Inside a
   program it raises Stop. NEW.md says the rest of the line never runs for a PROGRAM only. The direct-mode law is
   unstated and unmeasured.
9. **NEW switches TRON off** (`new-keeps-trace`). TRON.md states this and NEW.md's R-NEW-ERASE does not. NEW's page
   lists what NEW resets, and the list is incomplete against its own model.
10. **NEW's "error 2 on an argument" is the catch-all.** `NEW 1` falls through every branch to the final
    `raise Err(2)` ("a form this BASIC does not read"). FX 4 is right because error 2 is the default, not by a NEW law.
    The control `new-arg-erases` flips WHEN the program is erased, never the error number. A rival "NEW n is error 5"
    has no code to flip.
11. **LIST, DELETE and RENUM inside a running program leave no CONT point.** They raise Stop, and `run_from` returns
    without setting `cont`. Model: `10 LIST 10` / `RUN` / `CONT` gives `Can't CONTINUE`, and so does `10 RENUM 100` /
    `RUN` / `CONT`. R-LIST-STOP says LIST keeps the CONT point, which is only true of a typed LIST. The program case is
    unstated and unmeasured.
12. **An empty statement is Syntax error** (`NEW:` erases the program, then errors). Combined with R-NEW-ERRORS'
    "anything after NEW ... nothing is erased", the model reads `NEW:` as erase-then-error. No rule says which.

## 3. Weak controls / unseparated rivals

The working rule (one control per rule) is met, but several RULES state 3–6 clauses and the one or two controls each
pin only one clause. Clauses with no control of their own:

1. **R-NEW-ERASE.** No control for "the variables go" (FX 1), "ON ERROR is switched off" (FX 5) or "the program goes"
   (FX 0). A "NEW keeps ON ERROR" control would be FALSE on FX 5: with the handler kept, `PRINT 1/0` does not print
   `Division by zero`.
2. **R-NEW-ERRORS.** See 2.10: no rival on the error number.
3. **R-LIST-RANGE.**
   - No control for `.` (`list-n-from` only touches numeric arguments).
   - None for the open ends (`20-`, `-30`) or for an empty program.
   - Add "`.` is the last line typed" (FALSE on FX 15) and "`.` is the first line printed" (FALSE on nothing yet: see
     1.1).
4. **R-LIST-STOP, "ends a running program".** `list-continues-line` applies only `if direct`, so FX 17 (LIST in a
   program) has no control. Add "LIST inside a program goes on" (FX 17 would print `B` twice).
5. **R-LIST-SPELL.** `list-as-typed` flips the whole law at once. These rivals agree on FX 16:
   - "`#` on any `D`" against "`#` only when the value needs a double";
   - thresholds of 6, 7 and 8 digits.

   One case cannot pin three clauses.
6. **R-DELETE-RANGE.** No control for "`-m` from the start" (FX 22).
7. **R-DELETE-CHECK.** The only control is `delete-high-free`. Clauses without one:
   - "checked before anything is deleted": a rival "delete, then check" would be FALSE on FX 21 because LIST would show
     10 and 40;
   - "reversed";
   - "there must be a range";
   - "a comma is error 2".

   This is the clause the page's title sentence leans on most.
8. **R-DELETE-EDIT, "it ends its line"** (FX 29). No control.
9. **R-RENUM-NUMBERS.** No control for "n,old renumbers only from old" (FX 32) or for "RENUM n starts at n".
10. **R-RENUM-REFS.**
    - No control for "the target, then its line's OLD number". A rival "NEW number" would print `in 10` and be FALSE on
      FX 34.
    - None for GOSUB, RESTORE or the ON-list members separately.
    - `renum-touches-text` only flips quote handling, so the REM clause has no witness at all (1.4).
11. **R-RENUM-CHECK, the increment-0 clause.** No control. FX 36 would separate "increment 0 is always error 5" from
    "error only when two new numbers collide", because it uses a one-line program, but no control encodes that rival.
12. **Rivals the cases cannot separate at all** (no case, so no control is possible):
    - the RENUM overlap rules A / B / C (1.7);
    - DELETE's "counts as 0" against the model's open-top branch (1.11 / 2.7);
    - `.` as last-printed against first-printed (1.1).

## 4. Page claims with no case, or contradicted by the record or the model

1. **LIST.md, Details against Open.** Details states `40000` lists as `40000!`. Open says "`40000` and other
   integer-looking constants past 32767 in the listing" are NOT measured. Both cannot stand. The model also predicts
   `40000` (2.2).
2. **LIST.md, the mechanism sentence "then a type mark where the text alone would read back as a different type".**
   The page's own examples falsify it. `.123456789` has 9 digits, which by the page's own "more than 6 digits is
   double" reads back as double WITHOUT a `#`, yet the measured listing has `.123456789#` (FX 16). `1.5E+20`, by the
   same page "a double that loses its `#`", reads back as a single. The measured law is closer to "a `#` on every double
   in plain form", which is the model's law, not the sentence's.
3. **RENUM.md.** Details, Summary and the error table state the THEN / ELSE / RUN rewrite, the 65529 / 65530 /
   four-argument errors, `.`, and `ON ERROR` not catching the report, all as facts. Open says "RENUM of references after
   THEN / ELSE / RUN, RENUM past 65529" are not measured. The header says "every rule is pinned", which is true only of
   the four generated rules. Mark the Details claims that rest on editverb-msx1-characterization.md (not re-run here)
   as such, or move them into rules with cases.
4. **RENUM.md, rule sections.** R-RENUM-KEEPS ("RENUM is not an edit of the variables") sits under "3. Errors". In
   LIST.md, R-LIST-STOP sits under "1. Which lines". This is cosmetic, but a reader looks for the CONT law under Errors.
5. **DELETE.md, Details "A refused DELETE ... keeps the variables and keeps the CONT point — only `ERR` changes".** No
   KNL case reads variables, CONT or ERR after a refusal (1.10). The rule sentence R-DELETE-CHECK says only "nothing is
   [deleted]", which is honest. The Details say more than the data does.
6. **LIST.md, "There is no range error ... leave `ERR` at 0".** No case prints ERR. This is a screen probe, so the ERR
   half is unread.
7. **NEW.md, Details "The program and all variables go, arrays and strings included".** No array or string was
   measured (1.13). "`NEW "A"`" is stated as an example of error 2, with no case.
8. **NEW.md, Open: "NEW with open files".** The shared model's `reset()` does not close files on NEW, while RUN's
   branch does. The model already holds a law here (files survive NEW) that the page leaves open. If a later case
   measures it, the model will need a new law, not just a new case.
9. **spec-plan.md "Every page claim held".** True of the 39 cases. Items 1–3 above are page claims that were not among
   them.

## 5. Probe-apparatus risks

1. **The setup uses the call under test.** Every case starts with `NEW` / `CLS`, which spec-method §3a forbids for a
   call's own probe. It is harmless today only because `batch=False` boots per case. Under a forced `ZB_BATCH=1`
   (batchcheck), NEW keeps the string space and the model never resets `.`. FX 2's `CLEAR 500` would then leak into
   every later case's `FRE("")`, and a `.` would carry across cases.
2. **`kstop.normalise` strips every row and drops blank rows.**
   - "LIST printed nothing" cannot be told from "LIST printed an empty line".
   - A listed line of exactly 37 characters cannot be told from one that wraps into a blank row. The 37/38 wrap edge
     is measured only at 38 (FX 35); add a 37-character line.
   - Leading spaces in a listed line, and trailing spaces typed before a REM, are lost. The `"Ok"` / `"ZB"` prompt
     substitution would also eat a program's own `PRINT "Ok"`.
3. **The screen is 24 rows.** A future case with several `Undefined line` reports plus a LIST can scroll its echo off
   the top. The model predicts the whole screen, so this would show as FALSE on both machines rather than pass
   silently. It would still cost a round.
4. **A model crash reads FALSE.** `ok()` catches ValueError / AttributeError. `RENUM .`, `LIST A` and `DELETE .-30`
   therefore read "FALSE" rather than "the model has no law". A new case in these forms will look like a rule failure
   on the reference, and the reader must know it is a missing law (2.1, 2.4).
5. **Shared-model regressions.** All 20 `k*_controls.py` still find a case against every control (I ran them). But
   `rerefs()` / `spell()` now sit in the interpreter every screen probe uses. A later fix to REM detection (2.3) or to
   the empty statement (2.12) will move kstop / kerr / ktron / kdata predictions too, so it needs the whole set re-run,
   not just klist.

**Finding count: 15 + 12 + 12 + 9 + 5 = 53.**
