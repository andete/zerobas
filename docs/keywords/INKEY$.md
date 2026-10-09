<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `INKEY$` — the key waiting in the keyboard buffer, if any

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`INKEY$` returns the next key waiting in the keyboard buffer, as a
one-character string, or the empty string `""` if no key is waiting. It never
waits: that is the difference from [`INPUT`](INPUT.md) and `INPUT$`. The usual
way to wait for a key is a loop:

```
10 A$=INKEY$:IF A$="" THEN 10
```

zerobas behaves like the Philips VG-8020 for every case we have measured.

## Syntax

```
INKEY$
```

No arguments and no parentheses.

## Details

- **It does not wait.** With nothing typed, `INKEY$` is `""` (length 0) at
  once, and the program carries on.
- **A waiting key comes back as a one-character string**: a program polling
  with the loop above and a `Z` typed while it runs gets `"Z"`, on both
  machines.
- **The result is a string**, so `A=INKEY$` is `Type mismatch` (error 13).
  That is the one error the tier sweep checks for `INKEY$`, and both machines
  raise it.
- **It works inside a string expression**, `PRINT INKEY$` included — that is
  how the empty case is tested.

## Example

```
10 A$=INKEY$
20 PRINT "[";A$;"]";LEN(A$)
30 ON ERROR GOTO 60
40 A=INKEY$
50 END
60 PRINT "Error";ERR:RESUME NEXT
RUN
[] 0
Error 13
```

Nothing is typed while it runs, so `INKEY$` returns the empty string.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_inkey_s.out`](../../scratchpad/kwdoc_inkey_s.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `INKEY$` leaves the same amount
of free memory on both machines, but each machine writes some work-area cells
the other does not. Nothing a program can observe through `FRE` differs.

## What we found, and how

- **`PRINT INKEY$` was a `Type mismatch`** at first (fixed 2026-07-10, the day
  `INKEY$` was built). `A$=INKEY$` worked, but `PRINT` evaluates strings by a
  second route that did not know the new token. The first run against the
  reference caught it.
- **The test had to put a real key in the buffer without typing it**
  (2026-09-13, D-KWINKEY). Because `INKEY$` does not wait, a key typed by the
  test harness arrives either too early or too late. The sweep row instead
  stores a character in the keyboard buffer itself (the documented MSX work
  area) and sets the buffer's pointers, so `INKEY$` reads a real waiting key:
  `[A 1 ]` on both machines, where an empty buffer — or an `INKEY$` that does
  nothing — gives `[ 0 ]`.

## Where it lives

`str_fn_inkey` in [basic/str-engine.asm](../../basic/str-engine.asm). It asks
the BIOS whether a key is waiting (`CHSNS`) and, only if one is, takes it
(`CHGET`). Design notes: [spec-basic-inkey.md](../spec-basic-inkey.md).

## Tests that cover it

- `make string-acceptance` — its `INKEY$` part: the empty case, and a key
  typed while a polling loop runs, against the VG-8020.
- `make kwsweep` — the stuffed-buffer row and the error row for {13}.
- `make kwram` — the RAM-usage comparison.
