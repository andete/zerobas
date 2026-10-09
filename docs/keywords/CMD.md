<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `CMD` — a reserved word that is always refused

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

On an MSX1, `CMD` is a keyword with no job. BASIC recognises the word and
then refuses it: every statement that starts with `CMD` is `Illegal function
call` (error 5), whatever follows. The Philips VG-8020 does this, and so does
the National CF-3300 with its disk system; zerobas does the same on both its
builds. [`SET`](SET.md) and [`IPL`](IPL.md) are the same kind of word.

## Syntax

```
CMD [<anything>]
```

There is no form that does something.

## Details

- **Refused on sight**: `CMD`, `CMD 1` and `CMD "A"` are all error 5. The
  rest of the statement is never read.
- **The same on every machine measured**: the VG-8020 (no disk), the CF-3300
  (with disk), and zerobas with and without its disk ROM.
- **Trappable**: `ON ERROR GOTO` catches it like any other error 5.

The whole set of errors `CMD` raises is {5}, on both reference machines and
on zerobas.

## Example

```
10 ON ERROR GOTO 60
20 CMD
30 CMD 1
40 CMD "A"
50 END
60 PRINT "Error";ERR:RESUME NEXT
RUN
Error 5
Error 5
Error 5
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_cmd.out`](../../scratchpad/kwdoc_cmd.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **zerobas did not know the word** (fixed 2026-09-08, D-DONOTHING3): the
  references store `CMD` as a keyword and refuse it, and zerobas did neither.
  The word had been filed as a Disk BASIC keyword; measuring the diskless
  VG-8020 showed it is reserved in plain MSX BASIC, so the diskless build
  answers it too
  ([`donothing_run.out`](../../scratchpad/donothing_run.out)).
- **Does a word with no job count?** Joost ruled on 2026-09-17 that a keyword
  *"works correctly in the happy path, unless there is no happy path in which
  case it works correctly in the normal failing path"*. For `CMD` the refusal
  is that path.

## Where it lives

- The word is in the keyword table, [basic/kwtable.inc](../../basic/kwtable.inc).
- Its statement handler is `ex_donothing` in
  [basic/interp.asm](../../basic/interp.asm) — another name for the shared
  error-5 tail `gb_illegal`, used by `SET` and `IPL` as well.

## Tests that cover it

- `make kwsweep` — `CMD"X"` against the references, its error row, and the
  check that the stored program's bytes match the reference's.
- `make kwram` — the RAM-usage comparison.
