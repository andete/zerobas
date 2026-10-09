<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `USR` and `DEF USR` — call a machine-code routine

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. Two recorded
> differences: `DEF USR` accepts an address past 65535, and a bare `USR` with
> no argument is accepted (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`DEF USR n = address` stores the start address of a machine-code routine in
one of ten slots, 0 to 9. `USR n(x)` then calls that routine with the value
`x` and returns whatever the routine leaves as its result. zerobas hands the
argument over and takes the result back exactly where MSX machine code
expects them, so a routine written for a real MSX works unchanged.

## Syntax

```
DEF USR[<n>] = <address>
USR[<n>](<argument>)
```

`n` is a single digit, 0 to 9; without it, slot 0 is meant.

## Details

- **The ten addresses live in the published `USRTAB` cells** (`&HF39A`, two
  bytes each).
- **How the routine receives its argument** (the MSX convention, measured on
  the VG-8020): the argument is in `DAC`, the number accumulator at `&HF7F6`,
  and its type in `VALTYP` (`&HF663`: 2 integer, 4 single, 8 double). An
  integer sits at `DAC+2` and `DAC+3`, low byte first. The routine is entered
  with HL pointing at `DAC` and A holding the type.
- **How the result comes back:** whatever `DAC` holds when the routine
  returns, read according to `VALTYP` — a routine may change the type. A
  routine that only returns hands back its argument unchanged; what it leaves
  in the HL register means nothing.
- **The address may be given as a negative number**, as for `POKE`:
  `DEF USR=-8192` is `&HE000`; `DEF USR=-1` is accepted.
- **Each `USR` call runs the routine exactly once**, even inside an
  expression that then fails.
- **Errors:**

| you write | you get |
|---|---|
| `USR()`, `USR(1,2)`, `USR1()`, `USR1(1,2)` | error 2, `Syntax error` |
| `DEF USR`, `DEF USR9` | error 2, `Syntax error` |
| `DEF USR="A"`, `DEF USR9="A"` | error 13, `Type mismatch` |
| `DEF USR=70000` | error 6, `Overflow` on the VG-8020; accepted here (see *Differences*) |

Calling a slot that was never set has not been compared with the reference.

## Example

The routine reads the integer at `DAC+2`, adds 1 and stores it back; its last
byte (`C9`, a plain return) doubles as a second routine that changes nothing.

```
10 FOR I=0 TO 7:READ B$
20 POKE &HD000+I,VAL("&H"+B$):NEXT
30 DATA 2A,F8,F7,23,22,F8,F7,C9
40 DEFUSR=&HD000:DEFUSR1=&HD007
50 PRINT USR(5);USR1(5);USR1(1.5)
60 ON ERROR GOTO 90
70 A=USR(1,2)
80 END
90 PRINT "Error";ERR:RESUME NEXT
RUN
 6  5  1.5
Error 2
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_usr.out`](../../scratchpad/kwdoc_usr.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

- **`DEF USR=70000` is accepted here** and `Overflow` (error 6) on the
  VG-8020, for every slot (D-DEFUSRRANGE, found 2026-09-27). zerobas stores
  something and runs on. Open, TIER 6.
- **A bare `A=USR` or `A=USR1`, with no argument at all, is accepted here**
  and `Syntax error` on the VG-8020 (D-USRBARE, found 2026-09-28). Open,
  TIER 6; it does not block the every-error rung, because error 2 already has
  agreeing rows (`USR()`, `USR1(1,2)`).

The rung not yet proven is **RAM usage**: it has not been rated for `USR`.

## What we found, and how

- **`DEF USR` and `USR` came early** (by June 2026): the classic way a BASIC
  loader jumps into code it has just loaded is `DEFUSR=&Hxxxx : A=USR(0)`.
  The addresses went into the published `USRTAB` from the start, but the
  argument travelled in a register of zerobas's own choosing.
- **That convention was zerobas's own, and MSX code could not read it**
  (fixed 2026-09-25, D-ADDR29). Measured on the VG-8020, the argument is in
  `DAC` and the result is read back from `DAC`; zerobas used HL both ways and
  left `DAC` alone. A routine that read `DAC+2` got 0 where the reference
  gives the argument — four of six test routines answered differently
  ([`usrdac_after.out`](../../scratchpad/usrdac_after.out) is the 6/6 after
  the fix). Joost ruled on 2026-09-24 that `DAC` be matched in full: *"USR
  then finds its argument in DAC"*.
- **`USR` made a good counter.** A five-byte routine that increments a memory
  cell turned "how many times was this evaluated?" into a number. It showed
  that `"AB"+USR(0)` ran the routine zero times here and once on the
  references; fixed 2026-09-01 (D-CATFIX), it runs once
  ([spec-basic-catusr.md](../spec-basic-catusr.md)).

## Where it lives

[basic/usr.asm](../../basic/usr.asm): `ex_def` reads `DEF USR` (and hands
`DEF FN` to [`FN`](FN.md)'s code), `usr_setslot` stores the address,
`ev_usr` parses a call and `usr_call` / `usr_ret` perform it.

## Tests that cover it

- `make kwsweep` — `DEF USR` and `USR` for slot 0 and a numbered slot, each
  calling a one-byte routine that returns its argument, and the error rows.
- `make unit-test` — the entry state a routine sees, and the returned value.
- `make catusr-acceptance` — the evaluation count.
