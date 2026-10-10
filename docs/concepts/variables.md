<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# Variables — names, types, arrays, and where they live

> **Status (2026-10-10):** names, type suffixes, the `DEF` type statements,
> arrays, what clears variables, and the published pointers `VARTAB`, `ARYTAB`
> and `STREND` agree with the VG-8020 in every measured case. Open: an array
> that leaves very little memory free is `Out of memory` here (D-DIMRESERVE,
> TIER 4), and zerobas has less free memory overall (the RAM-usage rung).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

A variable name starts with a letter and may go on with letters and digits,
but **only the first two characters count**: `ZQ9` and `ZQ7` are the same
variable. The **suffix** gives the type — `%` integer, `!` single, `#`
double, `$` string — and a name without one is double precision unless a
`DEFINT`, `DEFSNG`, `DEFDBL` or `DEFSTR` says otherwise for its first letter.
A variable that has never been assigned reads as 0, or as an empty string.

**Arrays** are made with `DIM`, or on first use with 11 elements (0 to 10) in
every dimension. Simple variables and arrays sit in RAM right after the
program, simple variables first, and everything is thrown away by `RUN`,
`NEW`, `CLEAR` and by editing the program.

zerobas behaves like the Philips VG-8020 in all of this; only the byte order
inside a variable's entry is its own.

## How it works

### Names

- **Letters and digits, first character a letter.** Lowercase is stored as
  uppercase. A name may be longer than two characters, but only the first two
  are kept.
- **Spaces inside a name are ignored**: after `AB=7`, `PRINT A B` prints 7, on
  both machines.
- **A reserved word is recognised anywhere, even inside a name.** `SCORE` is
  stored as `SC`, the keyword `OR`, and `E` — on the VG-8020 too — so a name
  must not contain a keyword.
- **A `.` is not part of a name when the program runs**: `B.5=7` is
  `Syntax error` (error 2) on both machines.
- **A suffix is part of the variable's identity.** `A%`, `A!`, `A#` and `A$`
  are four different variables; while the default type is double, `A` and `A#`
  are the same one. Arrays have names of their own: `B` and `B(3)` do not
  share a value.

### Types by first letter: `DEFINT`, `DEFSNG`, `DEFDBL`, `DEFSTR`

`DEFINT A-C,N` makes every unsuffixed name starting with `A`, `B`, `C` or `N`
an integer. The rules, shared by all four statements (see
[`DEFINT`](../keywords/DEFINT.md)):

- a suffix always wins; the last `DEF` for a letter wins;
- **the type is looked up at every use**, not when the variable was created:
  `A=7:DEFINT A:PRINT A` prints 0, because the `A` you now name is a new
  integer and the double that holds 7 is no longer reachable by that name;
- after `DEFSTR S`, `S` and `S$` are one string variable, and a number stored
  into it is `Type mismatch`.

The 26-letter table is the published work-area variable `DEFTBL` (`&HF6CA`),
one byte per letter holding the type code (2, 3, 4 or 8 for integer, string,
single, double); zerobas keeps the same bytes there as the VG-8020. zerobas
resets every letter to double on `RUN`, `NEW` and `CLEAR`; whether each of
those resets it on the reference is not recorded separately.

### Storing a value

An assignment converts the value to the variable's type: to an integer by
truncating toward zero (`A%=-1.7` stores −1), to single precision by rounding
to six digits, to double exactly. An integer store outside −32768 to 32767 is
`Overflow`; a string into a numeric variable or the reverse is
`Type mismatch`, and nothing is stored. See [numbers.md](numbers.md).

### Arrays

- **`DIM A(10,5)`** declares an array; subscripts start at 0, so that one has
  11 by 6 elements. There is no limit on the number of dimensions.
- **Use without `DIM` creates the array with bound 10** in every dimension
  used, so `A(11)` on an undeclared `A` is `Subscript out of range` (error 9).
- **The elements may not need more than 65535 bytes** (2 per integer, 4 per
  single, 8 per double, 3 per string); past that `DIM` is
  `Subscript out of range`, and below it but past free memory `Out of memory`.
- **`DIM` an existing array again is `Redimensioned array`** (error 10);
  [`ERASE`](../keywords/ERASE.md) removes one so it can be declared anew.
- **A string array element holds a 3-byte descriptor** (length and address);
  the characters themselves are in the string space
  ([strings-and-string-space.md](strings-and-string-space.md)).

### Where variables live

MSX BASIC keeps its data in one block above the program, described by
published pointers in the work area:

```
TXTTAB (&HF676) -> program text, ended by two zero bytes
VARTAB (&HF6C2) -> simple variables, in order of creation
ARYTAB (&HF6C4) -> arrays, in order of creation
STREND (&HF6C6) -> free memory ...
                   ... the stack, then the string space, up to the top set by CLEAR
```

- **A simple variable takes 3 bytes plus its value**: 11 bytes for a double,
  6 for a string (its 3-byte descriptor), and in zerobas 5 for an integer and
  7 for a single. The double and string sizes, and every pointer above, were
  measured equal to the VG-8020's.
- **An array takes a header plus its elements**: `DIM B(5)` moves `STREND` by
  56 bytes on both machines, an 8-byte header and 6 doubles. In zerobas the
  header is 6 bytes plus 2 per dimension.
- **Creating a simple variable moves every array up** by the new entry's size,
  because the arrays sit above the simple variables. An address from
  [`VARPTR`](../keywords/VARPTR.md) is therefore only good until the next new
  variable — the example shows it. Creating a variable can be `Out of memory`.

The order of the bytes *inside* an entry, and the code that marks a string
entry, are zerobas's own; `VARPTR` points at the value (or the string
descriptor) on both machines.

### What clears variables

| action | variables and arrays | `DEF` types (zerobas) | string-space size | `ERR` / `ERL` |
|---|---|---|---|---|
| `RUN` | cleared | reset to double | kept | kept |
| `NEW` | cleared, with the program | reset to double | kept | kept |
| `CLEAR` | cleared, `DEF FN` too | reset to double | set, or kept | kept |
| typing a program line | cleared | kept | kept | not measured |
| `ERASE A` | only the array `A` | kept | kept | kept |

`RUN`, `NEW` and `CLEAR` also switch off `ON ERROR`; `RUN` and `CLEAR` reset
the `DATA` pointer and, on a disk machine, close open files.

## Example

```
10 A=1:A%=2:A!=3:A#=4
20 PRINT A;A%;A!;A#
30 ZQ9=5:PRINT ZQ7
40 DEFINT N:N=7/2:N$="HI":PRINT N;N$
50 B=2:B(10)=6:PRINT B;B(10)
60 X=0:DIM C(3):X=VARPTR(C(0))
70 Y=1:PRINT VARPTR(C(0))-X
80 ON ERROR GOTO 110
90 B(11)=1
100 END
110 PRINT "Error";ERR:RESUME NEXT
RUN
 4  2  3  4
 5
 3 HI
 2  6
 11
Error 9
```

`A` and `A#` are one variable, so `A#=4` overwrites `A=1`; `ZQ7` is `ZQ9`.
`B(10)` creates an array beside the simple variable `B`, with bound 10, so
`B(11)` is error 9. Line 70 creates `Y`, which moves the array `C` up 11 bytes.
Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_variables.out`](../../scratchpad/kwdoc_variables.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

- **An array that leaves very little memory free** fits on the VG-8020 a little
  closer to the end of memory than here, by about 30 bytes, where it was about
  170 until 2026-10-10 (D-DIMRESERVE, open, TIER 4). zerobas keeps a reserve for
  its own stack, which goes deeper than the reference's. Joost ruled on
  2026-10-09: *"yes, we need to match reference there"* ([`DIM`](../keywords/DIM.md)).
- **Less free memory overall**, so a program that only just fits on the
  VG-8020 can run out here. That is the RAM-usage rung, not yet proven.
- **The addresses `VARPTR` returns differ**, because the two machines place
  things differently; distances between entries agree.
- **The string type code inside an entry is 1 here**, where the type table uses
  3; making them one code is filed as an architecture item that Joost ruled on
  2026-09-10 stays after TIERS 1–4. A program sees it only by `PEEK`ing in front
  of a `VARPTR` address, which is not measured on the reference either.

## What we found, and how

- **Variables used to live in a fixed 128-byte pool.** In July 2026 they moved
  into the one block after the program, as on MSX
  ([spec-basic-arrays-slice4b-scalar-reloc.md](../spec-basic-arrays-slice4b-scalar-reloc.md)).
- **Typed variables and the `DEF` statements arrived on 2026-07-12**; before
  they shipped, the tests and a review found a `DEFINT` loop or `READ` variable
  stored as one type and read as another, and a range fill that overwrote
  about 177 bytes of work area
  ([spec-basic-float-core.md](../spec-basic-float-core.md) §11).
- **`DEFSTR` on a loop variable corrupted memory** (fixed 2026-08-01,
  D-DEFSTR); since then the type table holds the same bytes as the
  reference's ([spec-basic-deftbl-strcode.md](../spec-basic-deftbl-strcode.md)).
- **A `.` and a space behave differently inside names**, and both were
  measured before anything was changed: the tokeniser keeps `B.5` as a name but
  running it is `Syntax error` on both references (D-NAMDOT, 2026-08-01), while
  a space inside a name is simply skipped (D-NAMSPC, 2026-08-08,
  [spec-basic-namspc.md](../spec-basic-namspc.md)).
- **Arrays had a four-dimension limit and the wrong size error** (fixed
  2026-07-29, D-ARR-C and D-ARR-B): the reference has no dimension limit, and
  its size limit is 65535 bytes of elements
  ([arrdim-vg8020-characterization.md](../arrdim-vg8020-characterization.md)).
- **The pointer chain was published on 2026-09-25** (D-ADDR29): `VARTAB`,
  `ARYTAB` and `STREND` read the same on both machines in all nine measured
  states ([readings](../../scratchpad/ptrchain_after.out)). `ARYTAB` alone had
  been refused on 2026-08-01: a program computes array space as
  `STREND-ARYTAB`, and half a chain gives a confident wrong answer
  ([spec-basic-addr29.md](../spec-basic-addr29.md)).

## How zerobas does it

`var_name_key` in [basic/vars.asm](../../basic/vars.asm) reads a name into a
two-character key and resolves its type from the suffix or `deftbl_lookup`;
`is_ident_cont` skips spaces inside a name. The store is a sub-ROM tenant,
[sub/arrays.asm](../../sub/arrays.asm), serving simple variables
(`aeng_scalar_find`, `aeng_scalar_alloc`) and arrays (`ary_resolve` with the
auto-`DIM`, `aeng_dim`, `aeng_erase`, `ary_alloc`). A new simple variable is
inserted at `ARYTAB` by moving the array block up, after checking it fits.
`vars_reset` in [basic/arrays.asm](../../basic/arrays.asm) re-anchors the block
after `RUN`, `NEW`, `CLEAR`, `MAXFILES` and a program edit and writes `VARTAB`;
`STREND` is written wherever the array block's end moves; `clear_vars` resets
the type table, which `ex_deftype` ([basic/usr.asm](../../basic/usr.asm)) and
[sub/deftype.asm](../../sub/deftype.asm) fill. The design is in
[spec-basic-arrays.md](../spec-basic-arrays.md) and its slice specs; the header
comments of `basic/vars.asm` and `sub/arrays.asm` still describe earlier
states, and this page is current where they disagree.

## Related pages

- Keywords: [`LET`](../keywords/LET.md), [`DIM`](../keywords/DIM.md),
  [`ERASE`](../keywords/ERASE.md), [`DEFINT`](../keywords/DEFINT.md),
  [`DEFSNG`](../keywords/DEFSNG.md), [`DEFDBL`](../keywords/DEFDBL.md),
  [`DEFSTR`](../keywords/DEFSTR.md), [`VARPTR`](../keywords/VARPTR.md),
  [`SWAP`](../keywords/SWAP.md), [`CLEAR`](../keywords/CLEAR.md),
  [`NEW`](../keywords/NEW.md), [`RUN`](../keywords/RUN.md),
  [`FRE`](../keywords/FRE.md), [`FOR`](../keywords/FOR.md),
  [`READ`](../keywords/READ.md), [`INPUT`](../keywords/INPUT.md).
- Concepts: [numbers.md](numbers.md), [strings-and-string-space.md](strings-and-string-space.md),
  [memory-map.md](memory-map.md), [program-text.md](program-text.md).

## Tests that cover it

- `make float-acceptance` — typed variables, suffixes, store conversion and the
  `DEF` type rules.
- `make array-acceptance` — arrays, auto-`DIM`, `ERASE`, `VARPTR` of elements,
  and a program edit clearing simple variables.
- `make arrdim-acceptance` — the array size limit and the number of dimensions.
- `make namspc-acceptance`, `make lnblank-acceptance` — spaces and dots in names.
- `make sysvarsweep` — the published work-area variables, `DEFTBL` among them.
- `make kwsweep` and `make kwram` — the everyday and error rows of `LET`, `DIM`,
  `ERASE`, the `DEF` statements and `VARPTR`, and the RAM-usage comparison.
