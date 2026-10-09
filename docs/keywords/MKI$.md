<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `MKI$` — pack an integer into a 2-byte string

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`MKI$(n)` returns the integer `n` as a two-byte string holding its raw
16-bit value, low byte first. It is how a program puts a number into a
random-access file record (with `FIELD` and `LSET`); [`CVI`](CVI.md) turns the
two bytes back into the number. It is a Disk BASIC function, so the reference
is the National CF-3300. zerobas gives the same bytes and the same errors in
every case we have measured.

## Syntax

```
MKI$(<numeric expression>)
```

One argument, always.

## Details

- **Low byte first.** `MKI$(258)` (258 is `&H0102`) is `CHR$(2)+CHR$(1)`.
  Negative numbers survive the round trip: `CVI(MKI$(-1))` is −1.
- **A fraction is dropped toward zero**: `MKI$(1.5)` packs 1, `MKI$(-1.5)`
  packs −1, `MKI$(-32768.4)` packs −32768. This is the same truncation as
  [`CINT`](CINT.md).
- **The value must fit an integer**, −32768 to 32767, after truncating;
  `MKI$(32768)` and `MKI$(-32769)` are `Overflow` (error 6).
- **Without a disk system** (a diskless MSX such as the VG-8020) `MKI$` is
  `Illegal function call` (error 5): the keyword is known, but the function
  belongs to the disk ROM. On the VG-8020 even `MKI$("A")` is error 5; only a
  syntax fault such as `MKI$(1,1)` is reported first, as error 2. A diskless
  zerobas answers error 5 to the calls measured there (`LEN(MKI$(258))`,
  `ASC(MKI$(1))`, `CVI(MKI$(258))`); its wrong-argument cases are not
  measured.

| you write | you get |
|---|---|
| `MKI$(258)` | `CHR$(2)+CHR$(1)` |
| `MKI$(1.5)`, `MKI$(-1.5)` | the bytes of 1, of −1 |
| `MKI$(32768)`, `MKI$(-32769)` | error 6, `Overflow` |
| `MKI$("A")` | error 13, `Type mismatch` |
| `MKI$()`, `MKI$(1,1)` | error 2, `Syntax error` |
| `MKI$(258)` on a machine without a disk ROM | error 5, `Illegal function call` |

The whole set of errors `MKI$` can raise on the CF-3300 is {2, 6, 13}; zerobas
raises the same set.

## Example

```
10 ON ERROR GOTO 90
20 A$=MKI$(258)
30 B$=RIGHT$(A$,1)
40 PRINT LEN(A$);ASC(A$);ASC(B$)
50 PRINT CVI(MKI$(1.5));CVI(MKI$(-1.5))
60 A$=MKI$(32768)
70 PRINT CVI(MKI$(-32768.4))
80 END
90 PRINT "Error";ERR:RESUME NEXT
RUN
 2  2  1
 1 -1
Error 6
-32768
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_mki_s.out`](../../scratchpad/kwdoc_mki_s.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `MKI$` uses the same amount of
free memory on both machines, but the two write different sets of work-area
cells while doing it.

## What we found, and how

- **A diskless zerobas answered `MKI$`**, where a diskless MSX refuses with
  error 5 (fixed 2026-09-03, D-MKHOOK). On a real MSX the main ROM knows the
  keyword and the disk ROM supplies the function through a documented hook;
  zerobas had the function built into the main ROM. `MKI$` was the first verb
  routed through its hook, and the other disk functions followed the same day
  ([spec-basic-nodisk.md](../spec-basic-nodisk.md) §9–10).
- **The work moved into the disk ROM** (2026-09-17, D-MKINT), under Joost's
  ruling of that day: *"all disk commands need to be in the disk rom"*. The
  behaviour did not change.
- **Out-of-range numbers came back as a string** (fixed 2026-09-29,
  D-MKIRANGE). `MKI$(32768)` packed −32768 and `MKI$(-32769)` packed 32767,
  where the CF-3300 says `Overflow`; worse, `MKI$(-32768.4)` packed 32767
  instead of −32768 — a wrong value, not just a missing error. Found by the
  2026-09-27 run that enumerates every error the reference raises
  ([`t6enum_b3.out`](../../scratchpad/t6enum_b3.out)); before and after:
  [`mkirange_run.out`](../../scratchpad/mkirange_run.out),
  [`mkirange_after.out`](../../scratchpad/mkirange_after.out).
- **`MKI$(1,1)` was `Type mismatch`** (fixed 2026-09-29, D-MKEXTRA); the
  CF-3300 says `Syntax error`. The same fix covered `MKS$` and `MKD$`.
- **The early tests could not see the bytes.** The first row checked only
  `LEN(MKI$(1))=2`, which a function returning two zero bytes would pass.
  A row reading the first byte of 258 was added on 2026-09-13 (D-KWBREADTH)
  and one reading both bytes and their order on 2026-09-14 (D-KWBATCH5).

## Where it lives

- Main ROM: `str_mki` / `str_mkf` in [basic/strvar.asm](../../basic/strvar.asm)
  parse the argument and offer it to the disk ROM through the `MKI$` hook; an
  unclaimed hook is error 5.
- Disk ROM: `hk_mki` in [disk/kernel.asm](../../disk/kernel.asm) truncates a
  fractional argument and checks the range.
- The design of the family is in [spec-basic-mksd.md](../spec-basic-mksd.md).
  One housekeeping item is open (D-MKIREUSE, filed 2026-09-29): `hk_mki`
  carries its own float-to-integer conversion where main has one; replacing
  it changes no behaviour, and it waits on a ruling by Joost.

## Tests that cover it

- `make kwsweep` — the everyday rows (length, both bytes and their order, the
  first byte of 258), the error rows for {2, 6, 13}, and the −32768.4 value,
  all against the CF-3300.
- `make nodisk-acceptance` — error 5 on a diskless machine.
- `make kwram` — the RAM-usage comparison.
