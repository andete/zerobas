<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `SET` — a reserved word that is always refused

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

On an MSX1, `SET` is a keyword with no job. BASIC recognises the word and
then refuses it: every statement that starts with `SET` is `Illegal function
call` (error 5), whatever follows. Because it is reserved, `SET` cannot be
used as a variable name either. The Philips VG-8020 does this, and so does the
National CF-3300 with its disk system; zerobas does the same on both its
builds. [`IPL`](IPL.md) and [`CMD`](CMD.md) are the same kind of word.

## Syntax

```
SET [<anything>]
```

There is no form that does something.

## Details

- **Refused on sight**: `SET`, `SET 1`, `SET "A"` and `SET ZZZ QQQ` are all
  error 5. The rest of the statement is never read, so even text that would
  be a syntax error elsewhere gives error 5, not error 2.
- **Not a variable**: `SET=1` is error 5 too.
- **The same on every machine measured**: the VG-8020 (no disk), the CF-3300
  (with disk), and zerobas with and without its disk ROM.
- **Trappable**: `ON ERROR GOTO` catches it like any other error 5.

The whole set of errors `SET` raises is {5}, on both reference machines and
on zerobas.

## Example

```
10 ON ERROR GOTO 60
20 SET
30 SET 1
40 SET=1
50 END
60 PRINT "Error";ERR:RESUME NEXT
RUN
Error 5
Error 5
Error 5
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_set.out`](../../scratchpad/kwdoc_set.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **zerobas did not know the word** (fixed 2026-09-08, D-DONOTHING3). A
  statement like `SET PASSWORD` was read as a variable named `SET` followed by
  junk, a `Syntax error`, where the references say `Illegal function call`.
  The word had been filed as a Disk BASIC keyword; measuring the diskless
  VG-8020 showed it is reserved in plain MSX BASIC, so the diskless build owes
  it too ([`donothing_run.out`](../../scratchpad/donothing_run.out)). The
  word's code in a stored program was read off the reference, so a program
  containing `SET` is stored byte for byte as there.
- **Does a word with no job count?** On 2026-09-14 these words were dropped
  from the statement count as having nothing to get right. Joost refined the
  rule on 2026-09-17: a keyword *"works correctly in the happy path, unless
  there is no happy path in which case it works correctly in the normal
  failing path"*. For `SET` the refusal is that path, so it counts, and
  matching the reference's error is getting its whole behaviour right.

## Where it lives

- The word is in the keyword table, [basic/kwtable.inc](../../basic/kwtable.inc).
- Its statement handler is `ex_donothing` in
  [basic/interp.asm](../../basic/interp.asm) — another name for the shared
  error-5 tail `gb_illegal`, used by `IPL` and `CMD` as well.

## Tests that cover it

- `make kwsweep` — `SET PASSWORD` and the error rows, against the
  references, and the check that the stored program's bytes match the
  reference's.
- `make kwram` — the RAM-usage comparison.
