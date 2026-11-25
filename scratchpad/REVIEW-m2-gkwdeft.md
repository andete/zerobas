# Goldfish review (test-writer role), 2026-11-25: docs/keywords/DEFINT.md, DEFSNG.md, DEFDBL.md, DEFSTR.md

**Run-file records decoded.** By hand from the raw `CAP ref` / `CAP zb` hex of `scratchpad/KDT_run1.out`: records
KDT FX 0–10 on both sides (errors, the three type bytes and the WV# BCD bytes; e.g. FX 4 ref `00 00 02 00 00 c1 10 …`
= no error, A int, -1; FX 8 zb `00 00 59 44 00 …` = the letters `Y`, `D` where ref has `02 08`). These agree with
`kdeftype.decode`. All other records (11–57) I read only through `kdeftype.load` (the probe's own decoder), printed
next to the model's prediction (`kdeftype_model.run`) and the zerobas record. I also ran `kdeftype_controls.py` and
every `alt` switch against every page's rules (pure Python over the run file). No emulator, make or gate was run.

Every ref record equals the model's prediction; every zb record equals ref except the type bytes (the ENTRY rule).

## 1. Rules not pinned by any measured case

1. **R-INT-STORE, the range edges.** Only `40000` (error 6) and `-32768` (accepted) are measured. spec-plan §1 asks
   for "both ends of each range" and "the overflow test before vs after truncation (`-32768.5`, `32767.9`)". The model
   truncates first, then tests. Pin with `DEFINT A:A=32767.9:WV#=A`, `DEFINT A:A=32768`,
   `DEFINT A:A=-32768.5:WV#=A` and `DEFINT A:A=-32769`, each reading A.
2. **R-*-STORE, "after an error the variable exists, holding its type's zero".** No case reads the value after an
   error. FX 16 and FX 41/45 record only that A exists. Also, for a variable that ALREADY exists, the model keeps the
   old value (`assign` does not zero it), while the sentence says "its type's zero". Pin with
   `DEFINT A:A=40000:WV#=A+.5` (.5) and `DEFINT A:A=5:A=40000:WV#=A` (model: 5).
3. **R-INT-NAME, "through its FIRST letter".** Every name in the probe has one letter. Pin with
   `DEFINT A:AB=1.7:BA=1.7:WV#=AB+BA` (2.7). The model's `key` also makes only two characters significant
   (`name[:2]`, see 2.6). Pin that with `DEFINT A:ABC=1:ABD=2:WV#=ABC` (model: 2).
4. **A suffixed and an unsuffixed name of the same type are one variable** for INT, SNG and DBL. The model's
   `key = (base, type)` says so, but only DEFSTR measures it (FX 43). Pin with `DEFINT A:A%=5:WV#=A`,
   `DEFSNG A:A!=2.5:WV#=A` and `A#=1/3:WV#=A`.
5. **R-*-LIST, partial application on the error items whose case reads no name.** "The items before it -- and the
   glued item itself -- stand" is pinned only by FX 52, 53, 56 and 57. FX 24, 30, 31, 32 and 33 read nothing, so the
   model's predictions there are unchecked:
   - `DEFINT A-:A=1.7:WV#=A`: does the start of an unfinished range stand? The model says no (1.7). The rival "the
     start letter is applied, then the dash is read" says 1.
   - `DEFINT A B:A=1.7:WV#=A`, `DEFINT A,:A=1.7:WV#=A`, `DEFINT A$:A=1.7:WV#=A` and `DEFINT A-B-C:B=1.7:WV#=B`: the
     model says 1 for each.
6. **R-*-LIST, the spaces.** The sentence allows spaces "around the dash and before the comma". The model also skips
   spaces AFTER the comma and before `:` / end of line. Neither is measured. Pin with `DEFINT A, B:B=1.7:WV#=B` and
   `DEFINT A :A=1.7:WV#=A`.
7. **R-SNG-LIST, R-DBL-LIST, R-STR-LIST: the shared grammar is measured almost only through DEFINT.** These are
   DEFINT's sentence repeated: glued items, a bad later item, the spaces, a suffix, a trailing comma, CLEAR. The
   pages' own cases are 6, 3 and 10, and none of them is a partial list, a glued item, a spaced range or a CLEAR.
   "All four statements share one parser" is a zerobas fact (`deftype_tenant`); on the reference it is an assumption.
   Pin with `DEFSTR A,5:A="X":WV#=LEN(A)`, `DEFSNG AB:A=1/3:WV#=A`, `DEFDBL A-:…` and
   `DEFINT A-Z:DEFDBL A-C,Z-A:B=1/3:WV#=B`.
8. **R-INT-STORE, "FOR … store the same way".** FX 14 (`FOR I=1 TO 3`) ends at 4 whether I is an integer or a
   double, so its value does not show truncation (only its type byte shows the type). Pin with
   `DEFINT I:FOR I=1.7 TO 3:NEXT:WV#=I`: 4 if I is an integer, 3.7 if it is a double. The model would get this wrong;
   see 2.2.
9. **R-SNG-STORE and R-DBL-STORE, "an assignment makes its variable BEFORE the value is checked".** No DEFSNG or
   DEFDBL case raises an error, so the clause has no case on those two pages. Pin with `DEFSNG A:A="X"` (13; is A
   present, type 4?) and an overflow made by rounding, `DEFSNG A:A=9.9999999E62` (the model gives error 6, see 2.4).
10. **Arrays: a new type means a new array.** The model keys arrays by (name, type), and FX 19 cannot separate that
    from "DEFINT retypes the existing array": both store 1. Pin with
    `DIM A(2):A(1)=1.7:DEFINT A:WV#=A(1)` (model: 0) and
    `DIM A(2):A(1)=1.7:DEFINT A:A(1)=3:DEFDBL A:WV#=A(1)` (model: 1.7). `DIM A(2):DEFINT A:DIM A(2)` gives no
    error 10 under the model.
11. **R-*-NAME and other kinds of name.** "An unsuffixed name follows the table" also covers `DEF FN` names and
    parameters, `INPUT`/`LINE INPUT` targets and `SWAP`. None is measured, and Open lists only "a DEF inside a
    running DEF FN body". Pin with `DEFINT X:DEF FNB(X)=X:WV#=FNB(1.7)` (1 if X is an integer) and
    `DEFINT A:DEF FNA(X)=X/2:WV#=FNA(3)`.
12. **R-*-LIST, "CLEAR puts EVERY letter back".** FX 21 checks only A, and only CLEAR with arguments. Pin with
    `DEFINT A-Z:CLEAR:Z=1.7:WV#=Z`.

## 2. Model laws no rule states, special cases, and rule clauses the model does not compute

1. **Every rule's check is the whole interpreter.** LIST, NAME and STORE all check `behaves`, the full prediction.
   So a ✓ cannot be attributed to the sentence, and rivals of one law turn other rules false. Measured: `int-round`
   is FALSE on 16 cases of **R-INT-LIST**, `default-single` on 1 of R-INT-LIST and on R-INT-NAME, and
   `clear-keeps-def` on 1 of **R-INT-STORE** (FX 21 is in STORE because its `why` is not in `NAME_WHYS`). A zerobas
   failure of truncation would therefore show as a LIST difference. This is the same defect as gkwnum 2.1.
2. **`NEXT` is a special case, not an interpreter law.** `Machine.stmt` treats `NEXT` as "assign TO + 1 if the
   variable exists". It ignores the start value, STEP and the loop itself. That is correct only for an integer start
   with STEP 1, which is FX 14 exactly. R-INT-STORE's "FOR stores the same way" is checked by a model that never runs
   FOR. `FOR I=1.7 TO 3` (double I) is 3.7 on a real machine and 4 in the model.
3. **Arithmetic is double, rounded to 14 digits at every `*` and `/`** (`prod`). No rule states it. R-SNG-STORE's
   `1/3 → .333333` and R-DBL-STORE's fourteen digits both depend on it, and so does the assumption that rounding to 14
   digits and then to 6 equals rounding to 6 once.
4. **Overflow at |y| ≥ 10^63 on store** (`store`). No rule states it and no case reaches it. FX 38 stays below.
5. **A string stored in a numeric name is error 13** (`store`, `kind == "s"`). R-STR-STORE states the reverse; the
   INT, SNG and DBL STORE sentences state neither direction. Unmeasured: `DEFINT A:A="X"` (13, and A exists?).
6. **Two significant name characters, and arrays keyed apart from scalars and by type** (`key`, `array`). No rule
   states either (1.3, 1.10).
7. **An error keeps the old value of an existing variable**, which differs from the sentence's "holding its type's
   zero" (1.2).
8. **`_upper`: the tokenizer upper-cases outside strings.** FX 20 (lower case) rests entirely on this law, and no
   rule states it (see 5.4).
9. **`STR$` in the model is `str(Fraction)`.** That is right only for integers (`str(Fr(1,3))` is `"1/3"`); it serves
   FX 47 alone.
10. **Rules select cases by label, and some labels do not match their sentence.**
    - R-*-NAME selects `c.why in NAME_WHYS` (five literal description strings), and R-*-STORE selects the
      complement. Renaming a `why` silently moves a case between rules.
    - **R-STR-NAME**'s only case is FX 43 (A and A$ are one). That fact is stated by R-STR-STORE's sentence, not by
      R-STR-NAME's, which is DEFINT's text about `A=7:DEFINT A`. The `defstr-separate` control is credited to
      R-STR-NAME.
    - **R-DBL-STORE**, "Without any DEF every unsuffixed name is double", selects FX 1 and FX 2, which both contain a
      DEF.

## 3. Weak controls and plausible rivals that no case separates

1. **`sng-truncate` is a strawman.** It computes `int(x·10^6)/10^6`, which is six DECIMAL places, so 1.23456789
   becomes **1.234567** and 1.2345649 becomes **1.234564**: seven significant digits. Both of its FALSE cases (FX 36
   and 37) fail on the seventh digit, not on truncation. A real "truncate to six significant digits" rival gives
   1.23456 on FX 37, which agrees with the record, so it is FALSE on **1 of 4** (FX 36 only), not 2.
2. **Single rounding at an exact half** has no case. "Half up" is not separated from half-to-even. Measure
   `DEFSNG A:A=1.234565:WV#=A` (1.23457 under half up, 1.23456 under half to even). "Half up" for a negative number
   (away from zero, or towards +∞?) needs `DEFSNG A:A=-1.234565:WV#=A`.
3. **"Made BEFORE the value is checked": all measured errors are conversion errors** (40000 → 6; a number into a
   string → 13). Two readings agree on every case: "made before the right side is evaluated" (the model) and "made
   after evaluation, before conversion". Separate them with `DEFINT A:A=1/0` reading A (error 11) and
   `DEFSTR A:A=MID$("X",0)` (error 5).
4. **Rules with no control that fails on their own page's cases** (all alts tried):
   - **R-DBL-LIST** (3 cases): no rival is FALSE.
   - **R-SNG-NAME** (1 case, FX 39): no rival is FALSE; `create-time` agrees.
   - **R-SNG-LIST**: `all-or-nothing` and `clear-keeps-def` are FALSE on 0.
   - **R-STR-LIST**: `all-or-nothing`, `reversed-swaps` and `clear-keeps-def` are FALSE on 0.

   §3a says a rule must be shown able to fail. On these pages these rules are not.
5. **Thin controls.** `int-floor` is refuted only by FX 4, and `create-after` on DEFINT only by FX 16. One case each.
   Add `-2.5` and `-0.5` (truncation vs floor), and a second error-type case for create-after (3.3).
6. **Rivals the probe could separate but no control names.**
   - "the glued item itself does not stand, earlier items do": FX 56 separates it, but no control.
   - "an unfinished range applies its start letter": unseparated (1.5).
   - "DEFINT retypes an existing array": unseparated (1.10).

## 4. Page claims with no case, or contradicted by the record

1. **The Summary on all four pages**: "zerobas behaves exactly like the Philips VG-8020 for every case we have
   measured". The generated tables contradict it: R-INT-ENTRY ✗ on 23 cases, R-SNG-ENTRY ✗ on 5, R-DBL-ENTRY ✗ on 3,
   R-STR-ENTRY ✗ on 7.
2. **Differences, "(the type follows the name there)" and "Every value, error and type agrees".** The probe reads
   only `VARPTR-3`, so where zerobas keeps the type is not measured. Zerobas's type byte is never read. "Type agrees"
   rests indirectly on VARPTR finding a variable of the current table's type. For FX 7's C and FX 8's D, neither the
   type byte nor the value is read on zerobas. Pin with `PEEK(VARPTR(A)-1)` and `-2`, or with a value read
   (`D=1/3:WV#=D`).
3. **Errors examples that were measured for another keyword only.**
   - DEFSNG.md names `DEFSNG 5` and `DEFSNG A-`; only `DEFSNG Z-A` (FX 50) is measured.
   - DEFDBL.md names `DEFDBL 5`, `DEFDBL A-` and a reversed range; only a bare `DEFDBL` (FX 51) is measured.
   - DEFSTR.md names `DEFSTR 5`, `DEFSTR A-` and a reversed range; only `DEFSTR 1` (FX 49) is measured.
   - DEFINT.md's table lists `DEFINT 1`; the measured case is `DEFSTR 1`.
4. **DEFSNG.md, "`DEFSNG` undoes an earlier DEF: `DEFINT A-C:DEFSNG A-C:C=1.5` keeps 1.5".** No case has DEFSNG
   after another DEF. Pin with `DEFINT A:DEFSNG A:A=1/3:WV#=A` (.333333).
5. **DEFSTR.md Details: error 13 for `B=1+S` and for `FOR S=1 TO 3`, and "`READ S` reads the next DATA item as a
   string".** No KDT case covers any of the three.
6. **DEFINT.md, "What ends an item is `,`, `:` or the end of the line, nothing else".** This is narrower than the
   rule: a space before `,` is accepted (FX 55). A space before `:` is unmeasured (1.6).
7. **DEFINT.md, "`DEFINT I:FOR I=1 TO 3:NEXT` leaves I at 4"** is offered as evidence that loop variables follow
   the rule. A double I also ends at 4 (1.8).
8. **DEFINT.md Errors, "the only error the VG-8020 raises for any of the four, in either form".** Every case runs in
   program mode, so "either form" (presumably direct mode) has no case.
9. **The examples (2026-10-09 run, `kwdoc_*.out`) are not KDT cases**, for example `N=7/2` → 3, `DEFSTR S-T`, and
   `DEFDBL A-` in DEFDBL's example.
10. **The pages share text that does not fit them.**
    - The R-SNG-LIST, R-DBL-LIST and R-STR-LIST sentences cite `DEFINT AB` and `DEFINT A-CD`, cases those pages do
      not select.
    - The "What we found" spec-run bullet on DEFSNG.md, DEFDBL.md and DEFSTR.md is DEFINT's text word for word
      (`-1.7 -> -1`, `DEFINT A,5`) and says nothing about the page's own cases.
    - DEFDBL.md silently has no R-DBL-NAME (no case selects it), yet its Details claim "first letter only, a suffix
      always wins, looked up at every use".
11. **Status line, "every error: one difference, the variable entry's layout".** The entry layout is not an error
    difference. All error fields agree on every case (decoded).

## 5. Probe-apparatus risks

1. **WV# starts at 0, not at a sentinel** (spec-plan §1: "every case starts with its output holding a sentinel").
   FX 11, 39 and 42 expect 0, so "WV# was assigned 0" and "the assignment never ran" read the same. Only `e = 0`
   argues against the second. Start each case with, for example, `WV#=-7.25`.
2. **No witness that a case's own line ran.** The probe's comment records that an earlier run "read the previous
   case's record" when a line was refused at typing (`1E63`). `ramrec.frame` checks only the done flag and the end
   byte, so this can still happen silently: the previous case falls through to this case's record line, which
   re-records the old WE%/WF%/WV#. In this run, **13 of 57 ref records are byte-identical to the record before them**
   (FX 1, 19, 24, 25, 28, 31, 32, 33, 50, 51, 53, 55, 57; 11 on zerobas), so a missing case line would not be
   noticed. Make each case line POKE its own index (or clear its record) before it runs.
3. **The type readout goes through the subject.**
   - `VARPTR(name)` is resolved by the DEF table in force at the END of the case. T therefore reports only a variable
     of the current type: FX 11 cannot see that the double A still exists (FX 12 shows it indirectly), and FX 29's C
     is looked up as a double.
   - The design deliberately reads unassigned names. That breaks spec-plan §1's "every variable read through VARPTR is
     assigned first", and the break is safe only because VARPTR raises an error there. The page should say so.
   - `$EE` means ANY error inside the read line: handler 900 does not keep ERR, so error 5 cannot be told from any
     other error.
4. **FX 20 (lower case) tests the tokenizer, not DEFINT.** The line is crunched to upper case before DEFINT sees it.
   DEFINT's own handling of a lower-case byte could be reached only by POKEing the stored program line (own program
   RAM, still clean room).
5. **Program size is not asserted.** The program is 172 lines and about 19 KB of source text. `CLEAR 300,&HBF00`
   leaves it the $8001–$BEFF window (about 16 KB); the probe asserts only that the records end below $F380. I did not
   measure the tokenized size. Adding the cases above could push the program past HIMEM. That failure would be loud
   (no records) but would cost a run, so assert the size or move HIMEM.
6. **Independence between cases rests on the measured law itself.** Every case line starts with `CLEAR`, which
   resets the DEF table; only FX 21 (letter A) witnesses that. The cases are ordered so that a leak from FX 2, 39 and
   44 (`… A-Z`) would be invisible, because every later case DEFs its own letters explicitly.

**Findings: 12 + 10 + 6 + 11 + 6 = 45.**
