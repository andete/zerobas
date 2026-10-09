<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes run='LOAD "PROG3.BAS"' answers='LIST|LOAD "PROG3.BAS",R|LOAD "NONE.BAS"' -->

# `LOAD` — replace the program with one from a file

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known user-visible
> divergence; one open internal item (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`LOAD "file"` reads a BASIC program from disk or cassette and makes it the
program in memory; the old one is gone. With `,R` it then runs it. On disk
the reference is the National CF-3300, and `LOAD` reads both a tokenised file
(written by [`SAVE`](SAVE.md)) and an ASCII one (written by `SAVE ...,A`). On
cassette the reference is the Philips VG-8020, and `LOAD "CAS:..."` reads an
ASCII program; a tokenised tape program is [`CLOAD`](CLOAD.md)'s.
[`RUN "file"`](RUN.md) is the same load followed by a run.

## Syntax

```
LOAD <file name>[,R]
```

The file name is a string expression (`LOAD A$` works) and may carry a device:
`"A:PROG.BAS"` for a drive, `"CAS:name"` for the cassette.

## Details

- **The old program is replaced, not merged.** To add lines to the program in
  memory, use [`MERGE`](MERGE.md).
- **`LOAD` in a running program stops it**: the machine returns to `Ok`
  after the load, and nothing after the `LOAD` runs. With `,R` the newly
  loaded program runs instead.
- **The only option is `,R`.** Anything else after the name is
  `Syntax error` (2), including `,S`, which belongs to [`BLOAD`](BLOAD.md).
- **A truncated tokenised file is not an error.** The CF-3300 loads what is
  there and stops, silently, at every point the file can be cut.
- **On cassette**, the tape is searched by name; a bare `LOAD "CAS:"` takes the
  next program. Only ASCII programs count: a tokenised program or a binary
  file of the same name is stepped over without a message. The search prints
  `Skip :` for each ASCII program with another name and `Found:` for the one
  taken.
  A program that is not on the tape is not an error — the machine keeps
  searching; Ctrl-STOP during the search is `Device I/O error` (19).
- **On a diskless machine** a name with no device reads the cassette, and a
  drive name (`"A:X"`) is `Bad file name` (56).

### Errors

| situation | error |
|---|---|
| the file does not exist on the disk | 53 `File not found` |
| a number instead of a name (`LOAD 5`) | 13 `Type mismatch` |
| no name at all (`LOAD`) | 24 `Missing operand` |
| an option other than `,R` (`LOAD "X.BAS",Q`, `,S`) | 2 `Syntax error` |
| a tape search broken with Ctrl-STOP | 19 `Device I/O error` |
| a drive name on a diskless machine | 56 `Bad file name` |

The enumerated set is {13, 24, 53} for the plain form and {2, 53} for `,R`,
the same on both machines.

## Example

On a disk holding `PROG3.BAS`, the one-line program `10 PRINT"[3h]"`. The
program is typed, then `LOAD`, `LIST`, `LOAD ...,R` and a missing file are
typed as commands:

```
10 PRINT "OLD"
20 END
LOAD "PROG3.BAS"
LIST
10 PRINT"[3h]"
LOAD "PROG3.BAS",R
[3h]
LOAD "NONE.BAS"
File not found
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_load.out`](../../scratchpad/kwdoc_load.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

No user-visible difference is known on disk. Two items concern `LOAD`:

- **One open item is filed against `LOAD` at TIER 2** (reasonable time), and
  its own text says the tier tag is stale: what is left in it is moving the
  disk channels of `OPEN` into the disk ROM, as `LOAD` itself already was
  (2026-09-20). Joost ruled on 2026-10-09: *"defer to later"*.
- **A tokenised program on tape.** On 2026-09-27 Joost ruled to *"keep the
  feature"* that let `LOAD "CAS:"` read a tokenised tape program, where the
  VG-8020 skips it and searches on. Since D-CASTYPE (2026-10-08) zerobas's
  tape search filters by file type as the VG-8020 does, so `LOAD "CAS:"` now
  steps over a tokenised program too; a tape holding only a tokenised program
  has not been re-measured since. Joost then ruled on 2026-10-09: *"if we're
  more compliant with reference now that is fine"* — the reference's
  behaviour stands, and the earlier ruling is superseded.

**RAM usage** is not yet proven.

## What we found, and how

- **The tape search did not filter by file type** (fixed 2026-10-08,
  D-CASTYPE, and D-CASBIN for binary files): on a tape holding a tokenised
  `X` and then an ASCII `X`, the VG-8020 loads the ASCII one and zerobas
  loaded the first ([`castype_after.out`](../../scratchpad/castype_after.out)).
- **Ctrl-STOP during a tape search printed `load error` and ran on to the
  next line** (fixed 2026-10-08, D-CASBRK); the VG-8020 raises 19.
- **A wrong option printed `load error`** (fixed 2026-10-07, D-LOADTAIL): the
  references raise a trappable `Syntax error` for `LOAD "X.BAS",Q`, and — found
  while building the test — for `,S` too
  ([`loadtail_after.out`](../../scratchpad/loadtail_after.out)).
- **`LOAD` in a running program did not stop it** (fixed 2026-09-12,
  D-MERGERET). It went on executing at a stale position in the new program and
  printed `Syntax error in 49924`; the CF-3300 returns to a clean `Ok`.
- **A missing file printed `load error` and the program ran on** (fixed
  2026-08-20, D-LOADERR-FIX); both references raise `File not found` and stop.
  The name became a string expression the next day (D-FNEXPR2).
- **A tape `LOAD "CAS:x",R` printed `Illegal function call in 3346` after the
  loaded program's own output** (fixed 2026-08-07, D-CASTAIL):
  [castail-msx1-characterization.md](../castail-msx1-characterization.md).

## Where it lives

- Main ROM: `do_load` and `pcr_load` (the `,R` tail) in
  [basic/cload.asm](../../basic/cload.asm) and
  [basic/bload.asm](../../basic/bload.asm). A disk load is handed to the disk
  ROM; an ASCII file goes through `ascii_load`, which tokenises each line as
  if it were typed; the tape goes through `do_tape_prog` and
  `cas_ascii_load`.
- Disk ROM: `hk_dpload` in [disk/kernel.asm](../../disk/kernel.asm) mounts the
  disk, finds the file and reads it — the same split as on the CF-3300, whose
  whole sector loop runs on the disk ROM's side.
- The tape search: [basic/casmatch-body.inc](../../basic/casmatch-body.inc).

## Tests that cover it

- `make kwsweep` — plain `LOAD` (read back with `LLIST`), `LOAD ...,R`, and
  the error rows.
- `make loadtail-acceptance` — the option errors, on disk and on cassette.
- `make diskascii-acceptance` — `LOAD` of an ASCII file, against the CF-3300.
- `make dskmsg-acceptance` — `File not found` and the other disk messages.
- `make castail-acceptance`, `make cas-ascii-acceptance`,
  `make castype-acceptance`, `make casbin-acceptance` and
  `make casbrk-acceptance` — the tape forms.
- `make nodiskverbs-acceptance` — the diskless machine.
- `make kwram` — the RAM-usage comparison.
