# Goldfish review (test-writer role), 2026-11-25: docs/keywords/DATA.md, READ.md, RESTORE.md

**What I read.** I read all 29 records of `scratchpad/KDA_run1.out`. It has one group, `FX`, and I read both sides of
every case. Apart from the prompt token, ref and zb are identical on all 29. I read `kdata.py`, `kdata_model.py`,
`kdata_controls.py`, the three `*_rules.py` files, `kstop.normalise` and the parts of `kstop_model.py` that run these
cases (`split`, `reset`, `run_from`'s error path, the READ / RESTORE / DATA / RUN branches, `data_items`, `element`,
`value`, `type`, `ok`).

I ran `kdata_controls.py` (rc 0, 11 controls). I also ran each control's FALSE cases through `run()`. All 11 FALSE
results are real predicted screens, not exceptions swallowed by `ok()`.

To try rival laws, I wrote a throwaway script, outside the repo, that monkeypatches the model. Every "agrees on every
case" below is that script's output, run over the reference's 29 screens. Every "the model predicts" is `K.run()` on the
typed lines given.

I did **not** read `kwdoc_*.out`, `readerl_run.out`, `readfix_datareset.out`, `datareset_probe.py` or
`readvar-msx1-characterization.md`. So the Example blocks and the "What we found" claims are judged only on whether a
KDA case carries them.

## 1. Rules not pinned by any measured case

1. **R-READ-ERRORS, "also in the middle of a READ".** FX 13 and FX 14 print the same line, `Out of DATA in 10`. No case
   shows what the READ did to the variables it had already filled. The model assigns `A=1` and then fails. The rival "a
   READ that fails assigns nothing" agrees on every case.
   Pin: `10 READ A,B` / `20 DATA 1` / `RUN` / `PRINT A`. The model predicts `1`; the rival predicts `0`.
2. **R-DATA-CUT, "spaces inside kept".** FX 2 (`HI THERE`) has one inner space, so the rival "inner runs of spaces
   collapse to one" agrees.
   Pin: `20 DATA HI   THERE` printed in brackets.
3. **R-DATA-CUT / DATA.md Syntax, "the statement ends ... at a `:` outside quotes" for an UNQUOTED item.** The only
   colons after a DATA item are in FX 5, after a closing quote, and FX 6, inside the quote. No case has `DATA X:stmt`
   or a DATA that is stepped over with a statement after it. That is the D-KWBARS class the page itself recounts.
   Pins:
   - `10 DATA 42:READ A:PRINT A` / `RUN` (the model predicts `42`);
   - `10 DATA PAD  :PRINT "R"` / `20 READ A$:PRINT "[";A$;"]"` / `RUN`. This one also pins whether trailing spaces
     survive before a colon (see 2.1).
4. **DATA.md "`DATA` statements can be anywhere — before the `READ`".** In every case the DATA comes after the READ in
   program order (FX 12 has `END:DATA` in line 20, after the READ in line 10).
   Pin: `10 DATA 9` / `20 READ A:PRINT A` / `RUN`.
5. **R-READ-NEXT, "a READ typed at the prompt" before any RUN (D-READDIR).** FX 15, 18 and 19 all RUN first.
   Pin: `10 DATA 7` / `READ A:PRINT A`. The model predicts `7`; the old zerobas bug gave `0`.
6. **R-DATA-TYPE from the prompt, and its ERL.** FX 11 is the only case, and it is a program. The page says ERL is the
   DATA line "even when `READ A` is typed at the prompt".
   Pin: `20 DATA X` / `READ A`. The model predicts `Syntax error in 20`. Add `PRINT ERL` (the model computes it, but no
   case reads it).
7. **R-READ-ERRORS error 6: the boundary and the sign.** Only `70000` into `A%` was measured.
   Pin: `-32768`, `-32769`, `32767`, `32768` and `32767.5` into `A%`. The model accepts `32767.5`, and the rounding law
   is not stated anywhere.

## 2. Model laws no rule states, and rule clauses the model does not compute

1. **Trailing spaces are trimmed before a `:` and at the end of the line.** `split()` does `cur.strip()` per
   statement, and `type()` strips the typed text. So the model keeps trailing spaces only before a comma: it predicts
   `[PAD]` for `20 DATA PAD  :REM`. R-DATA-CUT says "TRAILING spaces kept" with no qualifier. Either the rule or the
   model is wrong. Case 1.3 decides which.
2. **An item read into an array element is consumed and then THROWN AWAY.** In the READ branch, the
   `(\w+)\((\d+)\)` arm checks the subscript and does `continue` without storing anything. The model predicts `0` for
   `10 READ A(1):PRINT A(1)` / `20 DATA 7`. READ.md's Syntax, Details and Example all say an element is an ordinary
   target. Related problems:
   - `READ B$(2)` does not match that arm (`\w` excludes `$`) and falls into the numeric path: the model predicts
     `Syntax error in 20`;
   - `READ A(I)` (a non-literal subscript, as in the page's own Example) is stored as a scalar named `A(I)`.

   Only FX 16 (an error) touches elements, so no case catches any of this.
3. **The item is consumed BEFORE it is checked.** `self.dptr += 1` comes before the subscript check, the numeric parse
   and the `%` overflow test. READ.md's "What we found" (D-READERL) says the opposite about the reference: after a
   refused item, "reading the item again as a string" works, so the refused item was NOT consumed. The model therefore
   contradicts a page claim, and no case decides it.
   Pins:
   - `10 READ A` / `20 DATA X,Y` / `RUN` / `READ A$:PRINT A$`. The model predicts `Y`; the page implies `X`.
   - `10 DIM A(3):READ A(9)` / `20 DATA 1,2` / `RUN` / `READ B:PRINT B`. The model predicts `2`.
4. **Out of DATA does not move the pointer.** READ.md (D-DATARESET) says the error puts the position back to where the
   last RESTORE left it. The model never does this, and a rival that does it agrees on every case: no case reads
   anything after an Out of DATA. Pin: `10 READ A,B,C` / `20 DATA 1,2` / `RUN` / `READ D:PRINT D`. The model predicts
   `Out of DATA`; the page implies `1`.
5. **Overflow names the READ's line; Syntax error names the DATA's line.** The model raises `Err(6)` without a `.line`.
   FX 20 (`Overflow in 10`, DATA in line 20) confirms this, and a rival "Overflow names the DATA line" is FALSE on
   FX 20. This is a measured law, but no rule sentence states it. R-READ-ERRORS should say which line, as R-DATA-TYPE
   does.
6. **A refused `RESTORE n` has already moved the pointer.** The RESTORE branch sets `self.data, self.dptr = ...,
   0` before it raises 8. So after a trapped `RESTORE 99` the model reads from the first item. No rule states this and
   no case reads it. The rival "a refused RESTORE changes nothing" agrees on every case.
7. **Numeric item parsing is Python's `float()`.**
   - `DATA INF` and `DATA NAN` read into a number give `inf` / `nan`;
   - `DATA 1E99` gives a 100-digit print, where DATA.md's "What we found" says `Overflow`;
   - `&H10` and `1D3` give `Syntax error`;
   - `"5"` (a quoted item) read into a number gives 5.

   No rule states any of these, and the Open list names only `&H` / exponent / suffix.
8. **An apostrophe in an unquoted DATA item starts a comment.** `split()` does not look at DATA, so `20 DATA A'B` reads
   `[A]`. Text after a closing quote is dropped silently: `DATA "A"X,B` reads `[A]`. These are unstated laws and
   plausible errors. `DATA A REM B` reads `[A REM B]` (ktron's case).
9. **Empty DATA forms.** A bare `DATA` is one empty item, and `DATA 1,` has an empty second item. These are unstated
   and unmeasured.

## 3. Weak controls, and plausible rivals that no case separates

1. **R-RESTORE-ERRORS: two rival mechanisms agree on all 3 of its cases.** Both also agree on the whole run.
   - **Rival A:** "RESTORE reads a possibly empty digit string as the line (empty is line 0), raises 8 if that line is
     missing, and only then requires the end of the statement (error 2)."
   - **Rival B:** "RESTORE evaluates an expression; an unusable one is 8".

   Both rivals give 8 for `99`, `X` and `,` because none of the cases has a line 0 or a valid number followed by
   junk. Pins:
   - `0 DATA 5` / `10 RESTORE X:READ A:PRINT A`. The model and the rule give 8; rival A gives 2.
   - `10 RESTORE 20X` / `20 DATA 1`. The model gives 8; rival A gives 2.
   - `10 X=20:RESTORE X:READ A:PRINT A` / `20 DATA 5`. The model gives 8; rival B gives `5`.
   - `RESTORE 65530` / `RESTORE 70000`. The model gives 8. A line-number reader that refuses over 65529 gives 2.

   The existing control ("a variable is error 2") is real but is the weakest rival. It does not touch "a missing line"
   at all. A rival "a missing line goes to the next DATA after it" is FALSE on FX 25 only, and no control states it.
2. **R-DATA-CUT is a nine-clause conjunction pinned by three controls.** The three are trailing-trim, quotes-kept and
   empty-error; empty-error is FALSE only on FX 8 (a number), not on FX 9 (a string). Each clause below has a separating
   case in the run, but no control of its own:
   - "leading spaces skipped": the rival is FALSE on FX 3;
   - "quoted spaces kept at both ends": the "trimmed" rival is FALSE on FX 7;
   - "a colon ends DATA even inside quotes" (the D-DATACOLON bug): the rival is FALSE on FX 5 and FX 6;
   - "an unterminated quote ends at the next colon": the rival is FALSE on FX 6;
   - "empty items skipped": the rival is FALSE on FX 8 and FX 9;
   - "digits into a string stay text": the rival (STR$ of the number) separates on FX 10;
   - "DATA after END is skipped": the rival separates on FX 12.

   Under the "a control of its own" rule these pass, but each clause relies on the whole-screen check alone. Add these
   rivals to `kdata_controls.py`.
3. **R-READ-NEXT's RUN clause and "across DATA lines" have no control.** The model's own `run-keeps-data` switch
   exists, is FALSE on FX 17, and is not listed in `kdata_controls.py`. "A READ reads only one DATA line" separates on
   FX 21.
4. **R-RESTORE-POINT's "the rest of its line runs" has no control.** "A bare RESTORE ends its line" (the D-DATACOLON
   bug) and "a bare RESTORE does nothing" are both FALSE on FX 22 only. FX 28 prints `5  5`, exactly as FX 22 does, so
   it does not separate RESTORE n from a bare RESTORE (the existing control is FALSE on FX 23 and 24 only). Its value
   is only against "RESTORE n to the current line keeps the position", which is not a control either.
5. **R-DATA-TYPE's "error 2" half has no control.** Only "the line it names" has one. The old law "text reads as 0"
   is FALSE on FX 11, and that is the only case. One case cannot separate "any non-numeric item is 2" from "an item
   with no leading digit is 2": FX 11 is `X`, while the page's own story is `12X`.
   Pin: `20 DATA 12X`. The model predicts `Syntax error in 20`.
6. **R-READ-NEXT, the CLEAR and edit clauses hang on FX 15.** Cases 18 and 19 prove a reset only because FX 15 proves
   that a direct READ does not restart. The rival "a direct READ always restarts" also predicts `5` on 18 and 19. This
   is not a defect, but if FX 15 is ever dropped, both clauses lose their pin silently.

## 4. Page claims with no case, or contradicted by the record

1. **READ.md errors: "The measured set of errors for `READ` on the VG-8020 is {2, 4, 6}".** FX 16 measured error 9
   (`Subscript out of range in 10`) on the reference, and R-READ-ERRORS states it. The table has no row for 9 either.
2. **READ.md Summary: "except two out-of-range number cases that are filed".** This contradicts the page's own
   "Differences: No known difference" and the Overflow row "on both machines (KDA FX 20)". It is stale; spec-plan says
   the Overflow row was corrected, but the Summary was not.
3. **DATA.md Summary: "with one open difference in an error case".** This contradicts "No known difference in
   behaviour" and the record: ref = zb on FX 11.
4. **RESTORE.md: "The whole set of errors `RESTORE` can raise is {8}".** That is an "every error" claim made from 3
   cases with no line-number range case (3.1). Narrow it to "measured" or add the 65530 / 70000 cases. The Status line's
   "every error ✓" rests on the same thing.
5. **Claims that only the 2026-10-09 kwdoc example run carries, or nothing at all.** None of these is a KDA case:
   - READ.md's Example: FOR, `A(I)`, `B%`, ON ERROR, and 2.5. The model cannot run it (see 2.2), and it does not refuse
     either: `10 FOR I=0 TO 1:READ A(I):NEXT` runs to a bare prompt with no error.
   - DATA.md's and RESTORE.md's Examples.
   - DATA.md "A string read from DATA uses no string space". Open admits this one.
   - READ.md "two-character name … `B$(2,3)`".
   - DATA.md / READ.md "What we found":
     - `1.5`, `2E3`, `-.25`, `40000` read correctly;
     - `1E99` is Overflow (the model contradicts this, 2.7);
     - `99999` into `A%`;
     - D-READERL's ERL / `LIST .` / RESUME NEXT / re-read as a string (the model contradicts the re-read, 2.3);
     - D-DATARESET (the model contradicts it, 2.4).

   Each of these lacks a KDA case.
6. **RESTORE.md Open misses its own unmeasured laws.** RESTORE n past the last DATA, and the pointer after a refused
   RESTORE (2.6). Its Open has "before the first DATA" and "typed at the prompt" but not these.
7. **DATA.md Open misses the item-syntax laws the model asserts.** Apostrophe, text after a closing quote, a bare
   `DATA`, a trailing comma, a quoted number read into a number, inner space runs (2.8, 2.9, 1.2), and an unquoted item
   followed by `:` (1.3).

## 5. Probe-apparatus risks

1. **The run file carries no build identity.** It has only `{"FX": {"ref", "zb"}}`, with no ROM hash or zerobas
   commit. Every case is ref = zb, and that is also what a stale zerobas ROM that happens to agree would look like. Your
   own memory's knife-inert class applies. `live_copy` only re-measures zerobas; it does not record what it measured.
2. **`normalise` strips every 40-column row.** Any space-sensitive claim must be bracketed, and the probe does that for
   strings. But a case for trailing spaces at the END of a typed DATA line can never be read: the echo row is stripped,
   the screen editor may drop the spaces, and `type()` strips the line. Such a case must end the item with `,` or `:`
   (1.3), never with the end of the line.
3. **The model does not refuse unknown statements.** FOR / NEXT and `PRINT A%` (`value()` has no `%` form, so the
   model raises 2) give plausible screens or a Syntax error, not "cannot model". So a new case written from the pages'
   own examples will read as a ✗ on the reference that is really the model's gap. The fix is a refusal on unparsed
   statements, not a guess.
4. **`ok()` maps any exception to FALSE.** I checked that none of the current 11 controls is FALSE through an
   exception. A future control could pass the "FALSE on some case" test only because it crashes. `kdata_controls.py`
   should count an exception separately.
5. **No case uses ON ERROR, ERR, ERL or RESUME.** No case reads past an error either. So everything that happens after
   an error is unobserved: what was assigned (1.1), the pointer (2.3, 2.4, 2.6), and the line named for a prompt READ
   (1.6). This is a whole axis of the three pages' claims, and the cheapest single addition is a small FY group that
   types one direct `READ` / `PRINT` after each error case.
6. **FX 9's echo wraps at 37 (a 38-character line, `"` alone on row 2).** The model predicts it, but that ties FX 9 to
   the model's wrap law, so a change to the shared wrap law can turn R-DATA-CUT red for a reason that has nothing to do
   with DATA. Shorter typed lines would decouple it.

**Findings: 35** (section 1: 7, section 2: 9, section 3: 6, section 4: 7, section 5: 6).
