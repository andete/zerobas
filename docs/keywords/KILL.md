<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `KILL` — delete a file from the disk

> **Status (2026-10-10):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`KILL "name"` deletes a file from the disk and gives its space back. The name
may contain the wildcards `?` and `*`, and then every matching file is
deleted. It is a Disk BASIC statement, so the reference is the National
CF-3300; zerobas leaves the disk in the same state, byte for byte, and raises
the same errors in every case we have measured.

## Syntax

```
KILL <file name>
```

The name is a string expression and may carry a drive (`"A:HI.TXT"`).

## Details

- **The space comes back at once**: deleting a small file on the test disk
  raises [`DSKF`](DSKF.md) by one.
- **A wildcard deletes every match**: `KILL "*.BAS"` removes all the `.BAS`
  files and leaves the rest. The disk image afterwards is byte-identical to
  the CF-3300's.
- **An open file cannot be deleted** — open for input, output, append or
  random access, and also when it is only matched by a wildcard. A file that
  has been `CLOSE`d can be.
- **Deleting another file leaves an open one intact.**

### Errors

| situation | error |
|---|---|
| no such file | 53 `File not found` |
| the file is open | 64 `File still open` |
| a drive past `B:` (`KILL "Q:A.TXT"`) | 62 `Bad drive name` |
| a number instead of a name (`KILL 5`) | 13 `Type mismatch` |
| no name at all (`KILL`) | 24 `Missing operand` |
| no disk in the drive | 70 `Disk offline` |
| no disk system (the diskless VG-8020) | 5 `Illegal function call` |

The whole set of errors `KILL` raises on the CF-3300 for these cases is
{13, 24, 53, 62, 64}; zerobas raises the same set.

## Example

On the test disk, which holds `TEST.BIN`, `HI.TXT`, `PROG.BIN`, `PROG.BAS`,
`PROG2.BAS` and `PROG3.BAS`:

```
10 ON ERROR GOTO 70
20 KILL "HI.TXT"
30 KILL "*.BAS"
40 KILL "HI.TXT"
50 FILES
60 END
70 PRINT "Error";ERR:RESUME NEXT
RUN
Error 53
TEST    .BIN PROG    .BIN
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_kill.out`](../../scratchpad/kwdoc_kill.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **The clock stopped while the disk worked** (fixed 2026-10-10, D-HOOKDI):
  `KILL` of a long file kept `TIME` running for none of its work here,
  against 39 % on the CF-3300; now 15 %. The disk ROM's code ran with interrupts off, so keys typed meanwhile
  were lost too. The CF-3300 switches them off only while it moves each
  sector, and zerobas still moves more sectors (D-FDCDI)
  ([before](../../scratchpad/verbclock_run2.out),
  [after](../../scratchpad/verbclock_after.out)).
  `make loaddi-acceptance` has a `kill` row.

- **A missing file printed zerobas's own `load error`** (fixed 2026-08-07,
  D-DSKMSG); the CF-3300 prints `File not found`, error 53, the same answer
  as `FILES` with no match.
- **On a diskless machine `KILL` ran and failed on the missing disk** (fixed
  2026-09-03, D-CHANHOOK); the VG-8020 answers error 5, and so does zerobas.
- **An empty drive printed `load error` and carried on** (fixed 2026-09-11,
  D-DISKERR); the CF-3300 raises `Disk offline`, trappable, and stops.
- **`KILL` while another file was being written damaged that file** (fixed
  2026-09-23, D-ALIASWCELL): the deletion shared the open file's sector
  buffer, and the file's first record came back as zero bytes.
- **`KILL` deleted an open file from under its channel** (fixed 2026-09-28,
  D-KILLOPEN). The CF-3300 refuses with `File still open`. The first build of
  the fix refused correctly but reported error 0, because putting the open
  channel back afterwards wiped the code; that was fixed the same day
  (D-ERRKEEP).

## Where it lives

- Main ROM: `ex_kill` in [basic/files.asm](../../basic/files.asm), through
  `verb_run` and the `H_KILL` hook.
- Disk ROM: `hk_kill` in [disk/kernel.asm](../../disk/kernel.asm) checks the
  open files and runs the delete loop over every match.

## Related concepts

- [Disk BASIC](../concepts/disk.md) — files on a 720 KB floppy, one drive

## Tests that cover it

- `make diskbasic-acceptance` — a plain and a wildcard `KILL`, each compared
  with the CF-3300 by the disk image it leaves.
- `make kwsweep` — the everyday row (the free space `DSKF` sees come back)
  and the error rows for {13, 24, 53, 62, 64}.
- `make dout-acceptance` — `KILL` of a file open for output is error 64.
- `make nodiskerr-acceptance` — error 70 on an empty drive.
- `make nodisk-acceptance` — error 5 on a diskless machine.
- `make kwram` — the RAM-usage comparison.
