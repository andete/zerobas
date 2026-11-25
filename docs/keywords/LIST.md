<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no run=LIST answers="LIST 20-|LIST 10,30" -->

# `LIST` — show the program on the screen

> **Spec:** DRAFT 1 (2026-11-25) — 13 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`klist.py`](../../probes/basic/spec/klist.py), with NEW's, LIST's, DELETE's and RENUM's
> cases together; it reads the screen); every rule is executable, every recorded output is read by one,
> and every rule is pinned by a control of its own. Not yet reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-10-13):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`LIST` prints the stored program as text: each line's number, a space, and the
line itself, with every keyword spelled out again. With a line number or a
range it prints only that part. zerobas behaves like the Philips VG-8020 in
every case we have measured, errors included.

## Syntax

```
LIST
LIST <line>
LIST <from>-<to>
LIST <from>-
LIST -<to>
```

The line numbers are plain numbers (not expressions). `.` may stand for a line
number: it means the line the editor last touched.

## Details

- **`LIST n` lists line `n` only** — exactly like `LIST n-n`.
- **Neither end of a range has to exist.** `LIST 15-35` lists every stored line
  from 15 to 35. The listing starts at the first stored line at or above the
  low end.
- **An open end means "to the edge of the program".** `LIST 20-` lists from 20
  to the end; `LIST -30` from the start up to 30. (Under `DELETE` the same
  `20-` is an error — the two verbs share a grammar but not its rules; see
  [`DELETE`](DELETE.md).)
- **There is no range error.** A reversed range (`LIST 30-20`), a line that is
  not there (`LIST 25`), a range above the program and an empty program all
  list nothing and leave `ERR` at 0.
- **A comma is not a separator**: `LIST 10,30` is `Syntax error` (error 2).
- **`LIST` ends the line and the program.** `LIST 20:B=9` lists line 20 and
  never runs `B=9`; a `LIST` inside a running program lists and then the
  program stops, without an error.
- **`LIST` is not a program edit**: variables and the `CONT` point survive it
  (unlike `DELETE`, `NEW` or typing a line).
- **`.` after a `LIST` is the last line it printed**; a `LIST` that printed
  nothing leaves `.` alone.
- **A number with a fraction or an exponent is listed in the machine's own
  spelling**, not as typed: the way `PRINT` shows it, without the leading
  blank, and then a type mark where the text alone would read back as a
  different type. `0.5` lists as `.5`, `1.5D3` as `1500#`, `0.123456789` as
  `.123456789#` (more than 6 digits is double precision), `40000` as
  `40000!` and `2E-5` as `2E-05`. A number of 10^14 or more, or below .01,
  lists in `E` form, and a double then loses its `#`: `1.5D20` lists as
  `1.5E+20`.

| you type | you get |
|---|---|
| `LIST` | the whole program |
| `LIST 20` | line 20, if it exists; otherwise nothing |
| `LIST 15-35`, `LIST 20-35` | the stored lines from 15 (or 20) to 35 |
| `LIST 20-` / `LIST -30` | from 20 to the end / from the start to 30 |
| `LIST 30-20`, `LIST 25` (no such line) | nothing, no error |
| `LIST 10,30` | error 2, `Syntax error` |

The whole set of errors `LIST` can raise is {2}, the same on both machines.

## Example

```
10 REM ALPHA
20 PRINT "BETA"
30 GOTO 10
LIST
10 REM ALPHA
20 PRINT "BETA"
30 GOTO 10
LIST 20-
20 PRINT "BETA"
30 GOTO 10
LIST 10,30
Syntax error
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_list.out`](../../scratchpad/kwdoc_list.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/list_rules.py`](../../probes/basic/spec/list_rules.py), loader in
[`klist_model.py`](../../probes/basic/spec/klist_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does. The check is the
whole interpreter; what pins a rule's SENTENCE is its controls -- each rule has at least one rival law that is false
on its own cases.

**Evidence.** One probe, [`probes/basic/spec/klist.py`](../../probes/basic/spec/klist.py): it reads the SCREEN, as
[`kstop.py`](../../probes/basic/spec/kstop.py) does -- each case starts with `NEW` and `CLS`, types a short program
and the commands it names, and keeps the normalised screen (the prompt -- "Ok" there, "ZB" here, a deliberate
difference -- read as one token; a listed line longer than 37 characters wraps). The model is kstop's small BASIC
([`kstop_model.py`](../../probes/basic/spec/kstop_model.py)), the one interpreter for every screen-reading keyword
probe. Run file [`scratchpad/KNL_run1.out`](../../scratchpad/KNL_run1.out) (JSON, 2026-11-25).
- **[KNL FX *i*]** (LIST), the lines typed after NEW / CLS:
  6: `10 PRINT "A"` / `20 PRINT "B"` / `30 PRINT "C"` / `40 PRINT "D"` / `LIST 20`
  7: `10 PRINT "A"` / `20 PRINT "B"` / `30 PRINT "C"` / `40 PRINT "D"` / `LIST 15-35`
  8: `10 PRINT "A"` / `20 PRINT "B"` / `30 PRINT "C"` / `40 PRINT "D"` / `LIST 20-`
  9: `10 PRINT "A"` / `20 PRINT "B"` / `30 PRINT "C"` / `40 PRINT "D"` / `LIST -30`
  10: `10 PRINT "A"` / `20 PRINT "B"` / `30 PRINT "C"` / `40 PRINT "D"` / `LIST 30-20`
  11: `10 PRINT "A"` / `20 PRINT "B"` / `30 PRINT "C"` / `40 PRINT "D"` / `LIST 25`
  12: `10 PRINT "A"` / `20 PRINT "B"` / `30 PRINT "C"` / `40 PRINT "D"` / `LIST 10,30`
  13: `10 PRINT "A"` / `20 PRINT "B"` / `30 PRINT "C"` / `40 PRINT "D"` / `LIST 20:PRINT "Z"`
  14: `10 A=5:STOP` / `20 PRINT A` / `30 REM` / `RUN` / `LIST 20` / `CONT`
  15: `10 PRINT "A"` / `20 PRINT "B"` / `30 PRINT "C"` / `40 PRINT "D"` / `LIST 20` / `LIST .`
  16: `10 A=0.5:B=1.5D3:C=0.123456789` / `LIST`
  17: `10 LIST 20` / `20 PRINT "B"` / `RUN`
  18: `LIST`

**Controls** ([`klist_controls.py`](../../probes/basic/spec/klist_controls.py)): each changes ONE law of the
interpreter and runs over the reference's cases: “LIST n lists from n to the end” is FALSE on 3 of the 8 cases R-LIST-RANGE selects (e.g. KNL FX 6); “a reversed range is error 5” is FALSE on 1 of the 8 cases R-LIST-RANGE selects (e.g. KNL FX 10); “the rest of LIST's line runs” is FALSE on 1 of the 3 cases R-LIST-STOP selects (e.g. KNL FX 13); “LIST is a program edit” is FALSE on 1 of the 3 cases R-LIST-STOP selects (e.g. KNL FX 14); “constants are listed as typed” is FALSE on 1 of the 1 cases R-LIST-SPELL selects (e.g. KNL FX 16); “a comma separates the range's ends” is FALSE on 1 of the 1 cases R-LIST-ERRORS selects (e.g. KNL FX 12).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/list_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/list_rules.py --write` -->

**4 rules; 4 hold on the reference. Of the 105 recorded outputs (each case's normalised screen (prompts as <prompt>, the echo of the typed lines, the output, the messages)): 105 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. Which lines

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-LIST-RANGE** LIST n lists line n only; n-m every stored line from n to m (neither end has to exist); n- to the end, -m from the start; a reversed range, a missing line or an empty program list nothing, with no error. `.` is the last line LIST printed. | 8 | ✓ | ✓ |
| **R-LIST-STOP** LIST ends its line, and a running program (with no error); it is not a program edit: the variables and the CONT point survive it. | 3 | ✓ | ✓ |

#### 2. The text

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-LIST-SPELL** A constant with a fraction or an exponent is listed in the machine's own spelling, not as typed: 0.5 as .5, 1.5D3 as 1500#, 0.123456789 as .123456789# (more than six digits is double). | 1 | ✓ | ✓ |

#### 3. Errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-LIST-ERRORS** A comma is not a separator: LIST 10,30 is error 2. | 1 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] LIST of a line longer than the screen; LIST stopped by CTRL+STOP (a held key); `40000` and other
  integer-looking constants past 32767 in the listing; LLIST (a printer) -- its own page.

## What we found, and how

- **A jump that had already run listed as an address** (fixed 2026-10-13,
  D-LISTLPTR). When a program runs, the VG-8020 rewrites each `GOTO`/`GOSUB`
  target in place, from the line number to a pointer at that line — so a
  BASIC cartridge, saved after it ran, carries pointers. zerobas printed the
  pointer as if it were the number: a game's `GOSUB 2000` listed as
  `GOSUB37271`. It now prints the number of the line pointed at, as the
  VG-8020 does ([`listlptr_after.out`](../../scratchpad/listlptr_after.out)).
- **A number with a fraction or an exponent came out as garbage** (fixed
  2026-10-11, D-LISTFLT; reported by Vampier): `321 i=0.123456789` listed as
  `321 I=@14VxSTOP`, the stored value printed byte by byte, and an ASCII
  `SAVE` wrote the same garbage. The spelling above was measured on the
  VG-8020 first, 24 numbers in two rounds; three of the second round's
  predictions missed, which is why `1.5D20` and `.05` are in the list
  ([`listflt_probe2.out`](../../scratchpad/listflt_probe2.out)).
- **The line numbers used to be ignored** (fixed 2026-08-02, D-LSTRNG): every
  `LIST` printed the whole program. Twenty shapes were measured on both
  reference machines first, and the surprise was that `DELETE`'s range rules,
  measured a day earlier with the same grammar, do **not** carry over — five of
  the twenty would have come out wrong if they had been copied
  ([listrange-msx1-characterization.md](../listrange-msx1-characterization.md)).
- **Two predictions were wrong, and the measurement won.** It was expected that
  `LIST` would let the rest of the line run and would not stop a program,
  because it changes nothing. On both references it ends both. The same round
  showed that it keeps variables and `CONT`, so it must not copy `DELETE`'s
  reset.
- **`.` landed the same day** (D-DOTLINE, 2026-08-02), after measuring that it
  is the line the editor last touched — and that `LIST` itself sets it to the
  last line printed
  ([dotline-msx1-characterization.md](../dotline-msx1-characterization.md)).
- **The tests had a blind spot** (2026-09-14, D-KWLISTSEL): the only keyword
  sweep row was a bare `LIST`, which cannot see a `LIST` that ignores its
  argument. Rows for one line and for a range were added.

## Where it lives

- [basic/list.asm](../../basic/list.asm): `ex_list` is the statement;
  `list_walk` prints the selected lines; `ex_llist` (for
  [`LLIST`](LLIST.md)) shares all of it and only changes where the text goes.
- The argument parse is `le_lstrange` in
  [sub/lineedit.asm](../../sub/lineedit.asm), beside `DELETE`'s parse that it
  deliberately does not resemble.
- The design notes are in [spec-basic-listrange.md](../spec-basic-listrange.md).

## Related concepts

- [Program text](../concepts/program-text.md) — how a typed line becomes a program line
- [The screen editor](../concepts/screen-editor.md) — typing, fixing and re-entering lines

## Tests that cover it

- `make lnblank-say-acceptance` — the `lst-` and `lse-` rows: every range
  shape, `ERR` after each, the `:` tail, `LIST` inside a program, and `.`.
- `make kwsweep` — the bare, single-line and range rows, and the error row
  for {2}.
- `make listflt-acceptance` — how a fractional or large number is listed,
  24 shapes against the VG-8020.
- `make kwram` — the RAM-usage comparison.
