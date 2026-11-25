# Goldfish review (test-writer role), 2026-11-25: docs/keywords/END.md, STOP.md, CONT.md, RUN.md

**Records read.** I decoded all 19 records of `scratchpad/KSP_run1.out`, on both sides, against `kstop.FX`. The
normalised screens of the reference and zerobas are identical in every case (`ref == zb`). I also counted what
`kstop_model.response()` keeps of each record. Every claim about the typed lines comes from the `FX` list in
`kstop.py`. Every claim about what the rules and controls compare comes from `kstop_model.py` (`T`, `RIVAL`,
`response`, `rules`) and `kstop_controls.py`. I did **not** read `kwdoc_*.out`, `spec-basic-cont-record.md`,
`spec-basic-oneflg-reset-scope.md`, `clearcont_cf.out`, `contusr_*.out`, `runclose_run.out` or any CF-3300 record. Where
a page cites one of those, I report only that no KST case is behind the claim. I do not say whether the claim is true.

## 1. Rules not pinned by any measured case

1. **R-END-STOP: "a GOSUB still pending [is] dropped".** KST FX 3 (`10 GOSUB 30:PRINT "[A]"` / `30 END` / `RUN`) only
   shows that `[A]` is not printed, which "END stops" already explains. Because CONT after END works (FX 1), whether the
   GOSUB frame survives is observable, and the rule may be FALSE. Case: `10 GOSUB 30:PRINT "[A]":END` / `30 END:RETURN`
   / `RUN` / `CONT`. "Dropped" predicts `RETURN without GOSUB in 30`; "kept" predicts `[A]`. STOP.md's Summary
   ("Unlike END ... subroutines are kept") rests on the same unmeasured contrast.
2. **R-END-STOP: "CONT after END goes on with the statement after it", for the mid-line part.** In FX 1, END is the last
   statement of line 10, so "the next statement" and "the next line" coincide. FX 0 has a statement after END but no
   CONT. Case: `10 PRINT "[A]":END:PRINT "[B]"` / `20 PRINT "[C]"` / `RUN` / `CONT`. Next statement gives `[B]`, `[C]`;
   next line gives `[C]`. END.md's Details and the CONT.md table both claim "mid-line".
3. **R-STOP-BREAK: "`Break in n` (n its line)".** The rule selects FX 4 and FX 8. FX 4's STOP is in line 10, the
   program's first line, and the model's `T` hard-codes `B = "Break in 10"`. "n is the STOP's line" cannot be told from
   "n is the first line run" or "always 10". FX 6 (`Break in 30`) would separate them, but it belongs to R-STOP-CONT.
   Either let R-STOP-BREAK select FX 6, or add `10 PRINT "[A]"` / `20 STOP` / `RUN`.
4. **R-CONT-WHEN: "after a program line was added *or changed*".** Only adding a new line 20 was measured (FX 12).
   Missing cases:
   - change line 10: `10 PRINT "[A]":STOP:PRINT "[B]"` / `RUN` / `10 PRINT "[A]":STOP:PRINT "[Z]"` / `CONT`;
   - retype line 10 byte for byte;
   - delete a line that does not exist: `20` typed alone;
   - delete a line that does: add `20 PRINT "[C]"` before `RUN`, then type `20` / `CONT`.

   They separate "any line entry", "a real change" and "a change at or before the resume point". Typing a line also
   clears the variables in MS BASIC, which nothing here checks: add `PRINT A` after the edit, with `A=5` set by the
   program.
5. **R-CONT-WHEN: "before anything ran".** Every case starts with `NEW`, so FX 10 is "CONT after NEW at power-on", not
   "CONT before anything ran". Power-on, after NEW, after CLEAR and after RUN are separate claims on CONT.md (Details
   and the Errors table), and none is measured against a live resume point. Cases, each on top of
   `10 PRINT "[A]":STOP:PRINT "[B]"` / `RUN`:
   - `NEW` / `CONT`;
   - `CLEAR` / `CONT`;
   - `RUN 15` (a missing line) / `CONT`. This one decides whether RUN drops the resume point before or after it checks
     the line.
6. **R-CONT-WHEN: "a direct statement in between does not stop it".** It rests on `PRINT 1+1` (FX 13), and on `A=7`
   (FX 9, another rule). The kinds of statement the page names, and an erroring one, are unmeasured:
   - a typed `STOP`;
   - a typed `END`;
   - a typed error such as `PRINT 1/0`;
   - a direct `GOSUB`/`FOR` such as `FOR J=1 TO 2:NEXT`.

   Each goes between `RUN` and `CONT` on the FX 13 program. CONT.md and STOP.md both claim the first three leave the
   point alone.
7. **R-RUN-CLEAR: "RUN clears the variables".** Only one simple single-precision variable was measured (FX 16). Not
   measured:
   - strings: `10 PRINT "[";A$;"]":A$="X"` / `RUN` / `RUN`;
   - arrays: `10 DIM A(5)` / `RUN` / `RUN`. If arrays survive, this gives `Redimensioned array`;
   - DEF FN, DEFINT, `ERR`/`ERL`;
   - the other resets on RUN.md's Details list (next item).
8. **RUN.md Details: "everything is reset first: ... the DATA pointer, an ON ERROR GOTO, and the resume point of
   CONT".** No case for any of the three.
   - DATA: `10 READ A:PRINT "[";A;"]":STOP` / `20 DATA 1,2` / `RUN` / `RUN`. If the pointer resets, the output is `[ 1 ]`
     twice.
   - ON ERROR: `10 ON ERROR GOTO 100` / `20 STOP` / `30 X=1/0` / `100 PRINT "[H]":END` / `RUN` / `RUN 30`. If the
     handler is reset, the output is `Division by zero in 30`, not `[H]`.
   - The CONT point: see 1.5.
9. **R-RUN-START: "RUN n at line n" clears too.** FX 14 has no variables, so "RUN n = GOTO n" is not excluded. Case:
   `10 A=5:RUN 30` / `20 PRINT "[X]"` / `30 PRINT "[";A;"]"` / `RUN`. Clearing gives `[ 0 ]`; GOTO gives `[ 5 ]`.
10. **R-RUN-START: "RUN inside a program starts it again there".** In FX 17 (`10 PRINT "[A]":RUN 20` / `20 PRINT "[B]"`),
    line 20 is also the next line. "RUN 20 in a program is ignored" therefore predicts the same `[A]`, `[B]`. Use the
    case in 1.9; it also skips line 20. A bare `RUN` inside a program (RUN.md Details) has no KST case. It needs a
    VRAM counter, as in the page's example: `10 V=VPEEK(4096):VPOKE 4096,V+1:PRINT "[";V;"]":IF V=1 THEN END` /
    `20 RUN`.
11. **END closing files (END.md "Open files stay open"; RUN.md "Open files are closed").** Both are marked as
    unreachable ("files left open at END ... the files region"). They are reachable on the diskless machines through a
    non-disk device:
    - END: `10 OPEN "CRT:" FOR OUTPUT AS #1:END` / `RUN` / `PRINT #1,"[X]"`. Still open gives `[X]`; closed gives
      `File not open`;
    - RUN: the same program, then `RUN 20` with `20 PRINT #1,"[X]"`.

    END.md's claim also goes against the usual MS BASIC manual reading ("END closes all files"), so it deserves a
    reference row of its own.
12. **STOP in a trap handler (STOP.md Details: "Inside an ON ERROR handler, STOP keeps the handler active").** No case.
    Case: `10 ON ERROR GOTO 100` / `20 X=1/0:PRINT "[B]":END` / `100 PRINT "[H]":STOP:RESUME NEXT` / `RUN` / `CONT`.
    "Kept" gives `[H]`, `Break in 100`, `[B]`. "Cleared" gives `RESUME without error in 100`. Compare
    `100 PRINT "[H]":END`, then `RUN`, `RESUME` (END.md's "a typed RESUME is RESUME without error").
13. **CONT after the program ran off its end (the CONT.md table's last row; "every further CONT returns silently").** No
    case. Case: `10 PRINT "[A]"` / `RUN` / `CONT` / `CONT`. It also needs the prompt to be read (see 5.1). Without
    that, "silent" and "hung" look the same.
14. **CONT after Ctrl+STOP; RUN "file".** These are correctly in Open. Note that `RUN "name"` on the VG-8020 goes to
    tape (CAS:) and would hang a screen probe without a cassette image. `RUN A+0` (Type mismatch, RUN.md) and `RUN 20`
    typed as `RUN20` do not need a file and could be measured now.

## 2. Model special-cases that hide a rule

1. **The model is a lookup table, not a model.** `T` maps each case's `why` string to its literal expected response,
   and `RIVAL` maps a control to a literal alternative for one case. Nothing computes a response from a rule. The rule
   sentences ("n its line", "the statement after it", "a missing n is Undefined line number") are therefore not checked
   as rules. Each check compares the reference screen with a transcription of that same screen. A wrong sentence over
   the same cases would hold just as well. For example, replace R-STOP-BREAK's text with "STOP prints `Break in 10`"
   and every table cell stays ✓. Spec-method §3a asks for a rule as `select` plus `expect`. Here `expect` is the data.
   At minimum, derive `Break in n` from the STOP's line, derive the CONT resume point from the statement list, and
   derive the RUN start line from `n`.
2. **`B = "Break in 10"` is a constant shared by the STOP cases.** This is the concrete instance of 2.1 behind 1.3. It
   hides the line-number part of R-STOP-BREAK.
3. **A rule is ✓ on an empty response.** FX 2 (`END` in direct mode), FX 3 (END inside a GOSUB) and FX 18 (RUN with no
   program) expect `[]`. Because `response()` drops every prompt (5.1), `[]` is also what a machine that hangs, or
   never returns to the prompt, produces. "Does nothing" and "returns to the prompt" are stated in the rule text but
   never read.
4. **`response()` drops a line equal to *any* typed fragment, at any position.** The echo is removed by set membership,
   not by place. Program output that happens to equal a typed fragment disappears: in FX 6 the fragment `N`, in every
   case `RUN` and `CONT`. A duplicated or missing echo also disappears. No case here is affected today, but it is a
   special case that can hide a difference.

## 3. Controls that are too weak

1. **R-RUN-START has no control at all.** Plausible rivals that no case separates:
   - "RUN n in a program is GOTO n";
   - "RUN n in a program is ignored" (FX 17, see 1.10);
   - "RUN with no program hangs or prints nothing more" (FX 18, see 2.3).
2. **R-END-STOP.** Its only control is "CONT after END cannot continue". Rivals no case separates:
   - "CONT after END resumes at the next LINE" (1.2);
   - "END keeps the GOSUB frame" (1.1);
   - "END in direct mode leaves the machine without a prompt" (2.3).
3. **R-CONT-WHEN, the error row.** The control is "CONT after an error cannot continue". The rival "CONT after an error
   re-prints the stored error without executing anything" gives the same screen as "re-executes the failing statement"
   in FX 11. Case: `10 PRINT "[A]":X=1/D:PRINT "[B]"` / `RUN` / `D=1` / `CONT`. Re-execution gives `[B]`; re-report
   gives `Division by zero in 10`.
4. **R-CONT-WHEN, the edit row.** The control "an added line keeps CONT possible" is false on FX 12. The rival "only an
   edit at or before the resume line drops it" is not separated, because line 20 is after line 10 (see 1.4).
5. **R-STOP-BREAK.** The control "direct STOP prints nothing" is a straw man. The rivals that matter, "n is the first
   line" and "n is the GOSUB caller's line", are not separated inside this rule's selection (1.3).
6. **R-RUN-CLEAR.** The control "RUN keeps the variables" is the only rival. "The end of a run clears the variables
   (RUN does not)" is not separated. Case: `10 A=5` / `RUN` / `PRINT A`. RUN.md implies `5`; the rival says `0`.
7. **R-STOP-CONT.** It has two controls in effect (statement start; the GOSUB and FOR cases), and they are adequate for
   the measured shapes. The FOR case never issues the CONT that ends the loop, so "the loop goes on" is shown for 2 of
   its 3 passes and the exit is not. Add a fourth `CONT`, and `PRINT "[E]"` after `NEXT`.

## 4. Page claims with no case behind them, or that contradict the record

1. **The rule tables count lines that no check reads ("every recorded output is read by one").** The headlines say
   23/56/35/29 outputs, all "read by a rule's check". Of those lines, `response()` keeps only:

   | page | lines counted | lines kept |
   |---|---|---|
   | END | 23 | 3 |
   | STOP | 56 | 18 |
   | CONT | 35 | 11 |
   | RUN | 29 | 6 |
   | **total** | **143** | **38** |

   The rest, prompts and echoes, are read and thrown away. Under §3a's field-level rule ("a check that reads one entry
   of a list its sentence talks about in full" does not count), the "0 unread" is hollow.
2. **END.md Details.** Each claim below has no KST case:
   - "END finishes an ON ERROR handler for good";
   - "Open files stay open (CF-3300)";
   - "Music keeps playing".

   The Open section then lists "files left open at END" as not reachable, which contradicts a Details bullet that
   states the result as measured. The Summary's "returns to the prompt" is unread (2.3).
3. **STOP.md Details.** Each claim below has no KST case:
   - "exactly as pressing Ctrl-STOP would";
   - "A typed STOP (or END, or a line with an error) does not spoil a pending CONT";
   - "Inside an ON ERROR handler STOP keeps the handler active";
   - the SCREEN 2 claim (measurable: `10 SCREEN 2:STOP` / `RUN`, then read the text screen);
   - "Music stops";
   - Differences: "`STOP ON 1` and `STOP,` are Syntax error".
4. **CONT.md Details and Errors.** Each claim below has no KST case:
   - the "the last line" table row;
   - "every further CONT returns silently";
   - "Only RUN, NEW, CLEAR and editing clear it" (RUN, NEW and CLEAR against a live point);
   - "typed STOP / END / error leave it alone";
   - "`CONT:PRINT 1` prints nothing extra";
   - both rows of the Errors table: the error number 17 is never read, and `Can't CONTINUE in <line>` inside a
     program, caught by ON ERROR, has no case;
   - "a CONT in a program continues from that STOP again".

   The Summary's "a Ctrl-STOP" has no case either. The Status line's "common errors ✓ · every error ✓" rests entirely
   on records outside this probe.
5. **RUN.md Details.** Each claim below has no KST case:
   - arrays, the DATA pointer, ON ERROR and the CONT point reset;
   - open files closed;
   - `RUN20`;
   - a bare RUN in a program;
   - all of `RUN "name"`, `,R`, `RUN A$`, `RUN A+0`.

   "Differences" says "its common errors (RUN 999, a missing file, a bad option) are measured". Only `RUN 15` is in KST.
6. **R-CONT-WHEN's sentence ("CONT before anything ran") describes a case that does not exist.** Every case begins with
   NEW (1.5).
7. **The Open section is the same text on all four pages and lists 4 items.** It does not account for the unmeasured
   claims in 4.2–4.5. Under §3a each is either a rule with a case or an Open item.
8. **The examples (all four) are not KST cases.** They cite the 2026-10-09 `kwdoc_*` run, which I did not read.
   CONT.md's example is the only evidence of "mid-line after END" anywhere near this page (1.2). It is not a rule case.
9. **`kstop_controls.py`'s docstring names the wrong file** (`probes/basic/spec/kgosub_controls.py`).

## 5. Probe-apparatus risks

1. **Prompts are removed before the check, so "returned to the prompt" is never tested.** Together with a capture taken
   on a timer (`run_cases`, `step`/`cap_gap`, not a sentinel), a hang reads as success wherever the expected response
   is empty or ends the case (FX 2, 3, 18, and the last output of every case). Compare the whole normalised screen,
   prompts included (they map to one token, and the records are identical), or at least require the final line to be
   `<prompt>`.
2. **Removing the echo loses attribution.** The response keeps the order of the outputs but not which typed command
   produced each one. "END did not stop; CONT printed nothing" and "END stopped; CONT printed `[B]`" differ only in
   where `[B]` sits relative to `CONT`. FX 0 rules out the first today, but no check would see a regression that moved
   output across a command. Again, compare the whole normalised screen.
3. **The 40-column cut assumes `raw` is the full 960-byte name table with no row separator of its own.** The
   omsx_repl docstring says it is (SCR_LEN, non-printing bytes read as space). The cut is correct today. If the capture
   ever trimmed rows, every line after the first short row would be shifted and garbled on both machines alike. Add an
   assert that `len(raw) == 960`.
4. **The 37-column echo wrap in `response()` is a separate constant from the screen's WIDTH.** If one machine wrapped
   at a different width, its leftover fragments would show up as "program output" and fail a keyword rule. The
   failure would be visible, but it would be blamed on the keyword, not the width. FX 6 and FX 7 are the only cases
   that wrap.
5. **Lines are stripped.** Leading spaces of numeric output are lost: `PRINT 1+1` reads `2`, not ` 2`. That is
   harmless here, but it is a dropped field.
6. **The function-key line is dropped by an exact regex.** Any other key-line text, or the line's absence, passes
   through as output. That fails loudly, which is safe.
7. **Prompt mapping.** A program line that prints exactly `Ok` or `ZB` becomes `<prompt>` and is then discarded. No
   case prints either, but a case reading `PRINT "Ok"` would be invisible.
8. **Screen overflow.** The longest record is 15 lines plus the key line, out of 24 rows. A longer case (for example the
   4-CONT FOR in 3.7, or a bare-RUN loop) would scroll, and the early lines would be lost without warning. Assert that
   the first line after `CLS` is `<prompt>`, which the records show for every case.

**Finding count: 42.** Section 1 has 14, section 2 has 4, section 3 has 7, section 4 has 9 and section 5 has 8. Section
4.2–4.5 holds about 30 individual unbacked claims; they are counted as 4 findings.
