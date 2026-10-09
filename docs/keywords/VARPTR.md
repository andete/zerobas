<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `VARPTR` — the memory address of a variable or a file channel

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. Three recorded
> differences, all in the file-channel form: `VARPTR(#0)`, how far channel
> blocks move when `MAXFILES` changes, and one header byte (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`VARPTR(variable)` returns the address in memory where a variable's value is
stored; `VARPTR(#n)` returns the address of file channel n's control block.
Programs use it to hand data to machine code or to `PEEK` at a value's bytes.
The addresses themselves differ between zerobas and the Philips VG-8020 —
the two machines lay out memory differently — but everything a program can
work out *from* them agrees: the size of each entry, the distance between
array elements and between channel blocks, and what sits at the address.

## Syntax

```
VARPTR(<variable or array element>)
VARPTR(#<channel number>)
```

## Details

- **A numeric variable or element:** the address of its value bytes. Array
  elements are 8 bytes apart for the default (double precision) type, so
  `VARPTR(Z(1))-VARPTR(Z(0))` is 8.
- **A string:** the address of its 3-byte descriptor — length, then a
  pointer to the characters. `PEEK(VARPTR(S$(0)))` is the string's length.
- **The address is a snapshot.** Simple variables are stored before arrays,
  so creating a new simple variable moves every array up by the new entry's
  size (11 bytes for a numeric variable). Take an address, use it, and do not
  create variables in between.
- **An array element that does not exist yet is created** (the array is
  dimensioned to 10, as on any read); an out-of-range subscript is
  `Subscript out of range` (error 9), a negative one error 5.
- **A simple variable that does not exist is `Illegal function call`**
  (error 5): `VARPTR` never creates one.
- **`VARPTR(#n)`** is the channel's control block: 265 bytes per channel (a
  9-byte header and a 256-byte buffer), the mode at +0, the device at +4 and
  the buffer position at +6. A channel past `MAXFILES` is `Bad file number`
  (error 52); `#-1` or `#256` is error 5.
- **Errors:**

| you write | you get |
|---|---|
| `VARPTR(Q)` with `Q` never assigned | error 5, `Illegal function call` |
| `VARPTR(#3)` with `MAXFILES=2` | error 52, `Bad file number` |
| `VARPTR(#-1)`, `VARPTR(#256)` | error 5 |
| `VARPTR(#"A")` | error 13, `Type mismatch` |
| `VARPTR(5)`, `VARPTR()`, `VARPTR(A,B)`, `VARPTR`, `VARPTR(#)` | error 2, `Syntax error` |

The error sets recorded for the every-error rung are {2} for the variable
form and {2, 5, 13, 52} for the channel form; the variable form's errors 5 and
9 above are measured by other gates. Both machines agree on all of them.

## Example

```
10 MAXFILES=2
20 A=0:B=0:DIM Z(4)
30 A=VARPTR(Z(0)):Q=1
40 B=VARPTR(Z(0))
50 PRINT VARPTR(Z(1))-B;B-A
60 S$(0)="hi":PRINT PEEK(VARPTR(S$(0)))
70 PRINT VARPTR(#2)-VARPTR(#1)
80 ON ERROR GOTO 120
90 PRINT VARPTR(W)
100 PRINT VARPTR(#3)
110 END
120 PRINT "Error";ERR:RESUME NEXT
RUN
 8  11
 2
 265
Error 5
Error 52
```

Line 30 creates `Q`, which moves the array `Z` up by 11 bytes.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_varptr.out`](../../scratchpad/kwdoc_varptr.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

All three are in the file-channel form and are open RAM-usage (TIER 4) work
under D-FCBSHAPE ([spec-fcbshape.md](../spec-fcbshape.md)):

- **`VARPTR(#0)` is error 59 here and an address on both references.**
  Channel 0 is the one `LOAD` and `SAVE` use, and zerobas reserves no block
  for it. Joost ruled on 2026-10-09: *"build it"* — at the price of 267 bytes
  of `FRE(0)` for every program, which the references also pay.
- **The blocks sit differently.** Changing `MAXFILES` from 1 to 2 moves
  `VARPTR(#1)` by 265 bytes on the references and by 267 here, because the
  2-byte pointer table sits on the other side of the blocks.
- **The position byte of a file being read does not move.** On the CF-3300,
  `PEEK(VARPTR(#n)+6)` counts along as a disk file is read (EOF even moves it
  one ahead); here it stays 0. Not built: it would cost a write on every byte
  read, for a value only a `PEEK` can see.

The rung not yet proven is **RAM usage**.

## What we found, and how

- **Array elements and strings were added in July** (`VARPTR(A$)` fixed
  2026-07-17; array elements 2026-07-18). A missing flag in the element form
  was caught two days later: every test had used a literal subscript, which
  hid it ([spec-basic-varptr-array-element.md](../spec-basic-varptr-array-element.md)).
- **An unset variable got an address** (fixed 2026-08-19, D-VPTRDOM). zerobas
  created the variable; both references raise error 5.
- **Malformed calls completed silently** (fixed 2026-08-26, D-EVFERR).
  `A=VARPTR` and `A=VARPTR(` gave no error; and `A=VARPTR(B` with `B` unset
  was error 5 where the references say 2, because the references look a
  simple variable up only after the closing parenthesis
  ([spec-basic-evferr.md](../spec-basic-evferr.md)).
- **The test once measured itself.** A sweep row first read −3 instead of 8 on
  both machines: splitting it to fit a line created a variable between the two
  readings and moved the array. The example's line 30 shows the same effect on
  purpose.
- **`VARPTR(#n)` did not exist** (added 2026-09-30, D-VARPTRCH). Both
  references answer the channel block's address, and agreeing on it needed
  zerobas's channel storage re-laid in the references' 265-byte shape first —
  Joost ruled on 2026-09-29 that the form be built with that re-layout, not
  on its own. The header bytes at +0, +4 and +6 have been written by `OPEN`
  since 2026-10-08 (D-FCBHDR).

## Where it lives

`ev_f_varptr` in [basic/expr.asm](../../basic/expr.asm) for variables;
`ev_ff_varptrch` in the same file for `#n`, using the channel check the file
functions share.

## Related concepts

- [Files and devices](../concepts/files-and-devices.md) — numbered channels to the disk, the tape, the screen and the printer
- [The memory map](../concepts/memory-map.md) — where BASIC keeps things in RAM
- [Strings and string space](../concepts/strings-and-string-space.md) — where string values live
- [Variables](../concepts/variables.md) — names, types, arrays, and where they live

## Tests that cover it

- `make array-acceptance` — the element form, string descriptors, and the
  auto-dimension and subscript errors.
- `make lvfix-acceptance` — the unset-variable error.
- `make fcbhdr-acceptance` — the channel header bytes after `OPEN`.
- `make kwsweep` — the element-stride row, the channel-stride row and the
  error rows for both forms.
- `make kwram` — the RAM-usage comparison.
