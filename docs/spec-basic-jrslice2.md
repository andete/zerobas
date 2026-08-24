<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-JRSLICE2 — the jp→jr remainder, landed via an address→source mapper

Status: **✅ SHIPPED. +67 B main page 1 (53 → 120), +35 B low region (10 → 45)**,
on `501bc26`. Completes [D-JRSLICE](spec-basic-jrslice.md): that slice banked the
51 sites locatable by unique target label; this one lands the 102 that needed
address precision.

`basic-reloc.rom` `f213a97d → d10033de`, merged `f9eeae8f → 4373ab53`,
`sub.rom` `490ffc49 → dd8f417b` (this pass touched shared/both-side files, so
unlike D-JRSLICE the sub image moved too — see §3).

---

## 1. Why a mapper was needed

D-JRSLICE's remainder was 104 convertible sites (69 page-1 + 35 low) whose target
is a SHARED TAIL — 31 source lines read `jp raise_error`, and only 3 are in `jr`
range. By target-label alone they cannot be told apart, and pasmo 0.5.5 emits no
listing to bridge ROM address ↔ source line.

## 2. The mapper — region + ordinal, and safety on the assembler

`scratchpad/jr_mapper.py`. Both sides are keyed by **(region, mnemonic, target,
ordinal)**:

* region = the nearest preceding label that exists as a `^name:` in source (so
  boundaries are identical on both sides; `equ` aliases are not boundaries);
* ordinal = the index of this (mnemonic, target) pair within its region.

The ROM side comes from a full linear decode; the source side from a per-file
scan resetting the ordinal at each code label. A convertible ROM site joins to a
source line iff the key matches **uniquely**. Result: **all 104 sites resolved,
0 no-match, 0 ambiguous.**

🎯 **The mapper does not carry the safety — the assembler does.** `jp`→`jr` is
correct for ANY in-range site, and pasmo enforces range across BOTH builds. So a
mis-map that picks an in-range line is still correct, and one that picks an
out-of-range line fails the build by name and is reverted. The mapper only has to
propose in-range candidates; the build disposes. This is why a region+ordinal
heuristic — not a proof — is sufficient.

## 3. What landed: 102 of 104, and the shared body that bit twice

15 files, exact `jp`→`jr` swaps. **`basic/pdfcb-body.inc`'s 2 sites were reverted
— the SAME line 53 that D-JRSLICE already hit.** It is a body included
byte-identically into main and a sub-ROM tenant; the `jr` is in range in main
(what the mapper measured) and out of range in sub. The assembler caught it in
the repack (both images), exactly as the safety argument promises.

🔴 **STANDING EXCLUSION: `pdfcb-body.inc` (and any shared `*-body.inc`) is
off-limits to a main-address-only mapper.** It has now failed twice for one
reason — a shared body has two addresses and this mapper measures one. A future
pass wanting those 2 B must range-check the SUB build too.

⚠️ **`sub.rom` moved this time** (`490ffc49 → dd8f417b`) because conversions
landed in files compiled into both images (`str-engine.asm`, `float*.asm`,
`arrays.asm`, …). That makes `subrom-abi-check` / `subrom-closure-check` the
load-bearing gates, not any functional one: both images re-addressed, and the
sub calls into main by address while main calls into sub by fixed tenant index.
Both green — the ABI regenerates from the main `.sym`, the 24-tenant closure is
intact, no main-page-1 escape.

## 4. The seam, now

Combined with D-JRSLICE, the `jp`→`jr` class has moved main page 1 from its
2 B starve to **120 B**, and the low region from 10 B to **45 B** — measured
`make basic-reloc`, 2026-08-24. The 2 `pdfcb-body.inc` bytes are the only
convertible page-1 sites left, held by the shared-body exclusion.
