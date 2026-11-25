<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `TRON` — trace a running program, line by line

> **Spec:** DRAFT 1 (2026-11-25) — 13 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`ktron.py`](../../probes/basic/spec/ktron.py), with TRON's, TROFF's and REM's cases
> together; it reads the screen); every rule is executable and every recorded output is read by one. Not yet
> reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`TRON` ("trace on") makes a running program print each line's number, in
square brackets, just before the line runs — so you can watch the order in
which lines execute. [`TROFF`](TROFF.md) switches it off. zerobas prints
exactly what the Philips VG-8020 prints in every case we have measured.

## Syntax

```
TRON
```

No arguments.

## Details

- **The trace is `[` + the line number + `]`**, in plain decimal with no
  padding (`[20]`, `[30000]`), and **no new line of its own**: it appears
  wherever the cursor is, so `[20]A` is line 20 printing `A`.
- **One trace per line, not per statement.** `20 PRINT"A":PRINT"B"` is traced
  once.
- **Every time a line is entered from the top, it is traced**: the target of a
  `GOTO` or `GOSUB`, and the lines of a `FOR` loop each time round.
- **Returning into the middle of a line is not traced**: the rest of a line
  after a `GOSUB` that returns, or after a `FOR` that `NEXT` sends back to.
  A loop spread over lines 20 (`FOR`) and 30 (`NEXT`) traces `[20][30][30]`.
- **The line holding `TRON` is not traced** — the trace is switched on while
  that line is already running.
- **Statements typed at the prompt are never traced**, but `TRON` typed at the
  prompt does trace the next `RUN`.
- **It stays on** through `RUN` and `END` (an `END` line is itself traced).
  `TROFF` or `NEW` switches it off.
- **`TRON 1`** — anything after `TRON` — is `Syntax error` (error 2), the only
  error the VG-8020 raises for `TRON`.

## Example

```
10 TRON
20 PRINT "A":GOTO 40
30 PRINT "skipped"
40 FOR I=1 TO 2
50 PRINT I;
60 NEXT
70 TROFF:PRINT
80 PRINT "B"
RUN
[20]A
[40][50] 1 [60][50] 2 [60][70]
B
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_tron.out`](../../scratchpad/kwdoc_tron.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

Line 10 is not traced, line 30 is jumped over, line 40 runs once while 50 and
60 run twice, and line 80 comes after `TROFF`.

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/tron_rules.py`](../../probes/basic/spec/tron_rules.py), loader in
[`ktron_model.py`](../../probes/basic/spec/ktron_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Evidence.** One probe, [`probes/basic/spec/ktron.py`](../../probes/basic/spec/ktron.py): the trace goes to the
screen, so the probe reads the SCREEN, as [`kstop.py`](../../probes/basic/spec/kstop.py) does -- each case starts with
`NEW` and `CLS`, types a short program and the commands it names, and keeps the normalised screen (the prompt -- "Ok"
there, "ZB" here, a deliberate difference -- read as one token). The model is kstop's small BASIC
([`kstop_model.py`](../../probes/basic/spec/kstop_model.py)), the one interpreter for every screen-reading keyword
probe: it types each case and predicts the WHOLE screen. Run file
[`scratchpad/KTN_run1.out`](../../scratchpad/KTN_run1.out) (JSON, 2026-11-25).
- **[KTN FX *i*]** (TRON), the lines typed after NEW / CLS:
  0: `10 PRINT "A"` / `20 PRINT "B"` / `TRON` / `RUN`
  1: `10 PRINT "A":PRINT "B"` / `TRON` / `RUN`
  2: `10 GOSUB 30:PRINT "R":END` / `30 PRINT "S":RETURN` / `TRON` / `RUN`
  3: `10 FOR I=1 TO 2` / `20 NEXT` / `TRON` / `RUN`
  4: `10 TRON:PRINT "A"` / `20 PRINT "B"` / `RUN`
  5: `TRON` / `PRINT "D"`
  6: `10 PRINT "A"` / `TRON` / `RUN` / `RUN`
  7: `10 PRINT "A"` / `20 END` / `TRON` / `RUN`
  8: `10 PRINT "A"` / `TRON` / `NEW` / `10 PRINT "A"` / `RUN`
  9: `10 TRON 1` / `RUN`
  10: `10 PRINT "A";` / `20 PRINT "B"` / `TRON` / `RUN`
  11: `30000 PRINT "A"` / `TRON` / `RUN`
  12: `10 GOTO 30` / `20 PRINT "X"` / `30 PRINT "Y"` / `TRON` / `RUN`

**Controls** ([`ktron_controls.py`](../../probes/basic/spec/ktron_controls.py)): each changes ONE law of the
interpreter and runs over the reference's cases: “a line is traced once per statement” is FALSE on 2 of the 8 cases R-TRON-TRACE selects (e.g. KTN FX 1); “going on after a RETURN traces the line again” is FALSE on 1 of the 8 cases R-TRON-TRACE selects (e.g. KTN FX 2); “the trace starts a new line” is FALSE on 4 of the 8 cases R-TRON-TRACE selects (e.g. KTN FX 2); “the line holding TRON is traced too” is FALSE on 1 of the 5 cases R-TRON-ONOFF selects (e.g. KTN FX 4); “a typed statement is traced” is FALSE on 3 of the 5 cases R-TRON-ONOFF selects (e.g. KTN FX 5); “NEW leaves the trace on” is FALSE on 1 of the 5 cases R-TRON-ONOFF selects (e.g. KTN FX 8).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/tron_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/tron_rules.py --write` -->

**2 rules; 2 hold on the reference. Of the 105 recorded outputs (each case's normalised screen (prompts as <prompt>, the echo of the typed lines, the output, the messages)): 105 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. The trace

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-TRON-TRACE** With the trace on, each program line prints `[n]` -- its number, no padding, NO new line of its own -- when it is entered from its top: by falling in, as a GOTO or GOSUB target, each time a NEXT sends a loop back to it. Once per line, not per statement; going on in the middle of a line (after a GOSUB's RETURN) prints nothing. An END line is traced. | 8 | ✓ | ✓ |

#### 2. On and off

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-TRON-ONOFF** TRON starts the trace at the NEXT line entered (the line holding it is not traced); a statement typed at the prompt is never traced; the trace stays on through RUN, and NEW switches it off. Anything after TRON is error 2. | 5 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `TRON` uses the same amount of
free memory on both machines, but the two machines write different cells of
the documented work area while doing it.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] The trace inside an error handler or an ON KEY / ON INTERVAL trap, a trace line that wraps
  past the screen edge, `LIST` of a REM's text (the program region).

## What we found, and how

- **The trace switch lived in zerobas's own memory** (fixed 2026-10-13). The
  VG-8020 keeps it in the published cell `TRCFLG` (`&HF7C4`): 175 under
  `TRON`, 0 under `TROFF`, in every context measured. zerobas kept its own
  copy elsewhere, so `PEEK(&HF7C4)` read 0. It uses `TRCFLG` now, with the
  same values ([`officialcell_probe.out`](../../scratchpad/officialcell_probe.out)).
- **`TRON` and `TROFF` arrived on 2026-07-27.** Until then they were an honest
  `Syntax error`. The VG-8020 was measured first, and the rules above — per
  line, not per statement; jump targets traced, returns into a line not;
  never in direct mode; kept by `RUN`, cleared by `NEW` — come from that
  measurement: [missing-vg8020-characterization.md](../missing-vg8020-characterization.md) §5.
- **`TRON` exposed a prompt difference** (fixed 2026-07-27). The trace leaves
  the cursor in the middle of a row, and there the VG-8020 starts its prompt on
  a fresh line while zerobas printed it straight after the trace. zerobas now
  does the same.
- **The first test could not see the trace** (2026-09-14, D-KWBATCH3). It
  printed a fixed marker after `TRON`, which a `TRON` that did nothing prints
  just as well; its replacement packed onto a single line, and a single line is
  never traced. The row now spans several lines and reads the trace itself.

## Where it lives

`ex_tron` and the trace printer `trace_line` are in
[basic/missing.asm](../../basic/missing.asm); the trace is called from the
program loop `run_program` in [basic/program.asm](../../basic/program.asm), on
the path that enters a line from the top. The on/off flag is `TRACEFLAG`,
cleared by `NEW`.

## Tests that cover it

- `make missing-acceptance` — the trace battery: per line, jumps, loops,
  `GOSUB`, direct mode, `RUN`, `END`, `NEW`.
- `make kwsweep` — the row that reads the trace (`[20][30]` before its
  marker), and the error row `TRON 1` (2).
- `make kwram` — the RAM-usage comparison.
