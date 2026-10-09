<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes verify=no reason="needs a printer" -->

# `LFILES` — list the files on the disk to the printer

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error not yet proven. No known
> divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`LFILES` prints the disk's directory on the printer instead of the screen;
`LFILES "pattern"` prints only the names that match. It is
[`FILES`](FILES.md) with a different destination and a different layout. It
needs both a disk and a printer, so the reference is the National CF-3300
with a printer attached; zerobas sends the same bytes to the printer in every
case we have measured.

## Syntax

```
LFILES [<file name pattern>]
```

The pattern is a string expression with the wildcards `?` and `*`, as for
`FILES`.

## Details

- **One entry per line**, not three per row: each entry is `NAME    .EXT`,
  a space, then a carriage return and line feed. The screen form packs
  entries side by side; the printer form does not.
- **A pattern filters**, with wildcards: `LFILES "*.BAS"` prints only the
  `.BAS` files.
- **Nothing matches** — or a bare `LFILES` on an empty disk — prints nothing
  on the printer and `File not found` (error 53) on the screen.
- **The printer head ends at column 0**, because every entry ends its own
  line; `LPOS(0)` reads 0 afterwards even if an `LPRINT "AB";` had left the
  head part-way along a line before.
- **The screen is the output again for the next statement**:
  `LFILES:PRINT "X"` puts the `X` on the screen, not the printer.
- **With no printer connected** it waits for one: in a test run without a
  printer, `LFILES` never finished.
- **Without a disk system** (the diskless VG-8020) `LFILES` is `Illegal
  function call` (error 5).

Not yet measured on the reference: the full set of errors (`LFILES 5`, a bad
drive name), which is why "every error" is not yet proven. `FILES`'s set is
measured; see its page.

## Example

On the test disk, which holds `TEST.BIN`, `HI.TXT`, `PROG.BIN`, `PROG.BAS`,
`PROG2.BAS` and `PROG3.BAS`, with a printer attached:

```
10 ON ERROR GOTO 50
20 LFILES "*.BAS"
30 LFILES "NONE.*"
40 END
50 PRINT "Error";ERR:RESUME NEXT
RUN
Error 53
```

The screen shows only the error from line 30. The printer receives three
lines, one per `.BAS` file:

```
PROG    .BAS
PROG2   .BAS
PROG3   .BAS
```

(each with a trailing space before the line end). This example needs a printer,
so the example checker does not run it; `make lptverb-acceptance` measures the
same behaviour — the printer's log, byte for byte — on zerobas and the
CF-3300.

## Differences from the reference

None known.

The rungs not yet proven are **RAM usage** and **every error**: `LFILES`'s
error cases have not been enumerated on the reference, because a case that
reaches the printer waits for it.

## What we found, and how

- **`LFILES` arrived on 2026-08-06** (D-LFILES), after its behaviour had been
  measured on the references first (D-LPTVERB). The obvious build — `FILES`
  with its output pointed at the printer — would have been wrong: it ran all
  the entries together on one line with no separators. The printer form is
  its own layout ([spec](../spec-basic-lfiles.md)).
- **An empty disk printed nothing** (fixed 2026-08-07, D-DSKMSG); the CF-3300
  says `File not found`, as for a pattern with no match.
- **The printer head was left where an earlier `LPRINT ...;` parked it**
  (fixed 2026-09-12, D-DFEND). `LFILES` did not reset the head position, so
  `LPOS(0)` read 2 where the CF-3300 reads 0, and two extra bytes reached the
  printer at the next prompt. A no-match `LFILES` must still leave the head
  alone — both machines do — so the reset happens only when something was
  printed.
- **A diskless zerobas ran `LFILES`** (fixed 2026-09-15, D-NODISKGAP).
  `FILES` had been gated on the disk system twelve days earlier, but `LFILES`
  enters the same code by a second door, and no test asked about it. The
  VG-8020 answers error 5; so does zerobas now.

## Where it lives

- Main ROM: `ex_lfiles` in [basic/files.asm](../../basic/files.asm), which
  shares `ex_files`'s path through `verb_run` and the `H_FILE` hook.
- Disk ROM, [disk/kernel.asm](../../disk/kernel.asm): `hk_files` and
  `hkf_body`; `df_emit` and `df_end` choose the printer layout and reset the
  head.
- Measurements: [lptverb-msx1-characterization.md](../lptverb-msx1-characterization.md)
  §4, rules R-LF1 to R-LF7.

## Related concepts

- [Disk BASIC](../concepts/disk.md) — files on a 720 KB floppy, one drive

## Tests that cover it

- `make lptverb-acceptance` — the printer log for a full listing, a pattern,
  no match, an empty disk and the screen afterwards, against the CF-3300.
- `make kwsweep` — the row that parks the head with `LPRINT "AB";` and reads
  `LPOS(0)` after `LFILES`.
- `make nodisk-acceptance` — error 5 on a diskless machine.
- `make kwram` — the RAM-usage comparison.
