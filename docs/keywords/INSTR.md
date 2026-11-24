<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `INSTR` — find one string inside another

> **Spec:** DRAFT 1 (2026-11-24) — 1,202 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kstr.py`](../../probes/basic/spec/kstr.py)); every rule is executable and
> every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
>
> **Goldfish pass 1 (test writer) 2026-11-24:** 7 findings, 4 measured, 1 moved to open.
>
> **Status (2026-10-12):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. Strings of 128
> characters and more are found since 2026-10-12. Two divergences found on
> 2026-11-24 by the spec probe (an empty string to find past the end; a space
> before the closing parenthesis): see Differences.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`INSTR(a$,b$)` returns the position, counting from 1, where `b$` first occurs
inside `a$`, or 0 if it does not occur. `INSTR(p,a$,b$)` starts looking at
position `p`. zerobas behaves like the Philips VG-8020 in every case we have
measured except two: an empty string to find with a start past the end, and a
space before the closing parenthesis (see Differences).

## Syntax

```
INSTR([<start>,]<string to search>,<string to find>)
```

Two forms: with and without the start position. Which one you wrote is
decided by the type of the first argument — a number is the start, a string
is the text to search.

## Details

- **Positions count from 1.** `INSTR("HELLO","LL")` is 3.
- **Not found is 0**, not an error.
- **The start position skips earlier matches**: `INSTR(2,"ABA","A")` is 3,
  not 1.
- **A start past the end** finds nothing: `INSTR(10,"HELLO","L")` is 0.
- **An empty string to find** is found at once, at the start: `INSTR("HELLO","")`
  is 1 and `INSTR(3,"HELLO","")` is 3. But only while the start is inside the
  string: `INSTR(6,"HELLO","")` is 0, and so is `INSTR("","")`.
- **The start must be 1 to 255.** 0, negative numbers and 256 or more are
  `Illegal function call` (error 5); outside −32768 to 32767 it is `Overflow`
  (error 6). The start is truncated first: −32768.5 and 32767.9 are still
  error 5, −32769 and 32768 error 6.
- **A number where a string belongs** is `Type mismatch` (error 13), in
  either string position. If that number itself fails to compute, its own
  error is reported instead.
- **A missing or extra argument** is `Syntax error` (error 2).
- **Spaces are allowed** before the parenthesis, after it, around every comma
  and before the closing parenthesis: `INSTR ( "ABCDE" , "C" )` is 3.

| you write | you get |
|---|---|
| `INSTR("HELLO","LL")` | 3 |
| `INSTR("HELLO","Z")` | 0 |
| `INSTR(3,"ABCABC","B")` | 5 |
| `INSTR("HELLO","")`, `INSTR(5,"HELLO","")` | 1, 5 |
| `INSTR(6,"HELLO","")`, `INSTR("","")` | 0 |
| `INSTR(0,"AB","B")`, `INSTR(256,"AB","B")` | error 5, `Illegal function call` |
| `INSTR(70000,"AB","B")` | error 6, `Overflow` |
| `INSTR("AB",5)`, `INSTR(1,5,"B")` | error 13, `Type mismatch` |
| `INSTR("AB")`, `INSTR()`, `INSTR(1,"AB")` | error 2, `Syntax error` |
| `INSTR("AB","B","C")`, `INSTR(1,"AB","B","C")` | error 2, `Syntax error` |

Without a start, `INSTR` can raise {2, 13}; with one, {2, 5, 6, 13}. Both sets
are the same on both machines.

## Example

```
10 A$="HELLO WORLD"
20 PRINT INSTR(A$,"O");INSTR(6,A$,"O")
30 PRINT INSTR(A$,"Z");INSTR(A$,"")
40 PRINT INSTR(20,A$,"O")
50 ON ERROR GOTO 80
60 PRINT INSTR(0,A$,"O")
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 5  8
 0  1
 0
Error 5
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_instr.out`](../../scratchpad/kwdoc_instr.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/instr_rules.py`](../../probes/basic/spec/instr_rules.py), model in
[`kstr_model.py`](../../probes/basic/spec/kstr_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Evidence.** One probe, [`probes/basic/spec/kstr.py`](../../probes/basic/spec/kstr.py) (the strings region's
second, on the shared RAM-record harness [`ramrec.py`](../../probes/basic/spec/ramrec.py)), typed on both
machines; run file [`scratchpad/KST_run1.out`](../../scratchpad/KST_run1.out) (2026-11-24; zerobas's side on that
day's build). Before every case the string result variable `R$` holds `CHR$(250)` and the numeric one `R` holds
-12345, so an error, which assigns nothing, cannot read as a result, and a result written to the wrong kind of
variable is seen. A string result is read through `VARPTR` and `PEEK`, never through a string function: its length,
first and last byte, the sum of its bytes and the sum of (position x byte); a numeric result as its variable's own
8 bytes (a double), decoded exactly. The source strings `S$` and `T$` are built byte by byte in string space and
read back after every case the same way as a string result: length, first and last byte, both sums (until goldfish
pass 1 the length and the sum only, which a keyword that reordered a source's bytes would have passed).
- **[KST INS*k* H*h* T*t* P*p*]**: `R=INSTR(N,S$,T$)`, or `R=INSTR(S$,T$)` when *p* is `-`; the start *p* in -32769, -1, 0, .9, 1, 1.9, 2, 3, 4, 5, 6, 7, 129, 130, 131, 254, 255, 255.9, 256, 32768. The haystack `S$` (*h*): `ABCABC` (INS1), `""` (INS2, E), `AAAAA` (INS3, A5), and 254 x `A` + `B` (A254B) or 128 x `A` + `BC` (A128BC) (INS4). The needle `T$` (*t*): `""` (E), `A`, `B`, `C`, `AB`, `BC`, `CA`, `ABC`, `AA`, `AAB`, `Z`, `ABCABC`, `ABCABCA` (INS1-3); `""`, `A`, `B`, `AB`, `BC`, `AAB`, `Z`, `ABC` (INS4). Repeated bytes make the first match, a later match and the match at or after the start different positions.
- **[KST FX *i*]**: a fixed statement, `S$` = `"ABCDE"`, `T$` = `"CD"` (both in string space); the list, with what
  each one separates, is `FX` in the probe.

**Controls** ([`kstr_controls.py`](../../probes/basic/spec/kstr_controls.py)): zerobas's former empty-needle rule (before D-INSTREMPTY's fix), min(start, LEN(a$)+1), is FALSE on 34 of the 105 empty-needle cases of the reference; the search starting one past the start on 54 of the 1,050 non-empty ones; start 0 allowed (as 1) on 110; the start range-tested before truncation on 2 of the 5 boundary starts (KST FX 121-125).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/instr_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/instr_rules.py --write` -->

**9 rules; 9 hold on the reference. Of the 20434 recorded outputs (each case's error, the string result's length, first and last byte and two checksums, the numeric result's 8 bytes (in FR: FRE("") before the statement), the two source strings' length, first and last byte and two checksums): 20434 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. INSTR([n,] a$, b$)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-INSTR-FIND** With b$ not empty: the result is the first position, counting from 1, at or after the start (1 without one) where b$ occurs in a$, and 0 when it does not -- b$ longer than the rest of a$, a start past the end, an empty a$. A start of 1.9 is 1: truncated. Haystacks of 130 and 255 characters are searched to the end. | 750 | ✓ | ✓ |
| **R-INSTR-EMPTY** With b$ empty: the result is the start (1 without one) when the start is within a$ (start <= LEN(a$)), and 0 otherwise -- so INSTR("","") is 0, and INSTR(7,"ABCABC","") is 0, not 7. | 75 | ✓ | ✓ |
| **R-INSTR-START** The start is truncated toward zero; below -32768 or above 32767 it is error 6, otherwise outside 1 to 255 error 5, whatever the strings are (an empty b$ included). Start 0 is an error; start 255 is not, at any length. The boundary is exact and the truncation comes first: -32769 and 32768 are 6, while -32768.5, -32768, -32767, 32767 and 32767.9 are 5. | 335 | ✓ | ✓ |
| **R-INSTR-ORDER** The start is checked before anything after it: a bad start wins over a number as either string, over a third argument that fails to compute, and over a missing argument (INSTR(0,S$,5), INSTR(0,5,T$), INSTR(0,S$,1/0) and INSTR(0,S$) are 5; INSTR(70000,S$,5) is 6). | 5 | ✓ | ✓ |
| **R-INSTR-TYPE** A number as either string is error 13 (Type mismatch), with or without a start; assigning the result to a string variable is 13 too: the result is a number. | 4 | ✓ | ✓ |
| **R-INSTR-OWNERR** An argument that fails to compute raises its own error (1/0 as any argument: error 11). | 4 | ✓ | ✓ |
| **R-INSTR-SYNTAX** One string, a start and one string, a start alone, no argument, a fourth (or, without a start, a third) argument, or no closing parenthesis is error 2 (Syntax error). A string as the first of three arguments is 2 as well: a string first means the two-string form, and the third argument is one too many. | 8 | ✓ | ✓ |
| **R-INSTR-FORMS** Spaces are allowed before the parenthesis, after it, before and after every comma, and before the closing parenthesis; an integer or hex start is a number like any other; the strings may be literals in the program text or expressions (INSTR(7,S$+S$,T$) is 8). | 21 | ✓ | ✓ |
| **R-INSTR-KEEP** The source strings are left as they were, in every case, error or not (S$ and T$ read back after every case: length, first and last byte, the sum and the sum of position x byte). | 1202 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None measured: every case agrees with the VG-8020 (D-CLOSESPACE and D-INSTREMPTY were fixed 2026-11-24).

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] An argument's own error was measured with one kind (`1/0`, error 11); that any error of the argument wins is assumed.
- [A] Which work-area cells the call writes (the RAM-usage rung, [`kwram_full.out`](../../scratchpad/kwram_full.out)).
- [A] The result's numeric TYPE: it is assigned to a double variable, so whether the function returns an integer is not seen; only its value is.
- [A] The sources kept (R-INSTR-KEEP) are compared by their digest -- length, first and last byte, the sum and the sum of position x byte -- not byte for byte, and not by where they lie: a string's address is not kept by BASIC itself (garbage collection moves strings), so it is not a rule.
- [A] Bytes other than `A`, `B`, `C`, `Z`: no haystack or needle holds a byte above 127 or a control character; a comparison that ignored bit 7 would not be seen.
- [A] A needle as long as a 255-character haystack, and needles longer than 7 against the short haystacks.

## What we found, and how

- **`INSTR` ran out of string space with room to spare** (fixed 2026-10-29,
  D-CATCOPY). It copied both of its strings before searching, even a
  concatenation that was already a fresh temporary and even a plain variable,
  so `INSTR(1,T$+" "," ")` with a 96-character `T$` and 104 bytes free, and
  `INSTR(T$," ")` with a 122-character `T$` and 78 bytes free, were
  `Out of string space` here and fine on the VG-8020, which copies neither.
  Found by a calendar program written for the project's program ladder, which
  word-wraps a note and ran out a month early
  ([`catcopy_measure.out`](../../scratchpad/catcopy_measure.out),
  [`catcopy_gate.out`](../../scratchpad/catcopy_gate.out)).
- **`INSTR` found nothing in a string of 128 characters or more** (fixed
  2026-10-12, D-INSTR128): `INSTR(S$,"F")` with an `F` at position 3 of a
  128-character `S$` read 0, where the VG-8020 reads 3. The search compared the
  last place a match could start with a sign test, and every value from 128
  up looked negative. Found by the `OPEN "GRP:"` gate, whose check of 128
  screen dots used `INSTR` ([before](../../scratchpad/instr128_before.out),
  [after](../../scratchpad/instr128_after.out): 7 of 11 rows wrong, then none).
- **`INSTR` arrived on 2026-07-10**, with its edge cases (not found, empty
  string to find, a start in the middle and past the end) captured on the
  VG-8020: [spec-basic-string-functions.md](../spec-basic-string-functions.md).
- **A start of 0 or less printed a silent `0`** where the reference raises
  error 5 (fixed 2026-07-17, in the follow-up to the string-heap work).
- **A start of 256 or more was still silently "not found"**, and one past
  32767 gave the wrong error (fixed 2026-07-28, D-MISS-2). `INSTR` had only
  half of the rule, hand-written, and was on nobody's list: it was found when
  a review question was answered by running the probe instead of by argument.
  The fix made the code smaller, because the hand-written half was replaced
  by the check `MID$` uses: [spec-basic-str-domain.md](../spec-basic-str-domain.md).
- **A number where a string belongs said `Syntax error`** where both
  references say `Type mismatch` (fixed 2026-08-29, D-INSTRTM). Two rows had
  been filed; measuring the whole surface first found five. The fix is in the
  order — evaluate the operand, then complain — so an operand that fails on
  its own still reports its own error:
  [spec-basic-instrtm.md](../spec-basic-instrtm.md).

## Where it lives

`ev_f_instr` in [basic/str-engine.asm](../../basic/str-engine.asm) reads the
arguments, keeping a variable or a temporary where it is (`str_snapshot_ro`, in
[basic/files.asm](../../basic/files.asm)); the start position is checked by the shared `eval_pos_arg` in
[basic/interp.asm](../../basic/interp.asm), the same check `MID$` uses. The
search itself is `sh_instr_search` in [sub/strheap.asm](../../sub/strheap.asm),
in the sub-ROM.

## Tests that cover it

- `make catcopy-acceptance` — `INSTR` copies neither a temporary nor a variable
  (D-CATCOPY).
- `make string-acceptance` — found, not found, empty, start in the middle and
  past the end, against the reference.
- `make str-domain-acceptance` — the start position's range, both error kinds.
- `make kwsweep` — both forms (`INSTR(2,"ABA","A")` must read 3), and the error
  rows for both sets.
- `make kwram` — the RAM-usage comparison.
- `make instr128-acceptance` — strings of 127, 128, 200 and 255 characters, a
  late match, a start past 127, long needles, and a 255-long search that finds
  nothing, against the VG-8020 on both machines.
