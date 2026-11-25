<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `RETURN` — come back from a subroutine

> **Spec:** DRAFT 1 (2026-11-25) — 9 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kgosub.py`](../../probes/basic/spec/kgosub.py), with GOTO's, GOSUB's and RETURN's cases
> together); every rule is executable and every recorded output is read by one. Not yet reviewed ([the keyword
> plan](spec-plan.md)).
>
> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`RETURN` ends a subroutine entered with [`GOSUB`](GOSUB.md) and continues with
the statement after that `GOSUB`. `RETURN 40` ends the subroutine but
continues at line 40 instead. zerobas behaves like the Philips VG-8020 in
every case we have measured, errors included.

## Syntax

```
RETURN
RETURN <line number>
```

## Details

- **A bare `RETURN` resumes mid-line**, at the statement after the `GOSUB`.
- **`RETURN <line>` is a `GOTO` with the subroutine closed first.** The
  subroutine's record is removed, then the program jumps to the line.
- **With no `GOSUB` open, both forms are `RETURN without GOSUB`** (error 3) —
  checked before the line number is even read, so `RETURN 99` and `RETURN B`
  with nothing open are error 3 too.
- **If the line does not exist**, `RETURN 99` is `Undefined line number`
  (error 8), but the subroutine has already been closed, and the error is
  reported against the `RETURN`'s own line, not the caller's. A malformed
  argument (`RETURN B`, `RETURN "A"`) is `Syntax error`; measured with
  `RETURN B`, that too closes the subroutine first.
- **`RETURN` throws away the `FOR` loops opened inside the subroutine**, and
  keeps those that were open before the `GOSUB`.
- **It cannot be used to leave an `ON ERROR` handler.** A handler is not
  entered through `GOSUB`, so `RETURN` there is error 3 on both reference
  machines — use `RESUME`.
- **`RETURN` at the end of an `ON KEY`/`ON INTERVAL`/... `GOSUB` handler**
  also switches that trap back on.

### Errors

| you write | you get |
|---|---|
| `RETURN`, `RETURN 99`, `RETURN B` with no `GOSUB` open | 3 `RETURN without GOSUB` |
| `RETURN 99` inside a subroutine, no line 99 | 8 `Undefined line number` |
| `RETURN "A"` inside a subroutine | 2 `Syntax error` |

The whole set is {3} for the bare form and {2, 3, 8} for the line form, the
same on both machines.

## Example

```
10 GOSUB 100:PRINT "Back"
20 GOSUB 200
30 PRINT "Skipped"
40 PRINT "Line 40"
50 ON ERROR GOTO 90
60 RETURN
70 END
90 PRINT "Error";ERR:RESUME NEXT
100 PRINT "Sub":RETURN
200 RETURN 40
RUN
Sub
Back
Line 40
Error 3
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_return.out`](../../scratchpad/kwdoc_return.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/return_rules.py`](../../probes/basic/spec/return_rules.py), model in
[`kgosub_model.py`](../../probes/basic/spec/kgosub_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Evidence.** One probe, [`probes/basic/spec/kgosub.py`](../../probes/basic/spec/kgosub.py) (on the shared RAM-record
harness [`ramrec.py`](../../probes/basic/spec/ramrec.py)), typed on both machines; run file
[`scratchpad/KGS_run1.out`](../../scratchpad/KGS_run1.out) (2026-11-25; zerobas's side on that day's build). Each case
is a block of 30 lines from its base n: line n starts from nothing (`CLEAR`, `ON ERROR` set again), runs the
statement(s) under test and ends `GOTO n+25`; the case's own target lines sit at n+5 .. n+20; n+25 records the first
and the last error (RESUME NEXT carries on after one), a counter WN% and WP%, the bits of the lines the case reached
(1 line n, 2 the rest of line n after a GOSUB, 4 / 8 / 16 lines n+5 / n+10 / n+15) -- so a rule says WHICH lines ran.
A loop that could run for ever carries the guard `ON -(WN%>20) GOTO n+25` (21 = "did not stop").
- **[KGS FX *i*]** (RETURN):
  16: `RETURN`
  17: `GOSUB n+5:WP%=WP% OR 2` (line n+5: `WP%=WP% OR 4:RETURN n+10`; line n+10: `WP%=WP% OR 8`)
  18: `GOSUB n+5:WP%=WP% OR 2` (line n+5: `WP%=WP% OR 4:RETURN 65000`)
  19: `GOSUB n+5:WP%=WP% OR 2` (line n+5: `WP%=WP% OR 4:RETURN:WP%=WP% OR 8`)
  20: `GOSUB n+5:WP%=WP% OR 2:RETURN` (line n+5: `RETURN`)
  21: `FOR I=1 TO 2:GOSUB n+5:WN%=WN%+1:NEXT` (line n+5: `RETURN`)
  22: `GOSUB n+5:WP%=WP% OR 2:NEXT` (line n+5: `FOR I=1 TO 3:WN%=WN%+1:RETURN`)
  23: `GOSUB n+5:WP%=WP% OR 2` (line n+5: `FOR I=1 TO 3:WN%=WN%+1:<guard>:NEXT:RETURN`)
  24: `FOR I=1 TO 2:GOSUB n+5:WP%=WP% OR 2` (line n+5: `WN%=WN%+1:<guard>:NEXT`)

**Controls** ([`kgosub_controls.py`](../../probes/basic/spec/kgosub_controls.py)): each is a rival rule run over the
reference's cases: “RETURN keeps the subroutine's FOR frames” is FALSE on 1 of the 2 cases R-RETURN-FRAMES selects (e.g. KGS FX 22); “NEXT in a subroutine reaches a FOR outside it” is FALSE on 1 of the 2 cases R-RETURN-FRAMES selects (e.g. KGS FX 24); “RETURN n ignores n and comes back after the GOSUB” is FALSE on 1 of the 4 cases R-RETURN-BACK selects (e.g. KGS FX 17).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/return_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/return_rules.py --write` -->

**3 rules; 3 hold on the reference. Of the 36 recorded outputs (each case's first and last error, WN% (a counter; 21 = the probe's guard ended a loop that did not stop) and WP% (the bits of the lines the case reached)): 36 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. Coming back

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-RETURN-BACK** RETURN continues after its GOSUB; the rest of RETURN's own line is not run. RETURN n continues at line n instead, dropping the GOSUB. A GOSUB inside a FOR returns into the loop, which goes on (2 runs); a whole FOR inside the subroutine runs before RETURN (3 runs). | 4 | ✓ | ✓ |
| **R-RETURN-FRAMES** RETURN drops every FOR frame opened since its GOSUB: a NEXT after it is error 1 (NEXT without FOR); and a NEXT inside a subroutine does not reach a FOR opened before the GOSUB (error 1). | 2 | ✓ | ✓ |

#### 2. Errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-RETURN-ERRORS** RETURN with no GOSUB pending is error 3 (RETURN without GOSUB) -- also a second RETURN once the GOSUB came back; RETURN n to a line that does not exist is error 8. | 3 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**; the size of a `GOSUB`'s record
is discussed on the [`GOSUB`](GOSUB.md) page.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] RETURN n into the middle of a FOR's body; RETURN inside an ON ERROR handler.

## What we found, and how

- **`RETURN <line>` was missing** (added 2026-08-02, D-RETLN). The 27-row
  measurement that preceded it found four rules nobody had written down: the
  "no `GOSUB` open" check comes first; both failures close the subroutine
  before they raise; the error belongs to the `RETURN`'s line; and the
  textbook use — leaving an `ON ERROR` handler — does not exist on MSX
  ([retln-msx1-characterization.md](../retln-msx1-characterization.md),
  [spec-basic-retln.md](../spec-basic-retln.md)). The first version also broke
  `RETURN` from a trap handler; a different gate caught it, not the 27 rows.
- **`RETURN` kept loops the subroutine had opened** (fixed 2026-08-19,
  D-FORRET). zerobas kept `FOR` and `GOSUB` records in separate stacks, so
  nothing was thrown away. Four rows written before the fix separated the
  real rule — "back to the depth at the time of the `GOSUB`" — from a cheaper
  one that fitted the first row only
  ([spec-basic-forret.md](../spec-basic-forret.md)).
- **A `GOSUB` with junk after its line number** made `RETURN` come back onto
  the junk (fixed 2026-09-08, D-FLOWTAIL); see [`GOSUB`](GOSUB.md).
- **The `RETURN <line>` form had no row in the keyword sweep** until
  D-KWRETRES. Its row jumps to a line that skips an increment a bare `RETURN`
  would have run, so a `RETURN` that ignored its line number shows a different
  value.

## Where it lives

`ex_return` and `ret_frame` in [basic/program.asm](../../basic/program.asm);
the line form jumps through `ex_goto_at` in
[basic/interp.asm](../../basic/interp.asm), the same code `GOTO` uses.

## Related concepts

- [Interrupts and traps](../concepts/interrupts-and-traps.md) — what runs between statements

## Tests that cover it

- `make kwsweep` — the bare and line rows, and the error rows for {2, 3, 8}.
- `make lnblank-acceptance` — the `lnrt-*` rows: `RETURN <line>`'s errors,
  where they are reported, and the loops it discards.
- `make stop-trap-acceptance` — `RETURN` from a trap handler.
- `make kwram` — the RAM-usage comparison.
