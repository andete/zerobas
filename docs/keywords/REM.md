<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `REM` — a comment

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

## Differences from the reference

None known.

Two rungs are not yet proven. **Every error**: no error set has been measured,
since `REM` has no error of its own. **RAM usage**: a `REM` line uses the same
amount of free memory on both machines, but the two machines write different
cells of the documented work area while running it.

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

## Tests that cover it

- `make kwsweep` — the everyday row (`REM z` after a statement, no error).
- `make ifsem-acceptance` — `REM` and `'` swallowing an `ELSE`, on both
  references.
- `make kwram` — the RAM-usage comparison.
