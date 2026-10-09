<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `TROFF` — stop tracing

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`TROFF` ("trace off") switches off the line-number trace that
[`TRON`](TRON.md) switched on. zerobas behaves exactly like the Philips
VG-8020 in every case we have measured.

## Syntax

```
TROFF
```

No arguments.

## Details

- **The line holding `TROFF` is still traced**, because the trace is printed
  before the line runs. The lines after it are not.
- **`TROFF` when the trace is already off** does nothing, and is not an error.
- **`NEW` also switches the trace off; `RUN` and `END` do not.** A program that
  ends with the trace on leaves it on for the next `RUN`.
- **`TROFF 1`** — anything after `TROFF` — is `Syntax error` (error 2), the
  only error the VG-8020 raises for `TROFF`.
- Everything about what the trace looks like is on the [`TRON`](TRON.md) page.

## Example

```
10 TRON
20 A=1
30 TROFF:PRINT "off"
40 PRINT "B"
50 ON ERROR GOTO 80
60 TROFF 1
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
[20][30]off
B
Error 2
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_troff.out`](../../scratchpad/kwdoc_troff.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

Line 30 is traced although it switches the trace off; line 40 is not.

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `TROFF` uses the same amount of
free memory on both machines, but the two machines write different cells of
the documented work area while doing it.

## What we found, and how

- **`TROFF` arrived with `TRON` on 2026-07-27**, after the VG-8020 was
  measured: [missing-vg8020-characterization.md](../missing-vg8020-characterization.md) §5.
- **A test of `TROFF` has to look at the line *after* it** (2026-09-14,
  D-KWBATCH3). The first row printed a fixed marker, which a `TROFF` that did
  nothing prints as well; and because the line carrying `TROFF` is traced
  either way, only an untraced line after it can show that `TROFF` worked. The
  row now reads `[20][30]` where a dead `TROFF` would read `[20][30][40][50]`.

## Where it lives

`ex_troff` in [basic/missing.asm](../../basic/missing.asm) clears the
`TRACEFLAG` byte that the program loop in
[basic/program.asm](../../basic/program.asm) checks before each line.

## Tests that cover it

- `make missing-acceptance` — the trace battery, `TROFF` included.
- `make kwsweep` — the row that reads where the trace stops, and the error
  row `TROFF 1` (2).
- `make kwram` — the RAM-usage comparison.
