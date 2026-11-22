<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# The interpreter entries — BASIC's helpers in the BIOS table

> **Status (2026-11-18):** the shared facts of the interpreter region's four BIOS calls (SYNCHR,
> CHRGTR, DCOMPR, GETYPR). Each call's state, and the differences its page names, are in the
> generated [BIOS index](../bios/index.md), never repeated here. Speed is deliberately left out of
> these docs until on-par speed is established.

## Summary

Four entries of the BIOS table are not about the hardware: they are the BASIC interpreter's own
small helpers, published so that an extension (a disk ROM, a cartridge adding `CALL` statements)
can parse BASIC text and look at values the way the interpreter does. Each has a one-byte form,
an `RST`:

| call | address | `RST` | does |
|---|---|---|---|
| [SYNCHR](../bios/SYNCHR.md) | $0008 | `RST 08h` | check the next character is the expected one, else Syntax error |
| [CHRGTR](../bios/CHRGTR.md) | $0010 | `RST 10h` | step to the next character of the text |
| [DCOMPR](../bios/DCOMPR.md) | $0020 | `RST 20h` | compare HL with DE, unsigned |
| [GETYPR](../bios/GETYPR.md) | $0028 | `RST 28h` | the type of the value in DAC |

DCOMPR and GETYPR agree with the reference in every measured case, and SYNCHR in its own; CHRGTR
differs in how it skips and in the numeric-constant tokens (below), and SYNCHR inherits that
where it goes on as CHRGTR.

## How it works

Every statement below carries its source:
- **[P]** the published interface, the MSX2 Technical Handbook (rated in
  [allowed-sources.md](../allowed-sources.md));
- **[M]** measured by this project (the per-call pages);
- **[A]** not yet established.

### The text pointer

SYNCHR and CHRGTR work on BASIC text, the tokenised form a program line is stored in
([program text](program-text.md)), with HL pointing into it [P]. CHRGTR returns the next
character in A, Z set at the end of a statement (00 or `:`) and the carry on a digit [P]. On the
reference it also skips a space, a TAB and an LF [M].

### Numeric constants in the text

A number in a program line is stored as a token ($0B–$1F) followed by its value. On the
reference, CHRGTR decodes such a token into work-area cells [M] ([CHRGTR](../bios/CHRGTR.md)):

| cell | holds |
|---|---|
| CONTXT ($F666) | the text address after the constant |
| CONSAV ($F668) | the token |
| CONTYP ($F669) | the type: 2 integer, 4 single, 8 double |
| CONLO ($F66A…) | the value |

HL then holds $46E6, not a text pointer, and the next CHRGTR from there returns the text after the
constant, so a caller stepping through the text treats the constant as one character [M].

### Value types

The interpreter keeps the current value in DAC and its type in **VALTYP** ($F663): 2 integer,
3 string, 4 single, 8 double [P]. GETYPR returns A = VALTYP − 3 with the flags telling the four
apart (S integer, Z string, carry single, no carry double) and changes nothing else [M].

### Errors

SYNCHR, on a mismatch, raises Syntax error and does not return: the error hook H.ERRO ($FFB1) is
called with E = 2 [M]. Error codes are on the [errors](errors.md) page.

### Where they run

The table's entries are in page 0 of the main ROM. On the VG-8020 the code continues into the
BASIC part of the ROM, in page 1. Called from a cartridge running in its own page 1, the
VG-8020's GETYPR returned a wrong, constant answer and then hung, where zerobas's ran every case
[M] ([GETYPR](../bios/GETYPR.md)). So the probes run from RAM, with page 1 switched to the main
ROM's slot ([slots](slots.md)). **[A]** Which of the two causes it is (page 1 not being the main
ROM, or the caller itself running in page 1); that case would separate them.

## Differences from the reference

Each call's differences are on its own page, never repeated here; the
[BIOS index](../bios/index.md) lists them per call. Two items cover CHRGTR (and SYNCHR where it
goes on as CHRGTR): **D-CHRGTRSKIP**, the characters it skips, and **D-CHRGTRTOK**, the
numeric-constant tokens.

## What we found, and how

Each call was measured by a probe that builds its input in RAM (a text, VALTYP, HL and DE), calls
the entry as its `RST`, and records the registers and work-area cells after it, over every value
of the input byte. The rules are checked against every case ([docs/spec-method.md](../spec-method.md)).

## How zerobas does it

The entries are in C-BIOS's table, in the main ROM's page 0, and lead into zerobas's own
interpreter ([ROM layout](rom-layout.md)); a difference a page finds becomes a TODO item, fixed
there and then pinned by the page's rules.

## Related pages

- [The BIOS](bios.md): what every BIOS call has in common.
- [Program text](program-text.md): the tokenised text CHRGTR steps through.
- [Numbers](numbers.md): the value types GETYPR tells apart.
- [Errors](errors.md): the codes SYNCHR's Syntax error belongs to.

## Tests that cover it

**`spec-live`** ([tools/spec_live.py](../../tools/spec_live.py), in every gate) re-runs every rule
of the four call pages on zerobas.
