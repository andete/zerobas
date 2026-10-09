<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `CLEAR` — reset the variables, and size the string space

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One recorded
> difference: `CLEAR` with three arguments (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`CLEAR` throws away every variable and array, and can at the same time set the
size of the string space (where string values are kept) and the highest memory
address BASIC may use. zerobas behaves like the Philips VG-8020 in every case
we have measured, except for the error a three-argument `CLEAR` raises.

## Syntax

```
CLEAR [<string space>][,<memory top>]
```

## Details

- **All variables and arrays are cleared**, and `DEF FN` definitions with them.
- **An `ON ERROR` handler is switched off** by a `CLEAR` that succeeds, so set
  it up after the `CLEAR`.
- **The next `READ` starts from the first `DATA` again.**
- **The program keeps running** after a `CLEAR` inside it.
- **`CLEAR n` sets the string space to exactly `n` bytes**: `FRE("")` reads
  `n` afterwards. The size at start-up is 200. A bare `CLEAR`, `NEW` and `RUN`
  keep whatever size was set last.
- **`CLEAR n,top`** also moves the top of BASIC's memory to `top` (it must lie
  between &H8000 and &HF380 and leave room for the program and its string
  space); moving the top does not change the string-space size.
- **A refused `CLEAR` changes nothing**: the variables, the handler and the old
  string-space size all stay.
- **On a machine with a disk**, a `CLEAR` that succeeds also closes every open
  file (measured on the National CF-3300).

| you write | you get |
|---|---|
| `CLEAR -1` | 5 `Illegal function call` |
| `CLEAR 70000` | 6 `Overflow` |
| `CLEAR 30000` (more than there is) | 7 `Out of memory` |
| `CLEAR "A"`, `CLEAR 200,"A"` | 13 `Type mismatch` |
| `CLEAR 200,&H7000` (below &H8000), `CLEAR 200,65535` | 5 `Illegal function call` |
| `CLEAR 200,&H8050` (no room left for the program) | 7 `Out of memory` |
| `CLEAR 200,` | 24 `Missing operand` |
| `CLEAR,`, `CLEAR ,&HD000` | 2 `Syntax error` |

The measured set of errors is {2} for the bare form, {5, 6, 7, 13} for the
string-space form and {5, 13, 24} for the memory-top form, the same on both
machines.

## Example

```
10 A=5:CLEAR 300
20 PRINT A;FRE("")
30 ON ERROR GOTO 60
40 CLEAR -1
50 PRINT FRE(""):END
60 PRINT "Error";ERR:RESUME NEXT
RUN
 0  300
Error 5
 300
```

`FRE("")` is the one memory figure that is the same on both machines once
`CLEAR` has set it, which is why the example can print it.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_clear.out`](../../scratchpad/kwdoc_clear.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**`CLEAR 1,2,3` is `Illegal function call` here and `Syntax error` on the
VG-8020** (D-CLEAR3ARG, open, a TIER 6 item;
[readings](../../scratchpad/t6enum_b6.out)). zerobas checks the second argument
(2 is below &H8000) before noticing the third; the reference rejects the shape
of the statement first. This does not block **every error**: the error 2 that
the bare form can raise is also reached by `CLEAR,`, which agrees.

**zerobas has less free memory than the VG-8020**, so a string space that just
fits there can be `Out of memory` here: on 2026-09-27 `CLEAR 25000` was
accepted on the VG-8020 and refused here. That belongs to the **RAM usage**
rung, which is not yet proven.

## What we found, and how

- **The string-space size used to be ignored** (fixed 2026-07-29, D-CLP).
  zerobas kept one free area for variables and strings, and `CLEAR n` evaluated
  `n` and threw it away. Measuring the reference showed a separate string
  space of exactly `n` bytes, kept by a bare `CLEAR`
  ([clearpool-vg8020-characterization.md](../clearpool-vg8020-characterization.md)).
- **A `CLEAR` inside a program left `ON ERROR` armed** (fixed 2026-07-29). The
  reference switches the handler off exactly when it clears the variables.
- **The memory-top argument had no checks at all** (fixed 2026-08-23 and
  2026-08-24, D-CLRFIX, D-HIMDOM, D-HIMRANGE). `CLEAR 200,` set the top of
  memory to 0 before reporting its error, and the error escaped `ON ERROR`;
  `CLEAR ,200` ran where both references say `Syntax error`; and no range was
  checked. The ranges in the table were measured on both references
  ([spec-basic-himrange.md](../spec-basic-himrange.md)). One old measurement
  turned out to be empty: it had read the string space after `CLEAR ,&HD000`,
  a statement that never ran because it is a syntax error.
- **`CLEAR` did not reset the `DATA` position** (fixed 2026-09-13,
  D-READDIR); the reference resets it, as it does for `RUN` and program edits.
- **A string space too big for memory hung zerobas** (fixed 2026-09-27,
  D-CLEARFIT). `CLEAR 30000` gave no prompt at all, and `CLEAR 25000` filled
  the screen with garbage. Both are now a clean `Out of memory` that keeps the
  old string space, as on the reference.
- **Files stayed open after `CLEAR`** on the disk build (fixed 2026-10-06,
  D-CLEARCLOSE): the CF-3300 closes them, so the next `PRINT #` is
  error 59, `File not OPEN`; zerobas kept writing.

## Where it lives

- `ex_clear` in [basic/clear.asm](../../basic/clear.asm): `clr_himem` reads the
  memory top, `clr_h_fits` checks that it leaves room, `clr_done` clears, and
  `clr_files` closes the files.
- The clearing itself is `vars_reset` in [basic/arrays.asm](../../basic/arrays.asm)
  and `clear_vars` in [basic/vars.asm](../../basic/vars.asm); the string space
  is set up by `heap_reset` in [basic/str-engine.asm](../../basic/str-engine.asm).

## Tests that cover it

- `make clearpool-acceptance` — the string-space size, what a bare `CLEAR`,
  `NEW` and `RUN` keep, and `Out of string space`.
- `make clearclose-acceptance` — files closed by `CLEAR` on the disk build.
- `make kwsweep` — the bare form (a variable really reset), the string-space
  form, the memory-top form, and the error rows.
- `make kwram` — the RAM-usage comparison.
