<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `CLEAR` — reset the variables, and size the string space

> **Spec:** DRAFT 1 (2026-11-25) — 16 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kdim.py`](../../probes/basic/spec/kdim.py), with DIM's, ERASE's and CLEAR's cases
> together; it reads the screen); every rule is executable, every recorded output is read by one, and
> every rule is pinned by a control of its own. Not yet reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-11-06):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One recorded
> difference: less free memory than the VG-8020 (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`CLEAR` throws away every variable and array, and can at the same time set the
size of the string space (where string values are kept) and the highest memory
address BASIC may use. zerobas behaves like the Philips VG-8020 in every case
we have measured, except that it has less free memory to give out.

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
- **A stopped program cannot be continued** after a `CLEAR` typed at the
  prompt: `CONT` says `Can't CONTINUE`.
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
| anything after the last argument: `CLEAR 1,2,3`, `CLEAR 200,&HF000,3`, `CLEAR 200 X` | 2 `Syntax error`, before a bad value is reported and before anything is cleared; only `Overflow` while reading an argument, and a negative first argument, come first |

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

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/clear_rules.py`](../../probes/basic/spec/clear_rules.py), loader in
[`kdim_model.py`](../../probes/basic/spec/kdim_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does. The check is the
whole interpreter; what pins a rule's SENTENCE is its controls -- each rule has at least one rival law that is false
on its own cases.

**Evidence.** One probe, [`probes/basic/spec/kdim.py`](../../probes/basic/spec/kdim.py): it reads the SCREEN, as
[`kstop.py`](../../probes/basic/spec/kstop.py) does -- each case starts with `NEW` and `CLS`, types a short program
and the commands it names, and keeps the normalised screen (the prompt -- "Ok" there, "ZB" here, a deliberate
difference -- read as one token). The memory-limit cases are far from the edge (`DIM A%(20000)`, `CLEAR 30000` exceed
any free memory a 32 K VG-8020 has), so no expectation depends on a free-memory figure. The model is kstop's small
BASIC ([`kstop_model.py`](../../probes/basic/spec/kstop_model.py)), the one interpreter for every screen-reading keyword
probe. Run file [`scratchpad/KDM_run1.out`](../../scratchpad/KDM_run1.out) (JSON, 2026-11-25).
- **[KDM FX *i*]** (CLEAR), the lines typed after NEW / CLS:
  26: `10 A=5:CLEAR:PRINT A` / `RUN`
  27: `10 ON ERROR GOTO 90:CLEAR` / `20 X=1/0` / `90 PRINT "[H]":END` / `RUN`
  28: `10 READ A:CLEAR:READ B:PRINT A;B` / `20 DATA 1,2` / `RUN`
  29: `10 CLEAR:PRINT "[K]"` / `RUN`
  30: `10 CLEAR 500:PRINT FRE("")` / `RUN`
  31: `PRINT FRE("")`
  32: `10 CLEAR 500` / `RUN` / `CLEAR` / `PRINT FRE("")`
  33: `10 CLEAR 300,&HC000:PRINT FRE("")` / `RUN`
  34: `10 CLEAR -1` / `RUN`
  35: `10 CLEAR 70000` / `RUN`
  36: `10 CLEAR 30000` / `RUN`
  37: `10 CLEAR "A"` / `RUN`
  38: `10 CLEAR 200,&H7000` / `RUN`
  39: `10 CLEAR 200,` / `RUN`
  40: `10 CLEAR,` / `RUN`
  41: `10 A=5:ON ERROR GOTO 90:CLEAR -1` / `20 END` / `90 PRINT "[";A;"]":END` / `RUN`

**Controls** ([`kdim_controls.py`](../../probes/basic/spec/kdim_controls.py)): each changes ONE law of the
interpreter and runs over the reference's cases: “CLEAR keeps ON ERROR” is FALSE on 1 of the 4 cases R-CLEAR-RESET selects (e.g. KDM FX 27); “CLEAR keeps READ's position” is FALSE on 1 of the 4 cases R-CLEAR-RESET selects (e.g. KDM FX 28); “a bare CLEAR goes back to 200 bytes” is FALSE on 1 of the 4 cases R-CLEAR-SIZE selects (e.g. KDM FX 32); “a refused CLEAR has already cleared the variables” is FALSE on 1 of the 8 cases R-CLEAR-ERRORS selects (e.g. KDM FX 41); “a comma and no top is error 2” is FALSE on 1 of the 8 cases R-CLEAR-ERRORS selects (e.g. KDM FX 39).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/clear_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/clear_rules.py --write` -->

**3 rules; 3 hold on the reference. Of the 88 recorded outputs (each case's normalised screen (prompts as <prompt>, the echo of the typed lines, the output, the messages)): 88 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. What it clears

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CLEAR-RESET** CLEAR clears the variables, switches ON ERROR off, takes READ back to the first item, and the program goes on after it. | 4 | ✓ | ✓ |

#### 2. The string space

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CLEAR-SIZE** The string space is 200 bytes at start-up; CLEAR n makes it exactly n (FRE of an empty string reads n); a bare CLEAR keeps the last size, and so does moving the top (CLEAR n,top). | 4 | ✓ | ✓ |

#### 3. Errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CLEAR-ERRORS** Every argument is checked before anything changes, so a refused CLEAR leaves the variables and the handler as they were. A negative size is 5, past 65535 6, more than free memory 7, a string 13; a top below &H8000 is 5; a comma and no top 24 (Missing operand); a comma and no size 2. | 8 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

**zerobas has less free memory than the VG-8020**, so a string space that just
fits there can be `Out of memory` here: on 2026-09-27 `CLEAR 25000` was
accepted on the VG-8020 and refused here. Since 2026-10-13 it fits on both
(the disk's sector buffers moved out of a diskless machine's memory), and the
first refused size is between 27000 and 27500 here since 2026-10-14 (26000 to
27000 before, 25000 to 26000 before a second step on 2026-10-13), while the
VG-8020 still accepts 28000
([`fatfloor_clear_probe.out`](../../scratchpad/fatfloor_clear_probe.out),
[`drawcompact_clear_probe.out`](../../scratchpad/drawcompact_clear_probe.out),
[`wszero_s6_clear2.out`](../../scratchpad/wszero_s6_clear2.out)).
That belongs to the **RAM usage** rung, which is not yet proven.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] CLEAR n,top's room for the program (`CLEAR 200,&H8050`), `CLEAR 200,65535`, `CLEAR ,&HD000`; open
  files (the CF-3300's claim); CLEAR inside a GOSUB or a FOR.

## What we found, and how

- **`CONT` still continued after a typed `CLEAR`** (fixed 2026-11-06,
  D-CLEARCONT). Both references answer `Can't CONTINUE`; zerobas went back into
  the stopped program with its `FOR` loop wiped and stopped at `NEXT without
  FOR`. Found by a typed session; the details are on the
  [`CONT`](CONT.md) page.
- **Something after the last argument was noticed too late** (fixed
  2026-10-24, D-CLEAR3ARG). The VG-8020 checks that the statement ends before
  it looks at the memory-top value: `CLEAR 1,2,3` is `Syntax error`, not
  `Illegal function call`, and `CLEAR 200,&H8100,3` is `Syntax error`, not
  `Out of memory`. zerobas checked the value first, and when the value was good
  (`CLEAR 200,&HF000,3`, `CLEAR 200 X`) it carried out the `CLEAR`, which also
  removes an `ON ERROR` handler, so the `Syntax error` that followed could not
  be caught. Thirteen cases on both machines pinned the order
  ([`clear3_run.out`](../../scratchpad/clear3_run.out),
  [`clear3_run2.out`](../../scratchpad/clear3_run2.out), from
  [`clear3_probe.py`](../../scratchpad/clear3_probe.py)); all agree since
  ([`clear3_after.out`](../../scratchpad/clear3_after.out)).
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
- **A string space just under 32768 still hung zerobas** (fixed 2026-11-01,
  D-CLEARWRAP). The room check adds the program size, the requested string
  space and a margin, and for `CLEAR 32100` to `CLEAR 32767` that sum passed
  65535 and wrapped round to a small number, so the request looked as if it
  fit. Both references answer `Out of memory`; zerobas now does too
  ([`clearwrap_run.out`](../../scratchpad/clearwrap_run.out) before,
  [`clearwrap_after.out`](../../scratchpad/clearwrap_after.out) after).
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

## Related concepts

- [Files and devices](../concepts/files-and-devices.md) — numbered channels to the disk, the tape, the screen and the printer
- [The memory map](../concepts/memory-map.md) — where BASIC keeps things in RAM
- [Strings and string space](../concepts/strings-and-string-space.md) — where string values live
- [Variables](../concepts/variables.md) — names, types, arrays, and where they live

## Tests that cover it

- `make clearpool-acceptance` — the string-space size, what a bare `CLEAR`,
  `NEW` and `RUN` keep, and `Out of string space`.
- `make clearclose-acceptance` — files closed by `CLEAR` on the disk build.
- `make kwsweep` — the bare form (a variable really reset), the string-space
  form, the memory-top form, and the error rows (`CLEAR 32767` among them).
- `make missing-acceptance` — something after the last argument, with and
  without a good value, under `ON ERROR` (rows `cl-bad3`, `cl-ok3`,
  `cl-onejunk`, and `cl-colon` as the control).
- `make kwram` — the RAM-usage comparison.
