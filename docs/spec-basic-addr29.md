<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-ADDR29 — the 29 published work-area variables, at their published addresses

**Status:** SPEC, 2026-09-24. **Tier:** 4 (RAM usage), goal (b) *same addresses*.

## 0. The ruling

D-RAMFOOT (`scratchpad/ramfoot_probe.py`, `scratchpad/ramfoot_run.out`) ran 16
one-line operations on the VG-8020 and on zerobas and recorded every address
each one writes. The naming pass (`scratchpad/ramfoot_names.py`,
`scratchpad/ramfoot_names.out`) found **29 published work-area variables (186
bytes)** that the VG-8020 writes for those operations and zerobas never
touches. Asked which of them zerobas should maintain at the published address,
Joost ruled ***"All 29"***, 2026-09-24. He was offered "pointers only"
(recommended), "+ screen state", "all" and "none for now".

This spec turns that ruling into slices. **It decides nothing that is his:**
where a variable cannot be matched for free, the choice and its price are
listed in §4 and go back to him.

## 1. What "maintain at the published address" can mean

A variable is **matched** when a program that `PEEK`s the published address
during or after the operation reads what the reference would read there.
There are three routes, in rising cost:

| route | how | ROM cost | when it applies |
|---|---|---|---|
| **E — equate** | move zerobas's own cell to the published address | 0 B | zerobas already keeps the SAME variable, in the SAME format and width |
| **W — write** | add stores on the paths that change it | bytes per site | zerobas computes the value but keeps no cell for it, or keeps it in another format |
| **N — new state** | zerobas has no such variable at all | bytes, and the reference's semantics to reproduce | the reference's own algorithm internals |

Route E also FREES zerobas's old cell, and the freed bytes count toward goal (a)
(free memory).

## 2. The group constraint (why some cells cannot move alone)

D-REHOME (2026-08-01, `docs/sysvar-rehoming-decisions.md` §REJECT-GROUP)
rejected re-homing `ARYTAB` and `FRETOP` on their own. Its reason is still
right, and the ruling does not remove it:

* A consumer computes array space as `STREND − ARYTAB`. Publishing a live
  `ARYTAB` next to an unmaintained `STREND` gives a large negative length: a
  confident wrong answer, where today the program gets an obviously dead `0 − 0`.
* `FRETOP` is only meaningful relative to `MEMSIZ`/`STKTOP`.

So the pointer chain moves **as one slice**: `VARTAB` ($F6C2), `ARYTAB`
($F6C4), `STREND` ($F6C6), and the string pair `FRETOP`/`MEMSIZ`. `VARTAB` is
not among the 29, because none of the 16 operations writes it, but the chain
needs it.

## 3. The table

The published address and width come from C-BIOS's `systemvars.asm`, with the
width derived from the next symbol, as sysvarsweep does. "zb at target" was
checked mechanically against `docs/ram-map.md`: **no target collides with a
zerobas cell.** The only two hits are `CNSDFG` and `ATRBYT`, which are already
declared at the published address.

| variable | addr | width | written by (of 16) | zerobas today | route | note |
|---|---|---|---|---|---|---|
| `CNSDFG` | `$F3DE` | 1 | CLS | **at address** (`basic/screen.asm` writes it on `KEY ON/OFF`) | W | CLS does not re-write it here |
| `ATRBYT` | `$F3F2` | 1 | COLOR | **at address** (graphics writes it) | W | `COLOR` does not set it here |
| `PRTFLG` | `$F416` | 1 | PRINT | `PRDEST` `$E0CB` (0 screen / 1 file, + `PRDEV`) | W | different encoding: a new byte, not a move |
| `TTYPOS` | `$F661` | 1 | LOCATE | — (zerobas reads `CSRX`) | N/W | the reference's print column |
| `DIMFLG` | `$F662` | 1 | 12 ops | `ARY_OP` `$E028` (0 resolve / 1 DIM / 2 ERASE) | W | encodings differ |
| `TEMPPT` | `$F678` | 2 | strings | `TEMPTOP` `$E238` | ✋ | the pool behind it is 96 B, `TEMPST` holds 30 (§4) |
| `TEMPST` | `$F67A` | 30 | strings | `TEMPPOOL` `$E381` (32 × 3 = 96 B) | ✋ | does not fit (§4) |
| `DSCTMP` | `$F698` | 3 | strings | — | N | |
| `FRETOP` | `$F69B` | 2 | LEFT$, STR$ | `FRETOP` `$E268` (heap low boundary, grows down) | E (chain) | §2 |
| `ENDFOR` | `$F6A1` | 2 | FOR | — (FOR frame in the pool) | N | |
| `SUBFLG` | `$F6A5` | 1 | 11 ops | — | N | |
| `TEMP` | `$F6A7` | 2 | 11 ops | — | N | |
| `ARYTAB` | `$F6C4` | 2 | 11 ops | `ARYTAB` `$E1C0` (same variable, byte-identical per D-REHOME) | E (chain) | §2 |
| `STREND` | `$F6C6` | 2 | 12 ops | `ARYEND` (implied by `CTLLIM = ARYEND+2`) | E/W (chain) | §2 |
| `PRMFLG` | `$F7B4` | 1 | 11 ops | — | N | |
| `ARYTA2` | `$F7B5` | 2 | 11 ops | — | N | |
| `FBUFFR` | `$F7C5` | 43 | PRINT, SIN, STR$ | `FOUTBUF` `$F024` (24 B formatter output) | E? | fits; is the CONTENT the same? |
| `DECCNT` | `$F7F4` | 2 | SIN | — | N | |
| `DAC` | `$F7F6` | 16 | 8 ops | `FAC` `$F01C` (8 B "value bytes as tokenised") | ✋ | floats match; integers are at `FAC+0` here and at `DAC+2` there (§4) |
| `HOLD8` | `$F806` | 48 | RND, SIN | — (`MULPROD` etc. — another algorithm) | N | |
| `HOLD2` | `$F836` | 8 | RND, SIN | — | N | |
| `HOLD` | `$F83E` | 9 | RND, SIN | — | N | |
| `ARG` | `$F847` | 16 | FOR, RND, SIN | `ARGA` `$F06A` (18 B UNPACKED record) | ✋ | format differs (§4) |
| `RNDX` | `$F857` | 8 | RND | `RND_SEED` `$F142` (7 B packed BCD) | ✋ | 7 vs 8 B (§4) |
| `PTRFIL` | `$F864` | 2 | PRINT | — | N | |
| `FNKSWI` | `$FBCD` | 1 | CLS | — (BIOS) | N | C-BIOS-side |
| `LINWRK` | `$FC18` | 40 | CLS | — (BIOS) | N | C-BIOS-side |
| `GRPHED` | `$FCA6` | 1 | CLS, LOCATE | — (BIOS CHPUT) | N | C-BIOS-side |
| `ESCCNT` | `$FCA7` | 1 | LOCATE | — (BIOS CHPUT) | N | the reference's LOCATE goes through CHPUT's ESC sequence |

**Tally: 1 plain E candidate (`FBUFFR`), 1 chain of 3–4 E/W moves, 5 ✋ choices,
4 W, and 16 N.** N and W cost ROM, and main has 13 B.

## 4. The choices that are Joost's

1. **`DAC` integer layout.** An equate move of `FAC` to `$F7F6` makes floats
   read right and integers wrong: zerobas keeps an integer at `FAC+0`, the
   reference at `DAC+2`. Either (a) move the equate and accept that integers
   read wrong, (b) change zerobas's integer layout on every integer path, which
   costs ROM on every site, or (c) leave `DAC` alone. **This also touches the USR
   convention:** zerobas passes a USR argument in `HL` and leaves DAC untouched
   (`basic/usr.asm:19`), a deliberate divergence D-REHOME recorded.
2. **`TEMPST` capacity.** The reference holds 10 temporary descriptors in 30 B.
   zerobas's pool holds 32 in 96 B and cannot sit at `$F67A` without overrunning
   `DSCTMP`/`FRETOP`. Either shrink the pool to 10 (a behaviour change at depth:
   the reference errors where zerobas does not), or publish only `TEMPPT` and the
   first 10 descriptors.
3. **`ARG`, `RNDX` formats.** zerobas's operand record is unpacked (18 B) and its
   RND seed is 7 B. Matching either means converting at every use (W) or
   reproducing the reference's layout (N).
4. **The N set (16 variables)** is the reference's own algorithm state: flags,
   scratch and the BIOS's CHPUT/CLS work cells. Writing them is mimicry at a ROM
   price, and the ruling says to do it. The **order** is what needs deciding,
   because the budget is 13 B and every N slice needs a carve first.

### 4.1 Ruled by Joost, 2026-09-24 — all four as recommended

| choice | ruling |
|---|---|
| `DAC` | **full**: `FAC` moves to `$F7F6` AND integers move to `DAC+2` on every integer path; `USR` then finds its argument in `DAC` as MSX machine code expects (the `HL`-only convention of `basic/usr.asm` is superseded) |
| `TEMPST` | **shrink the pool to 10** at `$F67A` — a too-deep string expression now errors where the reference errors; 96 B of zerobas workspace freed |
| `ARG` / `RNDX` | **`RNDX` now, `ARG` later** with the N set |
| the N set | **observable first**: `TTYPOS` `PTRFIL` `ESCCNT` `GRPHED` `LINWRK` `FNKSWI`, then evaluator scratch |

## 5. Proposed slice order (cheapest, least contested first)

1. **S1 `FBUFFR`** — equate move of `FOUTBUF`, after confirming that the
   CONTENT after `PRINT`/`STR$` matches (a row that PEEKs `$F7C5..`). 0 ROM
   bytes if it does.
2. **S2 the pointer chain** — `VARTAB`/`ARYTAB`/`STREND` (+`FRETOP`/`MEMSIZ`),
   moved together, with a row that reads `STREND−ARYTAB` and `FRE`-style
   differences on both machines. Mostly equates; `VARTAB` and `STREND` may need
   writes.
3. **S3 `CNSDFG`/`ATRBYT` writes** on `CLS`/`COLOR` — a few bytes each.
4. **S4…** the ✋ items once ruled, then the N set in whatever order Joost gives.

Every slice needs:
* a D-RAMFOOT re-run: the cell must move from "reference only" to "shared";
* the sysvarsweep re-run, which scores documented cells;
* a FULL battery, because an equate move changes where every user of the cell
  writes.
