<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no run='CSAVE "HI"' verify=no reason="needs a cassette" -->

# `CSAVE` — save the program to cassette

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`CSAVE "name"` writes the program in memory to the cassette in its tokenised
(compact, internal) form, under a name, so that [`CLOAD`](CLOAD.md) can find
it again. The reference is the Philips VG-8020. The bytes zerobas records are
the bytes the VG-8020 and the National CF-3300 record for the same program;
the VG-8020 loads a tape zerobas recorded, and zerobas loads the VG-8020's.

## Syntax

```
CSAVE <name>[,<speed>]
```

The name is a string expression and is required. The optional speed is 1 or
2 and chooses the recording speed.

## Details

- **The tape gets two blocks.** A header — ten bytes `&HD3`, which mark a
  tokenised BASIC program, and the name in a six-character field padded with
  blanks — then the program itself, its end marker, and seven zero bytes.
  Decoded off the recordings, that is byte for byte what all three machines
  write.
- **`CSAVE` is the tokenised save; `SAVE "CAS:name"` is the ASCII one.** On an
  MSX1 a `SAVE` to cassette always writes the program as text (file type
  `&HEA`), with or without `,A` — see [`SAVE`](SAVE.md). `CLOAD` reads only
  what `CSAVE` writes, and `LOAD "CAS:"` only what `SAVE "CAS:"` writes.
- **Nothing appears on the screen** while saving: there is no `Found:`-style
  message, which is why the test reads the tape itself rather than the screen.
- **The name is not optional.** `CSAVE` and `CSAVE:` are `Missing operand`;
  `CSAVE,2` is `Syntax error`.
- **An unterminated name is accepted**, as for any string: `CSAVE"P` saves
  under `P` on both references.

### Errors

| situation | error |
|---|---|
| a number instead of a name (`CSAVE 5`) | 13 `Type mismatch` |
| no name (`CSAVE`, `CSAVE:`) | 24 `Missing operand` |
| a speed but no name (`CSAVE,2`) | 2 `Syntax error` |
| a speed other than 1 or 2 (`CSAVE "X",3`) | 5 `Illegal function call` |
| anything after the speed (`CSAVE "X",1,2`) | 2 `Syntax error` |

The enumerated set the sweep checks is {13, 24}; the speed and tail errors
were measured later, on the VG-8020, and agree too.

## Example

With a blank tape in the recorder:

```
10 PRINT "HELLO"
CSAVE "HI"
```

The screen shows nothing but the next prompt; rewound, the tape can be read
back with `CLOAD "HI"`. This example
needs a cassette, so it is not run by the example checker; `make kwsweep`
covers `CSAVE` by recording onto a blank tape on the VG-8020 and on zerobas
and comparing the decoded recordings byte for byte.

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**. Not measured: what happens if
the recording is broken with Ctrl-STOP — a try with the current rig gave no
usable reading on either machine.

## What we found, and how

- **A tape zerobas wrote could not be loaded on a real MSX** (fixed
  2026-09-13, D-CASTAIL2). The VG-8020 hung searching it. Four slices went
  into the recording's timing before the bytes were compared: the program
  block ended without the seven zero bytes a real `CSAVE` writes, and the
  reference's `CLOAD` waited for them forever. Diffing our own recording
  against the VG-8020's showed it in one reading
  ([`kwdrain_casbytes.out`](../../scratchpad/kwdrain_casbytes.out)); now every
  writer/reader pair of the two machines loads.
- **A bad speed or tail printed `load error`** (fixed 2026-10-07,
  D-TAPETAIL); the VG-8020 raises 5 or 2, which a handler can trap.
- **`CSAVE` with no name saved anyway, under a blank name** (fixed
  2026-09-04, D-CSAVENAME) — a tape the references would never write, with
  no message. Both references refuse all three no-name forms.
- **The name had to be a literal** (fixed 2026-09-05, D-CSAVEEXPR):
  `CSAVE A$` printed `load error`, and `CSAVE 5` did too instead of
  `Type mismatch`.
- **The test once agreed on nothing.** The first `CSAVE` row read the screen,
  and both machines show nothing there, so it scored a match on an empty
  capture. The row now decodes the recording (D-KWTAPE3, 2026-09-13).

## Where it lives

- `do_csave` and `csav_speed` in [basic/save.asm](../../basic/save.asm): the
  name, the speed and the error faces; `tape_save_basic` hands the write to
  the sub-ROM's save tenant ([sub/save.asm](../../sub/save.asm)).
- The tape signal: [tape/tape.asm](../../tape/tape.asm).
- The format work: [cassave-msx1-characterization.md](../cassave-msx1-characterization.md).

## Tests that cover it

- `make kwsweep` — `CSAVE` onto a blank tape, the recording decoded and
  compared with the VG-8020's; the error rows for 13 and 24.
- `make cassave-acceptance` — what each cassette save writes (`CSAVE`
  tokenised, `SAVE "CAS:"` ASCII), on the VG-8020, the CF-3300 and zerobas.
- `make tapetail-acceptance` — the speed and tail errors.
- `make castail-acceptance` — a tape written the way `CSAVE` writes it, loaded
  back with `CLOAD`.
- `make kwram` — the RAM-usage comparison.
