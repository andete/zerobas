<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# Strings and string space — where string values live

> **Status (2026-10-09):** what a program can see agrees with the Philips
> VG-8020 in every measured case: the size of the string space, what each
> string costs, when `Out of string space` and `String formula too complex`
> happen. One open difference in which error wins (TIER 6, below); the
> published `FRETOP` cell is not kept yet (TIER 4).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

MSX BASIC keeps the characters of strings in a separate area of memory, the
**string space**. Its size is set by `CLEAR n` — 200 bytes when the machine
starts — and `FRE("")` says how much of it is left. A string variable itself
is only a small entry that says how long the string is and where its
characters are; the characters may be in the string space, or, for a string
that came straight from the program (a literal or a `DATA` item), in the
program text itself, where they cost the string space nothing.

A string is at most 255 characters long. Joining strings past that is
`String too long` (error 15); running out of string space is
`Out of string space` (error 14); an expression that needs more than ten
unfinished string results at once is `String formula too complex` (error 16).
zerobas has all three limits where the VG-8020 has them.

## How it works

### The descriptor

Every string value — a variable, an array element, an intermediate result —
is described by 3 bytes: the **length** (0 to 255), then the **address** of
its characters, low byte first. `VARPTR(A$)` returns the address of these 3
bytes on both machines, so `PEEK(VARPTR(A$))` is the length (see
[`VARPTR`](../keywords/VARPTR.md)). An empty string has length 0 and no
characters anywhere.

### What uses string space, and what does not

| statement (in a program) | string space used | why |
|---|---|---|
| `A$="HELLO"` | 0 | `A$` points at the characters in the program line |
| `READ A$` (from `DATA`) | 0 | the same: it points into the `DATA` line |
| `B$=A$`, when `A$` points into the program | 0 | the rule is *where the characters are*, not what was written |
| `B$=A$+"!"` | 6 | a computed string is always stored in the string space |
| `B$=A$`, when `A$` is in the string space | `LEN(A$)` | a copy: each variable owns its characters |
| `A$="HELLO"` typed **without** a line number | 5 | the typed line is not kept, so it is copied |
| `X=LEN(STRING$(100,"A"))` | 0 afterwards | an intermediate result is given back |

A string variable's entry costs **6 bytes of `FRE(0)`** on both machines
([`fremem_run.out`](../../scratchpad/fremem_run.out)); string array elements
use the same string space.

Writing into a string that points into the program with the `MID$` statement
first copies it into the string space, so the program line never changes (`LIST` shows the original on
both machines); with no room for the copy the `MID$` line is error 14.
Editing the program clears all variables, so nothing is left pointing at a
line that has gone.

### Size: `CLEAR n` and `FRE("")`

- `CLEAR n` makes the string space **exactly n bytes**; a bare `CLEAR`, `NEW`
  and `RUN` keep the last size, and moving the memory top (`CLEAR n,top`)
  does not change it. The space is carved out of the same
  memory as variables, so `FRE(0)` drops by exactly the difference: going from
  `CLEAR 200` to `CLEAR 1000` takes 800 bytes from `FRE(0)` on both machines.
- `FRE("")` (any string argument) first tidies the string space — see below —
  and then reports what is left. It reads `n` right after `CLEAR n`.
- A string that does not fit is `Out of string space` (error 14) and the
  failed allocation is undone: `FRE("")` afterwards reads what it read before.

### Garbage collection

Strings are stored from the top of the string space downwards. A string
variable's old characters stay behind, unused, when it gets a new value —
*garbage*. When a new string does not fit, every string still in use is moved
up against the top and the garbage disappears; only a string that still does
not fit is error 14. `FRE("")` compacts first, so it never counts garbage as
used. Nothing else a program sees depends on when compaction happens.

### Temporary strings

While an expression is evaluated, each unfinished string result —
`MID$(A$,1)` waiting for the `+` to its right, for example — holds a
*temporary descriptor*. Both machines have room for **10** of them: a nested
expression that needs 10 works, one that needs 11 is
`String formula too complex` (error 16). A temporary is given back as soon as
it is used up (by `LEN`, `ASC`, `VAL`, a `PRINT` item, a comparison, or the
`+` that consumed it), so a long *flat* chain such as
`PRINT MID$(A$,1);MID$(A$,1);…` with 11 or more items works on both.

On both machines the 10 descriptors sit at the published `TEMPST` (`$F67A`),
and the cursor `TEMPPT` (`$F678`) points at `$F67A` between statements.

### The 255-character limit

The length is one byte, so 255 is the maximum everywhere:

| you write | you get |
|---|---|
| a concatenation longer than 255 (`C$+C$` with `C$` 200 long) | 15 `String too long` |
| `STRING$(256,"A")`, `SPACE$(256)`, `CHR$(256)` | 5 `Illegal function call` |
| `STRING$(255,"A")` in the 200-byte starting space | 14 `Out of string space` |

## Example

```
10 CLEAR 1000:A$="HELLO"
20 PRINT FRE("")
30 B$=A$+"!":PRINT FRE("")
40 C$=STRING$(200,"X"):PRINT FRE("")
50 ON ERROR GOTO 100
60 D$=C$+C$+C$
70 D$=SPACE$(250):E$=D$:F$=D$:G$=D$
80 PRINT FRE("");LEN(G$)
90 END
100 PRINT "Error";ERR:RESUME NEXT
RUN
 1000
 994
 794
Error 15
Error 14
 44  0
```

`A$` points into line 10 and costs nothing; `B$` costs 6 bytes, `C$` 200.
Line 60 would be 600 characters long. In line 70 `E$` and `F$` are 250-byte
copies of `D$`, and the copy for `G$` does not fit in the 44 bytes left.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_strings-and-string-space.out`](../../scratchpad/kwdoc_strings-and-string-space.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

- **Which error wins when the string space is small** (open, TIER 6). With
  less free string space than twice an operand's length, `X$+X$` is
  `Out of string space` here where both references say `String too long`:
  `X$=STRING$(128,"A"):PRINT LEN(X$+X$)` in the starting 200 bytes is the
  plainest case. zerobas copies the first operand before it checks the
  combined length. Joost ruled on 2026-09-27 that the string space's ownership
  rules be reworked so the length is checked first; not done yet
  ([spec-basic-strlong.md](../spec-basic-strlong.md) §5).
- **The published `FRETOP` cell (`$F69B`) is not kept** (TIER 4, Joost's
  *"All 29"* ruling of 2026-09-24, see [memory-map.md](memory-map.md)).
  zerobas keeps the same pointer at its own address; it moves by the same
  amount for each string.
- **One measured case holds less, not more:** `X=LEN(MID$(…)+"Q")` leaves
  0 bytes in use here and 3 on the VG-8020, because zerobas extends a
  temporary in place. Left as it is: it can only give a program more room
  ([`strtemp_s2b.out`](../../scratchpad/strtemp_s2b.out)).
- **Not measured:** whether the reference copies a literal passed as a string
  argument to a `DEF FN` function. zerobas copies it.

## What we found, and how

- **A real program found the biggest one.** *Vleermuis*, a 1989 type-in
  game that the project loads on both machines from a cassette image
  ([`scratchpad/vleermuis/`](../../scratchpad/vleermuis/), see the
  [README](../../README.md)), stopped here with `Out of string space` at its
  fifth `READ A$(A)` of a 40-character `DATA` row, where the VG-8020 reads all
  120. zerobas copied every string it read; the references point at the
  program text. Joost re-tiered it TIER 1 and it was fixed on 2026-10-07
  (D-READREF); Vleermuis now runs the same on both machines.
- **The same was true of literals** (fixed 2026-10-07, D-LITREF). The row
  that chose the rule was `READ B$:A$=B$`, which costs nothing on the VG-8020:
  the test is where the characters are, not how the right side was written
  ([`litref_before.out`](../../scratchpad/litref_before.out)). The prediction
  that `MID$` would then write into the program was wrong: the VG-8020 copies
  the string out first, and so does zerobas now.
- **There used to be one pool, not two** (fixed 2026-07-29, D-CLP): `CLEAR n`
  was ignored and `FRE("")` reported all free memory. Sizing the space then
  showed what a resting `FRE("")` had hidden: `A$=STRING$(100,"A")` needed 300
  bytes for a moment, so after `CLEAR 100` it was error 14 here only
  ([clearpool-vg8020-characterization.md](../clearpool-vg8020-characterization.md)).
- **A concatenation over 255 was cut to 255** (fixed 2026-08-28, D-STRLONG),
  where both references raise `String too long`.
- **zerobas held about two temporaries per nesting level**, so moving its pool
  to the published `TEMPST` at 10 entries first broke expressions at depth 6.
  Temporaries are now given back as on the reference (D-TEMPPOL), and the pool
  moved on 2026-09-25: depths 6 to 14 of six shapes agree
  ([`tempst_pt.out`](../../scratchpad/tempst_pt.out)).
- **Dead intermediate results stayed until the next compaction** (narrowed
  2026-09-27, D-S2BHEAP): one released at the edge is now handed back at once,
  as on the reference; 4 of 8 rows differed, 1 does now (the generous one).

## How zerobas does it

The **main ROM** side is [basic/str-engine.asm](../../basic/str-engine.asm):
the temporary-descriptor pool (`str_temp_alloc`, `str_snapshot_to_temp`, its
overflow `sst_overflow`), concatenation (`str_concat_tail`), the copy-out
before `MID$` writes (`mid_own`), and the "points into the program?" test
`desc_in_text`, which `let_ref` (scalars, called from
[basic/interp.asm](../../basic/interp.asm)) and `ary_let_ref` (array elements,
from [basic/arrays.asm](../../basic/arrays.asm)) use to store a descriptor
without copying. `READ` stores its descriptor through `tgt_store_ref` in
[basic/vars.asm](../../basic/vars.asm). `CLEAR n` records the size in
`POOLSIZE` ([basic/clear.asm](../../basic/clear.asm)).

The **string space itself** is managed in the sub ROM,
[sub/strheap.asm](../../sub/strheap.asm). `heap_alloc` takes bytes from the
downward-moving edge `FRETOP`; its floor is `strheap_floor` = the memory
ceiling minus `POOLSIZE`, derived each time from `HIMEM` and the recorded
size, never stored. `sh_free_gap` answers `FRE("")` and `sh_free_vars`
answers `FRE(0)`. `sh_append` builds a concatenation and checks the 255 limit
before it allocates; `sh_var_store` lets a variable adopt a temporary's
characters instead of copying them.

The collector (`strheap_gc`) is zerobas's own design, not the reference's:
it finds every descriptor that points into the string space (simple
variables, array elements, the temporaries and the arguments of active
`DEF FN` calls), sorts them by address and moves each string up once. The
sort borrows scratch memory from the free space between the arrays and the
stack, and falls back to a method that needs none when that is too small.
Earlier designs are in
[spec-basic-arrays-slice4a-string-heap.md](../spec-basic-arrays-slice4a-string-heap.md)
and [spec-basic-clearpool.md](../spec-basic-clearpool.md); where they
disagree with this page, this page is current.

## Related pages

- Keywords: [`CLEAR`](../keywords/CLEAR.md), [`FRE`](../keywords/FRE.md),
  [`VARPTR`](../keywords/VARPTR.md), [`READ`](../keywords/READ.md),
  [`DATA`](../keywords/DATA.md), [`MID$`](../keywords/MID$.md),
  [`STRING$`](../keywords/STRING$.md), [`SPACE$`](../keywords/SPACE$.md),
  [`LET`](../keywords/LET.md), [`FN`](../keywords/FN.md).
- Concepts: [memory-map.md](memory-map.md) (where the string space sits),
  [variables.md](variables.md), [program-text.md](program-text.md),
  [errors.md](errors.md).
- More keywords: [`ASC`](../keywords/ASC.md), [`CHR$`](../keywords/CHR$.md), [`LEN`](../keywords/LEN.md).

## Tests that cover it

- `make clearpool-acceptance` and `make binfre-acceptance` — the size `CLEAR`
  sets and keeps, what each string costs in both pools, `Out of string space`.
- `make readref-acceptance` and `make litref-acceptance` — `DATA` strings,
  program literals and `A$=B$` use no string space; a direct-mode literal is
  copied; `MID$` copies a string out of the program first.
- `make string-acceptance` — the string functions and concatenation, and the
  temporary-pool edge (depth 9 fits, depth 10 of that shape is error 16).
- `make str-domain-acceptance` — the 0 to 255 argument rules.
- `make kwsweep` — the everyday and error rows of every string keyword.
- `make kwram` — the RAM-usage comparison.
