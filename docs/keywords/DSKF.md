<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `DSKF` — free space on the disk

> **Status (2026-10-10):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One recorded
> difference: drive 2 (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`DSKF(d)` returns the number of free clusters on drive `d`. On the 720 KB test
disk a cluster is one kilobyte, so the answer reads as free kilobytes: 706 on
the fresh test disk (this page's example), one more after a small file is deleted. It is a Disk BASIC
function, so the reference is the National CF-3300; zerobas gives the same
number and the same errors in every case we have measured.

## Syntax

```
DSKF(<drive number>)
```

One argument, always.

## Details

- **Drives 0 and 1 both name the one drive** of a single-drive machine, and
  both answer the same count.
- **Drive 2 is the "phantom" drive B:** on the CF-3300 it prints
  *Insert diskette for drive B:* and waits for a key. What happens after that
  is not measured, so test programs leave drive 2 alone.
- **Two checks, in this order:**
  1. the argument is not a byte (below 0 or above 255) → `Illegal function
     call` (error 5);
  2. a byte above 2 → `Bad drive name` (error 62). Measured for 3, 4, 8 and 9.
- **A string argument** (`DSKF("A")`) is `Type mismatch` (error 13).
- **No argument, or two** (`DSKF()`, `DSKF(0,0)`) is `Syntax error` (error 2).
- **An argument error is raised before any counting**, as on the
  reference.
- **Without a disk system** (the diskless VG-8020) `DSKF` is `Illegal function
  call` (error 5).

| you write | you get |
|---|---|
| `DSKF(0)`, `DSKF(1)` on the fresh test disk | `706` |
| `DSKF(2)` | the CF-3300 asks for a disk in drive B: and waits |
| `DSKF(3)`, `DSKF(9)` | error 62, `Bad drive name` |
| `DSKF(-1)`, `DSKF(256)` | error 5, `Illegal function call` |
| `DSKF("A")` | error 13, `Type mismatch` |
| `DSKF()`, `DSKF(0,0)` | error 2, `Syntax error` |

The whole set of errors `DSKF` raises on the CF-3300 for these cases is
{2, 5, 13, 62}; zerobas raises the same set.

## Example

On the test disk, which holds `TEST.BIN`, `HI.TXT`, `PROG.BIN`, `PROG.BAS`,
`PROG2.BAS` and `PROG3.BAS`:

```
10 ON ERROR GOTO 80
20 A=DSKF(0)
30 KILL "PROG2.BAS"
40 PRINT A;DSKF(0)
50 PRINT DSKF(9)
60 PRINT DSKF(-1)
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 706  707
Error 62
Error 5
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_dskf.out`](../../scratchpad/kwdoc_dskf.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**Drive 2.** The CF-3300 treats drive 2 as a second, logical drive B: on its
one mechanism and asks for that disk; zerobas answers at once with drive A's
count — a free-space figure for a disk that was never inserted. Joost ruled on
2026-10-09 that zerobas gets the same prompt mechanism (D-DSKIB, open).

One possible gap is filed without a reproduction: with a file
open, an error the disk ROM reports for `DSKF` (such as `Disk offline`) could
lose its error code and print as a plain `load error`. The same flaw was
fixed for `KILL`, `NAME`, `COPY` and `SAVE` on 2026-09-28; for `DSKF` it has
not been reproduced (D-ERRKEEP2, TIER 3).

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **The clock stopped while the disk worked** (fixed 2026-10-10, D-HOOKDI):
  `DSKF(0)` kept `TIME` running for 2 % of its count here, against 76 % on
  the CF-3300; now 25 %. The disk ROM's code ran with interrupts off, so keys typed meanwhile
  were lost too. The CF-3300 switches them off only while it moves each
  sector, and zerobas still moves more sectors (D-FDCDI)
  ([before](../../scratchpad/verbclock_run.out),
  [after](../../scratchpad/verbclock_after.out)).
  `make loaddi-acceptance` has a `dskf` row.

- **An early test said `DSKF` was a stub, and it was the test** (2026-09-12,
  D-KWDISK). `DSKF(0)` read 0 because nothing was in the emulated drive; with
  the test disk mounted it reads 707 on both machines.
- **Any drive number was accepted** (fixed 2026-09-16, D-DSKFDRV). zerobas
  answered 707 for drive 0, 1 and 9 alike — nothing checked the argument —
  where the CF-3300 says `Bad drive name` from drive 3 up. The boundary was
  measured at four points above it and two below.
- **`DSKF(-1)` and `DSKF(256)` were error 62, not 5** (fixed 2026-09-29,
  D-DSKFRANGE): the reference checks for a byte before it checks the drive.
- **A bad argument used to cost a full count** (fixed 2026-09-29,
  D-DSKFSLOW). `DSKF()` and `DSKF("A")` counted the whole disk before raising
  their error; the reference raises at once. The error was right, the wait
  was not.
- **`DSKF` while a file was being written damaged that file** (fixed
  2026-09-23, D-ALIASWCELL). The count shared a sector buffer with the open
  file, so the file came back with leftover bytes instead of its data. The
  same fault hit `KILL`, `NAME`, `COPY`, `DSKI$`, `DSKO$` and `SAVE`.

## Where it lives

- Main ROM: `ev_ff_dskf` in [basic/expr.asm](../../basic/expr.asm) evaluates
  the argument and hands it to the disk ROM through the `H_DSKF` hook.
- Disk ROM: `hk_dskf` in [disk/kernel.asm](../../disk/kernel.asm) checks the
  byte and the drive, then counts with `fat_count_free`
  ([basic/fat-prim-body.inc](../../basic/fat-prim-body.inc)).

## Related concepts

- [MSX-DOS](../concepts/msx-dos.md) — booting DOS, the BDOS, and the way back to BASIC

## Tests that cover it

- `make kwsweep` — the everyday row (the free count on the test disk), `KILL`'s row that
  reads `DSKF` before and after, and the error rows for {2, 5, 13, 62}.
- `make diskbasic-acceptance` — the free-space differential against the
  CF-3300.
- `make nodisk-acceptance` — error 5 on a diskless machine.
- `make kwram` — the RAM-usage comparison.
