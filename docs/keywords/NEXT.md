<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `NEXT` — end of a `FOR` loop: step, test, go round

> **Spec:** DRAFT 1 (2026-11-25) — 8 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kfor.py`](../../probes/basic/spec/kfor.py), with FOR's and NEXT's cases together);
> every rule is executable and every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-11-25):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✗ (a failing NEXT I does not create I: D-NEXTCREATE).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`NEXT` closes a loop opened by [`FOR`](FOR.md). It adds the step to the loop
variable, compares it with the limit, and either jumps back to the statement
after the `FOR` or lets the program carry on. A bare `NEXT` closes the
innermost open loop; `NEXT I` names the loop; `NEXT J,I` closes several at
once. zerobas behaves like the Philips VG-8020 in every case we have measured,
errors included.

## Syntax

```
NEXT
NEXT <variable>[,<variable>...]
```

## Details

- **A bare `NEXT` takes the innermost loop.**
- **A named `NEXT` must match the whole variable: both significant characters
  and the type.** After `FOR A%=1 TO 3`, `NEXT A` is `NEXT without FOR`
  (error 1), because `A` and `A%` are different variables. So is `NEXT A` after
  `FOR AB=1 TO 3`.
- **A named `NEXT` closes any inner loops it passes.** With `FOR AB` and
  `FOR CD` open, `NEXT AB` abandons the `CD` loop and steps `AB`.
- **`NEXT J,I` is `NEXT J` followed by `NEXT I`**, innermost first. A trailing
  comma (`NEXT J,`) is `NEXT without FOR`; a number in the list (`NEXT J,1`) is
  `Syntax error`.
- **`NEXT A$` is not a type error**: it is `NEXT without FOR`, because no loop
  can have a string variable. The same goes for an array element: `NEXT A(1)`
  is `NEXT without FOR` (and, as on the reference, it creates the array `A` if
  it did not exist). A space before the bracket, `NEXT A (1)`, is read the
  same way.
- **The arithmetic follows the loop's type**: decimal for a single or double
  variable, integer for `%`, where stepping past 32767 is `Overflow` (error 6)
  on the `NEXT` line. See [`FOR`](FOR.md) for the loop rules.
- **`RETURN` throws away loops opened inside the subroutine**, so a `NEXT`
  after it no longer finds them — see [`RETURN`](RETURN.md).

### Errors

| you write | you get |
|---|---|
| `NEXT` or `NEXT I` with no loop open | 1 `NEXT without FOR` |
| `NEXT J` when only `I` is open, `NEXT A$`, `NEXT J,K` with `K` not open | 1 `NEXT without FOR` |
| `NEXT 5` | 2 `Syntax error` |

The whole set of errors `NEXT` raises in its three forms is {1, 2}, the same
on both machines (plus the integer `Overflow` above).

## Example

```
10 FOR I=1 TO 2:FOR J=1 TO 3
20 PRINT I;J;
30 NEXT J,I
40 PRINT:PRINT "I=";I;"J=";J
50 ON ERROR GOTO 80
60 NEXT K
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 1  1  1  2  1  3  2  1  2  2  2  3
I= 3 J= 4
Error 1
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_next.out`](../../scratchpad/kwdoc_next.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/next_rules.py`](../../probes/basic/spec/next_rules.py), model in
[`kfor_model.py`](../../probes/basic/spec/kfor_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Evidence.** One probe, [`probes/basic/spec/kfor.py`](../../probes/basic/spec/kfor.py) (on the shared RAM-record
harness [`ramrec.py`](../../probes/basic/spec/ramrec.py)), typed on both machines; run file
[`scratchpad/KFR_run1.out`](../../scratchpad/KFR_run1.out) (2026-11-25; zerobas's side on that day's build). Every case
is its own line and starts from nothing (`CLEAR`, `ON ERROR` set again); the body counts its runs in WN%; the next line
records the FIRST error (the statement's own), the LAST error (RESUME NEXT carries on along the line, so after a failed
FOR its body and NEXT still run), the runs and the loop variable's bytes. A loop that could run for ever carries a
guard, `ON -(WN%>20) GOTO <the record line>` -- not `IF ... THEN`, whose false test would skip the NEXT after it on the
same line -- so 21 runs read "it did not stop". Three probe faults were caught while building it, each by a run that
read wrong on both machines: the last error alone recorded, the IF guard, and a VARPTR of a variable that does not
exist (error 5 on both machines).
- **[KFR FX *i*]** (NEXT):
  22: `FOR I=1 TO 2:FOR J=1 TO 3:WN%=WN%+1:<guard>:NEXT I`
  35: `NEXT`
  36: `NEXT I`
  37: `FOR I=1 TO 2:WN%=WN%+1:<guard>:NEXT J`
  38: `FOR I=1 TO 2:WN%=WN%+1:<guard>:NEXT I,`
  39: `FOR I=1 TO 2:WN%=WN%+1:<guard>:NEXT 5`
  40: `FOR I=1 TO 2:WN%=WN%+1:<guard>:NEXT I J`
  41: `FOR I=1 TO 2:FOR J=1 TO 2:WN%=WN%+1:<guard>:NEXT J,I,K`

**Controls** ([`kfor_controls.py`](../../probes/basic/spec/kfor_controls.py)): each is a rival rule run over the
reference's cases: “a failing NEXT I does not create I -- zerobas's” is FALSE on 1 of the 1 cases R-NEXT-CREATE selects (e.g. KFR FX 36).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/next_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/next_rules.py --write` -->

**3 rules; 3 hold on the reference. Of the 32 recorded outputs (each case's first and last error, the body's runs (WN%, 21 = the probe's guard ended a loop that did not stop) and the loop variable's bytes after it): 32 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. Closing loops

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-NEXT-CLOSE** NEXT I inside FOR J closes I's loop and drops J's frame: 2 bodies, I 3. | 1 | ✓ | ✓ |

#### 2. Errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-NEXT-ERRORS** NEXT without a FOR and NEXT J inside FOR I are error 1 (NEXT without FOR); a name after the loops ran out -- a trailing comma, a third name (NEXT J,I,K) -- is error 1 once those loops have finished; two names without a comma error 1 at once; a number after NEXT error 2. The loop variable is as the loops left it (NEXT J inside FOR I: I 1, its frame unused). | 6 | ✓ | ✓ |
| **R-NEXT-CREATE** NEXT I without a FOR is error 1 too, and it creates the variable I (it reads 0; VARPTR finds it). | 1 | ✓ | ✗ 1: KFR FX 36 |

<!-- RULES END -->

## Differences from the reference

- **A failing NEXT I creates I** (rule R-NEXT-CREATE, case KFR FX 36; [D-NEXTCREATE](../../todo/open/D-NEXTCREATE.md)):
  after `NEXT I` with no FOR (error 1 on both), the reference's VARPTR(I) finds I; zerobas never created it (VARPTR
  raises error 5, as for any variable that does not exist).

The rung not yet proven is **RAM usage**.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] NEXT reached by GOTO into a loop's body, NEXT after RETURN, NEXT on a different line from its FOR.

## What we found, and how

- **`NEXT` added two whole numbers** (fixed 2026-09-27, D-FORFLOAT). A loop
  with a fractional step never ended and one past 32767 wrapped round to
  negative numbers; `NEXT` now uses the same decimal arithmetic as the rest of
  BASIC, as the reference does. The details are on the [`FOR`](FOR.md) page.
- **Four `NEXT` forms were missing, all found and fixed on 2026-08-08**, each
  measured on both reference machines first:
  - **Matching on the full name and type** (D-FORVAR). zerobas compared one
    letter, so `NEXT A` closed a `FOR AB` loop. Measuring showed the type is
    part of the match too, which nobody had predicted
    ([forvar-msx1-characterization.md](../forvar-msx1-characterization.md)).
  - **`NEXT J,I`** (D-NXLIST) was `Syntax error`. It took three rounds of
    measurement to pin down: a trailing comma is not a bare `NEXT`, and a
    number in the list is a different error
    ([nxlist-msx1-characterization.md](../nxlist-msx1-characterization.md)).
  - **`NEXT A(1)`** (D-NXARY): the reference evaluates the subscript, and so
    creates the array, before failing to match
    ([spec-basic-nxary.md](../spec-basic-nxary.md)).
  - **`NEXT A (1)`** with a space (D-TGTSPC): the space is still in the stored
    line on all three machines, so the parser has to skip it
    ([spec-basic-tgtspc.md](../spec-basic-tgtspc.md)).
- **The tests had a blind spot.** `NEXT` had one row, the bare form, and a bare
  `NEXT` never exercises the name matching at all. Rows for the named and the
  comma-list forms were added (D-KWBATCH7).

## Where it lives

`ex_next` in [basic/program.asm](../../basic/program.asm), with `nx_comma`
(the list), `nx_scan` and `nx_cmp` (finding the matching loop) and `nx_have`
(step and test). The arithmetic is `combine_add` and `combine_cmp` in
[basic/float-arith.asm](../../basic/float-arith.asm); array names go through
the shared `tgt_parse` in [basic/vars.asm](../../basic/vars.asm).

## Tests that cover it

- `make forvar-acceptance` — name and type matching, and the decimal loops.
- `make nxlist-acceptance` — `NEXT J,I`, trailing commas, numbers in the list.
- `make nxary-acceptance` and `make tgtspc-acceptance` — `NEXT A(1)` and
  `NEXT A (1)`.
- `make kwsweep` — the bare, named and comma-list rows, and the error rows for
  {1, 2}.
- `make kwram` — the RAM-usage comparison.
