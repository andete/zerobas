<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `RETURN` — come back from a subroutine

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

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**; the size of a `GOSUB`'s record
is discussed on the [`GOSUB`](GOSUB.md) page.

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

## Tests that cover it

- `make kwsweep` — the bare and line rows, and the error rows for {2, 3, 8}.
- `make lnblank-acceptance` — the `lnrt-*` rows: `RETURN <line>`'s errors,
  where they are reported, and the loops it discards.
- `make stop-trap-acceptance` — `RETURN` from a trap handler.
- `make kwram` — the RAM-usage comparison.
