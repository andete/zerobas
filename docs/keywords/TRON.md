<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `TRON` — trace a running program, line by line

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

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `TRON` uses the same amount of
free memory on both machines, but the two machines write different cells of
the documented work area while doing it.

## What we found, and how

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
