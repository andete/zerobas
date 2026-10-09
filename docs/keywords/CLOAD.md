<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no run='CLOAD "ZR"' answers=LIST verify=no reason="needs a cassette" -->

# `CLOAD` — load a BASIC program from cassette

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error not yet proven. No known
> divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`CLOAD "name"` searches the cassette for a BASIC program saved with
[`CSAVE`](CSAVE.md) under that name and makes it the program in memory,
replacing the old one. Bare `CLOAD` takes the next such program on the tape.
The reference is the Philips VG-8020, a cassette-only MSX; where a tape row
was also run on the National CF-3300, it agreed. zerobas finds, skips and
loads the same files, and prints the same search messages.

## Syntax

```
CLOAD [<name>]
CLOAD? [<name>]
```

The name is a string expression (`CLOAD A$` works). `CLOAD?` compares the
tape with the program in memory instead of loading it.

## Details

- **The search prints what it sees.** Every program passed over prints
  `Skip :` and its name, and the one taken prints `Found:` and its name, the
  same rows on both machines.
- **Only tokenised programs count.** `CLOAD` looks for files written by
  `CSAVE`; an ASCII program (written by `SAVE "CAS:..."`) or a binary file
  (written by `BSAVE`) is stepped over silently, even under the same name — no
  `Skip :` row is printed for it.
- **A missing program is not an error.** The machine keeps searching the tape
  for as long as it plays; the only way out is Ctrl-STOP.
- **Ctrl-STOP during the search** is `Device I/O error` (19), which an
  `ON ERROR` handler can trap.
- **Run from a program, `CLOAD` stops it**: after the load the machine returns
  to `Ok`, and the rest of the old program does not run. A successful `CLOAD?`
  also ends the line.
- **Two programs on one tape both load**, by name or with two bare `CLOAD`s in
  a row.

### Errors

| situation | error |
|---|---|
| a number instead of a name (`CLOAD 5`) | 13 `Type mismatch` |
| Ctrl-STOP during the search | 19 `Device I/O error` |

`CLOAD`'s full error set has never been enumerated on the reference, because
every other `CLOAD` form waits for the tape; that is why **every error** is not
yet ticked.

## Example

A tape holding two programs saved with `CSAVE`: `ZQ` (`10 PRINT"[Z9]"`) and
then `ZR` (`10 PRINT"[Z8]"`). Typed with the tape rewound:

```
CLOAD "ZR"
Skip :ZQ
Found:ZR
LIST
10 PRINT"[Z8]"
```

This example needs a cassette, so it is not run by the example checker. The
same search — `CLOAD"ZR"` reading `Skip :ZQ` and `Found:ZR`, and bare `CLOAD`
reading `Found:ZQ` — is a row of `make kwsweep`, run against the VG-8020 with
that two-program tape.

## Differences from the reference

None known.

**Every error** and **RAM usage** are not yet proven.

## What we found, and how

- **The tape search did not filter by file type** (fixed 2026-10-08,
  D-CASTYPE). On a tape holding an ASCII `X` and then a tokenised `X`,
  `CLOAD "X"` read the ASCII one here and the tokenised one on the VG-8020,
  which steps over the other type as it steps over a wrong name
  ([`castype_after.out`](../../scratchpad/castype_after.out)). A binary file
  ahead of the program stopped the search with an error (D-CASBIN, the same
  day).
- **Ctrl-STOP during the search printed `load error` and the program ran on**
  (fixed 2026-10-08, D-CASBRK). The VG-8020 raises 19, and a handler sees it.
- **A second program on a real tape could not be loaded** (fixed 2026-09-28,
  D-CASRELOCK). After skipping or loading a program, the tape reader tried to
  lock onto the seven zero bytes a CSAVE writes after it, and read
  `load error`. An earlier report of this (D-CLOADSKIP, 2026-09-23) had been
  withdrawn on the strength of a test tape that no real machine writes.
- **`CLOAD` in a program kept running the program it had just replaced**
  (fixed 2026-09-28, D-CLOADPROG): `Syntax error in 3346`, a line number read
  out of the new program, where both references stop at `Ok`.
- **`CLOAD 5` printed `load error`** (fixed 2026-09-05, D-CSAVEEXPR); both
  references say `Type mismatch`, and the name became a string expression.
- **zerobas printed no search messages** (fixed 2026-08-07, D-CASSEARCH).
  Both references print `Found:` and `Skip :` rows for every verb that
  searches the tape: [cassearch-msx1-characterization.md](../cassearch-msx1-characterization.md).

## Where it lives

- `do_cload` in [basic/cload.asm](../../basic/cload.asm) takes the name (or
  none) and the `?`, marks the search as "tokenised only", and calls
  `do_tape_prog`, the tape loader `LOAD "CAS:"` and `RUN "CAS:"` share;
  `cas_open_match` runs the search.
- The name match, the type filter and the `Found:` / `Skip :` rows:
  [basic/casmatch-body.inc](../../basic/casmatch-body.inc), a sub-ROM tenant;
  skipping a file's data is `cas_skip_data` there.
- The tape signal itself: [tape/tape.asm](../../tape/tape.asm).

## Related concepts

- [The cassette](../concepts/cassette.md) — files on tape, and how BASIC finds them

## Tests that cover it

- `make kwsweep` — the named form (`Skip :ZQ` then `Found:ZR`), the bare form,
  and `CLOAD 5`, against the VG-8020 with a prepared tape.
- `make castail-acceptance` — the search rows, two programs on one tape, and
  `CLOAD` from a running program, on the VG-8020, the CF-3300 and zerobas.
- `make castype-acceptance` and `make casbin-acceptance` — the search by file
  type.
- `make casbrk-acceptance` — Ctrl-STOP during the search.
- `make kwram` — the RAM-usage comparison.
