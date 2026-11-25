<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `REM` — a comment

> **Spec:** DRAFT 1 (2026-11-25) — 14 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`ktron.py`](../../probes/basic/spec/ktron.py), with TRON's, TROFF's and REM's cases
> together; it reads the screen); every rule is executable and every recorded output is read by one. Goldfish pass 1
> acted on (2026-11-25: every rule pinned by a control of its own, 6 more cases); not yet re-reviewed
> ([the keyword plan](spec-plan.md)).
>
> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors: not applicable · RAM usage not yet proven · every error not yet
> proven. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`REM` ("remark") turns the rest of the line into a comment: BASIC keeps the
text so `LIST` shows it, and skips it when the program runs. An apostrophe,
`'`, does the same. zerobas behaves like the Philips VG-8020 in every case we
have measured.

## Syntax

```
REM <any text>
' <any text>
```

## Details

- **Everything after `REM` up to the end of the line is ignored, colons
  included.** `PRINT "A":REM PRINT "B"` prints only `A`. A `REM` placed before
  other statements on the same line therefore switches them off — usually the
  thing to watch out for.
- **The apostrophe is a short `REM`**, and can follow a statement without a
  colon: `30 PRINT "C" 'a comment`.
- **A `REM` swallows an `ELSE` too.** In `IF 0 THEN REM ELSE B=1` the `ELSE`
  belongs to the comment, so `B` is not changed — on both reference machines.
- **The comment text is kept**, and `LIST` and `LLIST` show it. `RENUM` does
  not touch numbers inside a comment.
- **There is no error to make with `REM`.** That is why "common errors" is
  marked not applicable (Joost, 2026-09-29), and why no error set has been
  measured for it.

## Example

```
10 REM This line does nothing
20 PRINT "A":REM PRINT "B"
30 PRINT "C" 'a comment
40 B=9:IF 0 THEN REM ELSE B=1
50 PRINT B
RUN
A
C
 9
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_rem.out`](../../scratchpad/kwdoc_rem.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/rem_rules.py`](../../probes/basic/spec/rem_rules.py), loader in
[`ktron_model.py`](../../probes/basic/spec/ktron_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Evidence.** One probe, [`probes/basic/spec/ktron.py`](../../probes/basic/spec/ktron.py): the trace goes to the
screen, so the probe reads the SCREEN, as [`kstop.py`](../../probes/basic/spec/kstop.py) does -- each case starts with
`NEW` and `CLS`, types a short program and the commands it names, and keeps the normalised screen (the prompt -- "Ok"
there, "ZB" here, a deliberate difference -- read as one token). The model is kstop's small BASIC
([`kstop_model.py`](../../probes/basic/spec/kstop_model.py)), the one interpreter for every screen-reading keyword
probe: it types each case and predicts the WHOLE screen. Run file
[`scratchpad/KTN_run1.out`](../../scratchpad/KTN_run1.out) (JSON, 2026-11-25).
- **[KTN FX *i*]** (REM), the lines typed after NEW / CLS:
  17: `10 PRINT "A":REM PRINT "B"` / `RUN`
  18: `10 PRINT "C" 'X` / `RUN`
  19: `10 B=0:IF 0 THEN REM ELSE B=1` / `20 PRINT "[";B;"]"` / `RUN`
  20: `10 REM:PRINT "A"` / `20 PRINT "B"` / `RUN`
  21: `10 GOTO 20` / `20 REM X` / `30 PRINT "Z"` / `RUN`
  22: `10 PRINT "A" REM X` / `RUN`
  23: `REM typed` / `PRINT 1`
  24: `10 PRINT "A":'B:PRINT "C"` / `RUN`
- **[KTN FY *i*]** (REM, goldfish pass 1), the lines typed after NEW / CLS:
  11: `10 READ A$:PRINT A$` / `20 DATA X REM Y` / `RUN`
  12: `10 PRINT "A'B"` / `RUN`
  13: `10 IF 1 THEN 'X` / `20 PRINT "B"` / `RUN`
  14: `10 GOTO 30 REM X` / `20 PRINT "X"` / `30 PRINT "Y"` / `RUN`
  15: `10 B=5:IF 0 THEN REM ELSE B=1` / `20 PRINT B` / `RUN`
  16: `10 PRINT "A","B"` / `RUN`

**Controls** ([`ktron_controls.py`](../../probes/basic/spec/ktron_controls.py)): each changes ONE law of the interpreter and runs over the reference's cases; every rule has at least one of its own: “a colon ends a REM” is FALSE on 1 of the 14 cases R-REM-LINE selects (e.g. KTN FX 20); “an ELSE after REM still counts” is FALSE on 2 of the 14 cases R-REM-LINE selects (e.g. KTN FX 19); “the apostrophe needs a colon before it” is FALSE on 3 of the 14 cases R-REM-LINE selects (e.g. KTN FX 18); “REM after a statement needs no colon” is FALSE on 1 of the 14 cases R-REM-LINE selects (e.g. KTN FX 22); “a REM inside DATA ends the item” is FALSE on 1 of the 14 cases R-REM-LINE selects (e.g. KTN FY 11); “an apostrophe inside a string starts a comment” is FALSE on 1 of the 14 cases R-REM-LINE selects (e.g. KTN FY 12).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/rem_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/rem_rules.py --write` -->

**1 rules; 1 hold on the reference. Of the 81 recorded outputs (each case's normalised screen (prompts as <prompt>, the echo of the typed lines, the output, the messages)): 81 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. The rest of the line

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-REM-LINE** REM makes the rest of its line a comment, colons included -- and an ELSE, so `IF 0 THEN REM ELSE B=1` leaves B alone. The apostrophe is REM, and needs no colon before it (`PRINT "C" 'X`); REM itself does: `PRINT "A" REM X` prints A, then error 2. A REM line is an ordinary GOTO target; a typed REM does nothing. REM is a statement, not text: inside DATA it is data (`DATA X REM Y` reads `X REM Y`), inside a string an apostrophe is a character; after THEN an apostrophe is a comment, and after GOTO's line number a REM is never read. `PRINT "A","B"` is no error (a comma moves to the next zone). | 14 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None known.

Two rungs are not yet proven. **Every error**: no error set has been measured,
since `REM` has no error of its own. **RAM usage**: a `REM` line uses the same
amount of free memory on both machines, but the two machines write different
cells of the documented work area while running it.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] `LIST` / `LLIST` of a comment and `RENUM` around one (the program region); REM inside a `DEF FN`
  line.

## What we found, and how

- **`REM` is the test-writer's trap, more than the user's.** Several test rows
  padded a line with `REM ZZZ…` to push the next statement onto a new line —
  and one such row wrote `REM ZZZ…:ERROR 7`, which commented the `ERROR` out.
  It agreed with the reference on both machines while testing nothing
  (2026-09-14, D-KWPARTIAL). Padding before another statement is now done with
  assignments; a `REM` is used only as the last thing on its line.
- **`REM` and `ELSE`** were measured together when `IF … ELSE` was reworked
  (2026-09-02, D-IFSEM): the skip that looks for an `ELSE` must not look inside a comment,
  and on both references it does not.

## Where it lives

At run time `REM` is `ex_rem` in [basic/interp.asm](../../basic/interp.asm): it
simply ends the line. The tokeniser, [basic/tokenise.inc](../../basic/tokenise.inc),
copies the comment text verbatim; the statement skipper used by `IF`,
[basic/tokskip-body.inc](../../basic/tokskip-body.inc), knows that a `REM` runs
to the end of the line; and `LIST` turns the stored form of `'` back into `'`
([basic/list.asm](../../basic/list.asm)).

## Related concepts

- [Program text](../concepts/program-text.md) — how a typed line becomes a program line

## Tests that cover it

- `make kwsweep` — the everyday row (`REM z` after a statement, no error).
- `make ifsem-acceptance` — `REM` and `'` swallowing an `ELSE`, on both
  references.
- `make kwram` — the RAM-usage comparison.
