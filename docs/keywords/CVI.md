<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `CVI` — read an integer back from a 2-byte string

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`CVI(s$)` takes the first two bytes of a string and returns the integer they
hold, low byte first. It is the reading half of [`MKI$`](MKI$.md):
`CVI(MKI$(n))` is `n`. Programs use it on fields read from a random-access
file. It is a Disk BASIC function, so the reference is the National CF-3300;
zerobas gives the same values and the same errors in every case we have
measured.

## Syntax

```
CVI(<string expression>)
```

One argument, always.

## Details

- **Low byte first**: `CVI("AB")` is 16961, which is 66*256+65 ("B" is 66,
  "A" is 65).
- **The full integer range comes back**, sign included:
  `CVI(MKI$(-1))` is −1 and `CVI(MKI$(32767))` is 32767.
- **Only the first two bytes count.** A longer string is fine and the rest is
  ignored: `CVI(MKS$(1.5))`, given four bytes, is 5441.
- **A string shorter than two bytes** (`CVI("A")`, `CVI("")`) is
  `Illegal function call` (error 5). zerobas once read past the end of the
  string here; it no longer does.
- **A number instead of a string** (`CVI(5)`) is `Type mismatch` (error 13).
  But when the argument itself goes wrong first, its own error wins:
  `CVI(LEFT$("AB"))` is `Syntax error` and `CVI(0*(1/0)+1)` is
  `Division by zero`, on the CF-3300 and here.
- **Without a disk system** (a diskless MSX such as the VG-8020) `CVI` is
  `Illegal function call` (error 5): the keyword is known, but the function
  belongs to the disk ROM. A diskless zerobas does the same for the calls
  measured there (`CVI("AB")`, `CVI(MKI$(258))`).

| you write | you get |
|---|---|
| `CVI("AB")` | 16961 |
| `CVI(MKI$(-1))` | −1 |
| `CVI(MKS$(1.5))` | 5441 (first two of four bytes) |
| `CVI("A")`, `CVI("")` | error 5, `Illegal function call` |
| `CVI(5)` | error 13, `Type mismatch` |
| `CVI()`, `CVI("AB","AB")` | error 2, `Syntax error` |
| `CVI("AB")` on a machine without a disk ROM | error 5, `Illegal function call` |

The whole set of errors `CVI` can raise on the CF-3300 is {2, 5, 13}; zerobas
raises the same set.

## Example

```
10 ON ERROR GOTO 80
20 PRINT CVI(MKI$(258));CVI(MKI$(-1))
30 PRINT CVI("AB")
40 PRINT CVI(MKS$(1.5))
50 A=CVI("A")
60 A=CVI(5)
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 258 -1
 16961
 5441
Error 5
Error 13
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_cvi.out`](../../scratchpad/kwdoc_cvi.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `CVI` uses the same amount of
free memory on both machines, but the two write different sets of work-area
cells while doing it.

## What we found, and how

- **Three wrong answers in one function** (fixed 2026-08-31, D-CVITM).
  `CVI(5)` was `Syntax error` instead of `Type mismatch`; `CVI("A")` read one
  byte of the string and one byte of whatever followed it, and answered a
  plausible 8769 instead of error 5; and the first fix briefly turned `CVI()`
  into `Type mismatch`, because an empty argument has to be judged before the
  type question is asked
  ([spec-basic-cvitm.md](../spec-basic-cvitm.md)).
- **That fix had a hole** (fixed the same day, D-CVISTRTM): `CVI(0*(1/0)+1)`
  answered `Type mismatch` where the CF-3300 says `Division by zero`. The
  argument is now evaluated first, so its own error wins
  ([spec-basic-cvistrtm.md](../spec-basic-cvistrtm.md)).
- **Which machine is the reference was settled by measurement** (2026-09-02).
  The VG-8020 answers error 5 to every `CVI`. The National CF-3000, a
  cassette machine whose main ROM is byte-identical to the CF-3300's, also
  answers 5 — so the difference is the disk ROM, and the CF-3300 is the
  machine that can judge `CVI`. The same argument had settled it for `LSET`
  the same day ([spec-basic-lsetref.md](../spec-basic-lsetref.md)).
- **A diskless zerobas answered `CVI`** where a diskless MSX refuses (fixed
  2026-09-03, D-MKHOOK): it now goes through its documented hook, and with no
  disk ROM nobody answers
  ([spec-basic-nodisk.md](../spec-basic-nodisk.md) §10).
- **The conversion moved into the disk ROM** (2026-09-17, D-CVMOVE), and that
  was a compatibility fix: main had redone the conversion after the hook
  returned, so a different disk ROM's answer would have been overwritten. The
  first version of the move broke `CVI(MKI$(258))` — the two functions shared
  a scratch buffer, and a round trip made it overwrite its own input. Caught
  by the test rows before it shipped.

## Where it lives

- Main ROM: `ev_ff_cvi` / `ev_ff_cv` in [basic/expr.asm](../../basic/expr.asm)
  parse the argument, check its length and type, and offer it to the disk ROM
  through the `CVI` hook; an unclaimed hook is error 5.
- Disk ROM: `hk_cv` in [disk/kernel.asm](../../disk/kernel.asm) does the
  conversion. [`CVS`](CVS.md) and [`CVD`](CVD.md) share both routines, with a
  width of 4 and 8 bytes.

## Tests that cover it

- `make kwsweep` — the everyday row (`CVI(MKI$(7))`), the sign and range row
  (−1 and 32767), the short-string row, and the error rows for {2, 5, 13},
  all against the CF-3300.
- `make nodisk-acceptance` — error 5 on a diskless machine.
- `make kwram` — the RAM-usage comparison.
