<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `FIELD` — name the parts of a random-file record

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One recorded
> difference, by Joost's ruling: a fielded variable read after its channel was
> closed and reused (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`FIELD #n, w AS v$, ...` divides the record buffer of random-access channel
`n` into named pieces: the first `w` bytes become `v$`, the next ones the
next variable, and so on. The variables are windows onto the buffer, not
copies: [`LSET`](LSET.md) and [`RSET`](RSET.md) fill them before `PUT`
writes the record, and after `GET` reads a record they show its bytes. It is
a Disk BASIC statement, so the reference is the National CF-3300.

## Syntax

```
FIELD [#]<channel>, <width> AS <string variable> [, <width> AS <string variable> ...]
```

The channel must be open for random access (`OPEN "f" AS #n LEN=r`, with no
`FOR`). The `#` may be left out.

## Details

- **The pieces follow each other** from the start of the record:
  `FIELD #1,4 AS A$,4 AS B$` makes `A$` bytes 1–4 and `B$` bytes 5–8.
- **A width is a number from 0 to 255**, truncated toward zero (`10.7` is
  10); 0 is legal and gives an empty piece. A negative width or one above 255
  is `Illegal function call` (error 5); 70000 is `Overflow` (error 6).
- **The widths together may not exceed the record length** set by `LEN=`:
  `FIELD #1,9 AS A$` on a channel opened with `LEN=8` is `FIELD overflow`
  (error 50).
- **Each channel's pieces are its own.** With two random files open and a
  `FIELD` on each, a `GET` on one does not change what the other's variables
  read.
- **Closing the file does not undo the `FIELD`**: the variable still reads
  the last record after `CLOSE` — the common pattern of reading a record,
  closing, then using the value.
- **Records written with `PUT` reach the file's directory entry at
  `CLOSE`**, not at each `PUT`, as on the CF-3300; until then the size on
  the disk is the old one (`END` and `RUN` close files too). Joost ruled on
  2026-09-27 for the faithful behaviour, stamping at `CLOSE`; it shipped on
  2026-10-08 (D-PUTDIR).
- **Without a disk system** (the diskless VG-8020) `FIELD` is `Illegal
  function call` (error 5).

### Errors

| situation | error |
|---|---|
| the channel is not open | 59 `File not OPEN` |
| a channel above `MAXFILES` (`FIELD #16,...`) | 52 `Bad file number` |
| the channel is open for sequential input or output | 61 `Bad file mode` |
| the widths add up to more than the record length | 50 `FIELD overflow` |
| a negative width, or above 255 | 5 `Illegal function call` |
| a string as the width, or a numeric variable after `AS` | 13 `Type mismatch` |
| no `AS` part (`FIELD #1,4`) | 2 `Syntax error` |

The whole set of errors `FIELD` raises on the CF-3300 for its enumerated cases
is {2, 13, 50, 52, 59}; zerobas raises the same set, and the same 5, 6 and 61
above.

## Example

```
10 OPEN "F.DAT" AS #1 LEN=8
20 FIELD #1,4 AS A$,4 AS B$
30 LSET A$="AB":RSET B$="CD":PUT #1,1
40 LSET A$="WXYZ":PUT #1,2
50 GET #1,1:PRINT "[";A$;"][";B$;"]"
60 ON ERROR GOTO 90
70 FIELD #1,9 AS C$
80 CLOSE:END
90 PRINT "Error";ERR:RESUME NEXT
RUN
[AB  ][  CD]
Error 50
```

Record 2 overwrote the buffer with `WXYZ`; reading record 1 back brings
`AB  ` and `  CD` into view again.

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_field.out`](../../scratchpad/kwdoc_field.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**A fielded variable after its channel is closed and reused.** After
`CLOSE`, a reopen of the same channel and a new `FIELD #1,10 AS C$` filled
with `LSET C$="ZZZZZZZZZZ"`, the CF-3300's old `A$` silently reads
`ZZZZZZZZZZ` — another file's data — while zerobas's reads empty. The
reference keeps a pointer in the variable; zerobas binds fields through a
table of its own. Joost ruled on 2026-09-27: *"keep ours"* — a stated
divergence, closed.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **`FIELD` on a sequential channel was accepted silently** (fixed
  2026-07-31, D-NOTOPEN2); the CF-3300 raises `Bad file mode`.
- **The width was not checked at all** (fixed 2026-08-08, D-FLDWIDTH):
  `FIELD #1,-1 AS A$` gave a 255-byte piece, `256` an empty one and a string
  width a 0-byte one, where the reference raises error 5 (6 for 70000) and
  `Type mismatch`. Width 0, which zerobas's own comments had called illegal,
  turned out to be legal on the reference.
- **Fields could run past the end of the record** (fixed 2026-08-20,
  D-RECLEN). The bound is the record length from `LEN=`, not a fixed 256: a
  200-byte piece in a 64-byte record is the case that tells the two apart.
- **`CLOSE` used to wipe the `FIELD` definitions** (fixed 2026-09-01,
  D-FLDCLOSE), so a value read before closing came back empty; the reference
  keeps it, and Joost's call was to match it.
- **Two random files shared one record buffer** (fixed 2026-09-07,
  D-FIELDALIAS, D-FIELDFIX). Reading a variable fielded on channel 1 after a
  `GET` on channel 2 returned channel 2's record, and the mix-up could reach
  the disk. An earlier two-channel test had passed only because it always
  re-read a channel just before looking at it.
- **A diskless zerobas answered `FIELD` with the channel's error 59**
  (fixed 2026-09-16, D-FLDGATE); the VG-8020 says error 5.

## Where it lives

- Main ROM: `ex_field` in [basic/field.asm](../../basic/field.asm) hands the
  statement to the disk ROM through the `H_FIELD` hook; the parse of each
  `w AS v$`, the record-length check and the field table stay in main
  (`field_prologue`, `field_item`, `fld_add`, `fld_find`).
- Disk ROM: `hk_field` in [disk/kernel.asm](../../disk/kernel.asm) decides to
  run and calls back into main for each item.
- The width rules: [fldwidth-msx1-characterization.md](../fldwidth-msx1-characterization.md).

## Related concepts

- [Files and devices](../concepts/files-and-devices.md) — numbered channels to the disk, the tape, the screen and the printer

## Tests that cover it

- `make diskbasic-acceptance` — `FIELD`, `LSET` and `RSET` records written and
  compared with the CF-3300.
- `make fldwidth-acceptance` — widths, their types and domain, and the record
  length bound.
- `make fldary-acceptance` — fields bound to array elements.
- `make kwsweep` — the round trip (`FIELD`, `LSET`, `PUT`, `GET`) and the error
  rows for {2, 13, 50, 52, 59}.
- `make nodisk-acceptance` — error 5 on a diskless machine.
- `make kwram` — the RAM-usage comparison.
