<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no answers="NEW|LIST|PRINT A" -->

# `NEW` — erase the program and its variables

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`NEW` erases the stored program and every variable, so you can start typing a
new program. It is usually typed at the prompt, but it is also a legal
statement inside a program. zerobas behaves like the Philips VG-8020 in every
case we have measured.

## Syntax

```
NEW
```

No arguments, ever.

## Details

- **The program and all variables go**, arrays and strings included, and an
  `ON ERROR` handler is switched off.
- **The string-space size set by `CLEAR` stays**: after `CLEAR 500` and `NEW`,
  `FRE("")` still reads 500.
- **Inside a running program `NEW` erases the program and stops**, with no
  error. The rest of the line, and anything after it, never runs.
- **Anything after `NEW` is `Syntax error`** (error 2) — `NEW 1`, `NEW "A"` —
  and then **nothing is erased**.

The whole set of errors `NEW` can raise is {2}, the same on both machines.

## Example

```
10 ON ERROR GOTO 50
20 A=5:NEW 1
30 PRINT "Kept";A
40 END
50 PRINT "Error";ERR:RESUME NEXT
RUN
Error 2
Kept 5
NEW
LIST
PRINT A
 0
```

`NEW 1` is refused and erases nothing, so the program carries on; the plain
`NEW` typed afterwards erases it, and `LIST` shows nothing.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_new.out`](../../scratchpad/kwdoc_new.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **`NEW` inside a program was a `Syntax error`** (fixed 2026-09-12,
  D-NEWSTMT). zerobas only recognised `NEW` as a word typed at the prompt; a
  program that reached it failed. Before fixing it, the VG-8020 was asked what
  happens *after* a program's `NEW`: it erases the program and stops, so a fix
  that merely stopped raising the error would have kept running erased text
  ([readings](../../scratchpad/kwdrain_newdefect.out)). The fix also removed
  the separate prompt-only path, so one implementation now serves both.
- **`NEW 1` erased the program** (fixed 2026-09-28, D-NEWARG). The VG-8020
  says `Syntax error` and keeps the program; zerobas erased it — a typo after
  `NEW` lost your work. The check now comes before anything is cleared
  ([before](../../scratchpad/newarg_before.out),
  [after](../../scratchpad/newarg_after.out)).
- **Which resets belong to `NEW` was measured, not assumed** (2026-07-29). The
  `ON ERROR` handler is switched off exactly when the variables are cleared —
  by `RUN`, `NEW`, `CLEAR`, `MAXFILES` and every program edit — and zerobas
  keeps that rule in one place for all of them.

## Where it lives

`ex_new` in [basic/program.asm](../../basic/program.asm): it checks that
nothing follows, then calls `clear_vars`
([basic/vars.asm](../../basic/vars.asm)) and `new_prog`, and stops the run.

## Related concepts

- [Program text](../concepts/program-text.md) — how a typed line becomes a program line
- [Variables](../concepts/variables.md) — names, types, arrays, and where they live

## Tests that cover it

- `make unit-test` — `tests/test_statements.py` runs `NEW` inside a program,
  and a deliberately broken build fails it with the old `Syntax error`.
- `make kwsweep` — the everyday row (a program that reaches `NEW` stops
  cleanly) and the error row for {2}.
- `make kwram` — the RAM-usage comparison.
