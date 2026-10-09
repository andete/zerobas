<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `IPL` — a reserved word that is always refused

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

On an MSX1, `IPL` is a keyword with no job. BASIC recognises the word and
then refuses it: every statement that starts with `IPL` is `Illegal function
call` (error 5), whatever follows. The Philips VG-8020 does this, and so does
the National CF-3300 with its disk system. zerobas does the same on both its
builds. [`SET`](SET.md) and [`CMD`](CMD.md) are the same kind of word.

## Syntax

```
IPL [<anything>]
```

There is no form that does something.

## Details

- **Refused on sight**: `IPL`, `IPL 1` and `IPL ZZZ QQQ` are all error 5.
  The rest of the statement is never read, so even text that would be a
  syntax error elsewhere gives error 5, not error 2.
- **The same on every machine measured**: the VG-8020 (no disk), the CF-3300
  (with disk), and zerobas with and without its disk ROM.
- **Trappable**: `ON ERROR GOTO` catches it like any other error 5.

The whole set of errors `IPL` raises is {5}, on both reference machines and
on zerobas.

## Example

```
10 ON ERROR GOTO 60
20 IPL
30 IPL 1
40 IPL ZZZ QQQ
50 END
60 PRINT "Error";ERR:RESUME NEXT
RUN
Error 5
Error 5
Error 5
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_ipl.out`](../../scratchpad/kwdoc_ipl.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **zerobas did not know the word** (fixed 2026-09-08, D-DONOTHING3); a
  statement starting with `IPL` was read as a variable name followed by junk,
  a `Syntax error`. The word had been filed as a Disk BASIC keyword, and an
  old note feared that trying it on the disk machine would write to the disk.
  Measured instead: the CF-3300 refuses it on sight, like the diskless
  VG-8020, so it is a plain MSX BASIC reserved word
  ([`donothing_run.out`](../../scratchpad/donothing_run.out)).
- **Does a word with no job count?** Joost ruled on 2026-09-17 that a keyword
  *"works correctly in the happy path, unless there is no happy path in which
  case it works correctly in the normal failing path"*. For `IPL` the refusal
  is that path.

## Where it lives

- The word is in the keyword table, [basic/kwtable.inc](../../basic/kwtable.inc).
- Its statement handler is `ex_donothing` in
  [basic/interp.asm](../../basic/interp.asm) — another name for the shared
  error-5 tail `gb_illegal`, used by `SET` and `CMD` as well.

## Tests that cover it

- `make kwsweep` — `IPL` against the references, its error row, and the check
  that the stored program's bytes match the reference's.
- `make kwram` — the RAM-usage comparison.
