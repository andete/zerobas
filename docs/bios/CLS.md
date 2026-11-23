<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `CLS` ($00C3) — clear the screen

> **Spec:** FINAL (2026-11-17), the core rule: the third review's pass was CLEAN (docs/spec-method.md §7).
> The open items below stay [A] and do not hold up the fixes. After two earlier test-writer reviews. Measured on the Philips VG-8020 by
> calling the call directly, the inputs written by the probe to several values. The page states POSIT
> ($00C6, place the cursor) too, as the two are measured together; [POSIT's page](POSIT.md) points
> here.

## Summary

`CLS` acts exactly when the Z flag is set (A and the carry do not matter).
- In SCREEN 0 / 1 it fills the whole name table with spaces, homes the cursor (without scrolling,
  also from the key line's row), resets LINTTB, and redraws the function-key line on row CRTCNT when
  CNSDFG is non-zero. The table is the one the mode's call set up: a TXTNAM changed afterwards is
  ignored.
- In SCREEN 2 it zeroes the pattern table and fills the colour table with BAKCLR as it is.
- In SCREEN 3 it fills the multicolour pattern table with BAKCLR in both nibbles.

`POSIT` places the cursor at column H, row L, whatever the Z flag. It CLAMPS a column of 0 or above
LINLEN to LINLEN. It clamps a row of 0 or above (CRTCNT + CNSDFG) mod 256 to that limit, which is
CRTCNT − 1 while the key line shows with the usual CNSDFG $FF. In SCREEN 2 and 3 it does nothing.

zerobas does all of it the same, apart from:
- the key line's row (D-INITEDGES);
- A / F on return (D-TEXTAF).

## The specification

Reference: the Philips VG-8020's main BIOS. Ours: the C-BIOS repack. The screen and its cells are on
[the screen editor page](../concepts/screen-editor.md); what the calls touch is on
[the shared-state map](shared-state.md).

**Re-runs (2026-11-18).** The rules read zerobas's side of each probe below re-run, unchanged, on the 2026-11-18 build: [`XCLS_fix4.out`](../../scratchpad/XCLS_fix4.out), [`XSCR_fix6.out`](../../scratchpad/XSCR_fix6.out), [`XSCR3_fix6.out`](../../scratchpad/XSCR3_fix6.out), [`XSCR4_fix6.out`](../../scratchpad/XSCR4_fix6.out), [`XSCR5_fix6.out`](../../scratchpad/XSCR5_fix6.out). The runs cited below are the ones the rules were written from; the reference's side is the same machine and setup.

**Evidence.** **[XC n]**: case `n` of the XCLS matrix, run 2,
[`scratchpad/XCLS_run2.out`](../../scratchpad/XCLS_run2.out). The case list, the setup and the record
are in `probes/bios/spec/xcls_cases.py`, which also generates `probes/bios/spec/xcls.asm` and decodes
the run.
- The matrix: CLS with Z set and clear in SCREEN 0 (widths 40, 37, 39), 1 (32, 29) and 2. The key
  line is on or off, CRTCNT 24 or 13, and there are two colour sets.
- POSIT with in-range, edge (0, LINLEN + 1, 255) and out-of-range H / L, under CRTCNT 24 and 13 and
  in SCREEN 2.
- **A separating setup:**
  - the screen is set up by INITXT / INIT32 / INIGRP, then LINL40 := LINL32 := 77;
  - FNKSTR holds "key0".."key9", and the colours are 11 / 6 / 13 or $3A / $C5 / $F9;
  - ALL of VRAM is filled with $5A garbage, LINTTB with $55, and the cursor is put at (7, 5);
  - the call goes through a RAM `JP`, with H / L and the Z flag set just before.

  Run 1 ([`XCLS_run1.out`](../../scratchpad/XCLS_run1.out)) is run 2's first 27 cases. In it,
  POSIT's row clamp to 24 could not be told from CRTCNT's 24, and the SCREEN 2 case's L equalled the
  garbage CSRY. Run 2 adds the cases that separate them.
- Each record ends in a sentinel byte, and a whole-VRAM sum checks that nothing else was written.
- **[XS n]**: case `n` of the XSCR supplement, run 2,
  [`scratchpad/XSCR_run2.out`](../../scratchpad/XSCR_run2.out), shared with [DSPFNK's page](DSPFNK.md). The cases, the
  setup and the record are in `probes/bios/spec/xscr_cases.py`. The expected outputs are computed per
  case by `probes/bios/spec/xscr_model.py`, from the case's inputs alone.

  XSCR followed this page's first review, which found inputs with ONE value and outputs read only
  as sums that alias. It gives the inputs several values:
  - two garbage sets, with an address-dependent name table that no write of a space or a label
    reproduces;
  - the cursor on and off the key line's row;
  - moved name tables, and several CNSDFG values and widths;
  - more label bytes, and A / F set independently on entry.

  It reads LINTTB's entries, and the SCREEN 2 / 3 tables byte for byte. Run 1
  ([`XSCR_run1.out`](../../scratchpad/XSCR_run1.out), its first 50 cases) kept LINTTB only as a sum.
  A first try at run 2 with a longer record crashed the VG-8020 (the capture reached its stack).

- **[XS3 n]**: case `n` of the XSCR3 supplement,
  [`scratchpad/XSCR3_run1.out`](../../scratchpad/XSCR3_run1.out); the cases are in
  `probes/bios/spec/xscr3_cases.py`, the model is the same. It answers the second reviews:
  - LINTTB's garbage address-dependent, so a scroll's shift shows;
  - FNKSB off, with the cursor on and off the key row;
  - ERAFNK at widths 37 / 32 and with CNSDFG 0;
  - CLS with the cursor on the key line's row;
  - POSIT with CNSDFG 2 / $80, and CRTCNT 13 with $FF;
  - TXTNAM / T32NAM changed AFTER INITXT / INIT32.

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/bios/spec/xcls_rules.py -- do not edit; `python3 tools/spec_rules.py probes/bios/spec/xcls_rules.py --write` -->

**13 rules; 13 hold on the reference. Of the 13150 recorded outputs (each case's cursor, cells, A, table entries ...): 13138 read by a rule's check, 12 declared NOT evidence (below), 0 unread.**

#### 1. CLS ($00C3): clear the screen

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-C-TEXT** CLS with the Z flag set, in SCREEN 0 / 1: the whole name table (960 / 768 cells) becomes spaces -- at any width, CRTCNT 13 included -- and nothing else in VRAM changes (the whole 16 KB's sum read). With CNSDFG non-zero the key line is redrawn on row CRTCNT as DSPFNK draws it (the first five labels; docs/bios/DSPFNK.md) and CNSDFG becomes 255. | 11 | ✓ | ✓ |
| **R-C-HOME** It homes the cursor (CSRX 1, CSRY 1) and sets LINTTB to 24, 23, …, 1 down the rows. | 11 | ✓ | ✓ |
| **R-C-ZCLEAR** CLS with the Z flag CLEAR does nothing at all: VRAM, the cursor, LINTTB and CNSDFG as found, in every mode. | 4 | ✓ | ✓ |
| **R-C-GRP** CLS with the Z flag set in SCREEN 2: the pattern table ($0000, 6 KB) becomes 0 and the colour table ($2000, 6 KB) BAKCLR AS IT IS (FORCLR is not used): read here only as sums, which for 2048 equal bytes keep the byte mod 32 -- XSCR's byte reads pin it ($16, $C5: R-C-SEVERAL); the name and sprite tables are left as found, and so are the cursor, LINTTB and CNSDFG. | 3 | ✓ | ✓ |
| **R-C-GATE** CLS acts exactly when the Z flag is set: A = 0 with Z set and A = 1 with Z and carry set clear the screen; A = 1 and A = 0 with Z clear do nothing -- A and the carry do not matter. | 5 | ✓ | ✓ |
| **R-C-SEVERAL** And with the inputs at several values (XSCR): CNSDFG 2 / $80 / $FF all redraw the key line (CNSDFG becomes 255); a second garbage set; H / L 3 / 9 ignored; the name table moved (TXTNAM $1000, T32NAM $1C00 -- cleared there); CRTCNT 13 in SCREEN 1; 15-character labels cut to slot − 1; in SCREEN 2 the colour table's BYTES read BAKCLR as it is ($16, $C5) and the pattern table's 0 -- every cell, the cursor, LINTTB and the whole VRAM's sum as the model says. With the cursor ON the key line's row (24, or 13 at CRTCNT 13) CLS does not scroll: it clears, homes, and draws the line. With TXTNAM / T32NAM changed AFTER INITXT / INIT32 it clears the table the mode's call set up, not the one TXTNAM now names. | 15 | ✓ | ✓ |
| **R-C-MLT** CLS in SCREEN 3 (Z set): the multicolour pattern table ($0000, 1.5 KB) becomes $66 -- BAKCLR 6 in both nibbles, one BAKCLR measured -- and nothing else changes: the name table, the cursor, LINTTB. | 1 | ✓ | ✓ |

#### 2. POSIT ($00C6): place the cursor

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-P-CLAMP** POSIT in SCREEN 0 / 1: CSRX := H and CSRY := L, each CLAMPED -- a column of 0 or above LINLEN becomes LINLEN (0 / 41 / 255 at width 40 give 40; 38 at 37 gives 37; 31 / 30 at 29 give 29), a row of 0 or above the LIMIT (CRTCNT + CNSDFG) mod 256 becomes that limit: CRTCNT with the key line off (0 / 14 / 20 give 13 with CRTCNT 13; 25 / 30 / 255 give 24 with 24), CRTCNT − 1 with CNSDFG's usual $FF (25 / 24 / 0 give 23: the key line's row is not the cursor's), and -- the same sum -- 25 with CNSDFG 1, 26 with 2, 152 with $80 (L 100 stays, 153 gives 152), 12 at CRTCNT 13 with $FF. It ignores the Z flag (Z clear: still clamped). | 33 | ✓ | ✓ |
| **R-P-GRP** POSIT in SCREEN 2 and 3 does nothing: the cursor stays as found -- (7, 5) and (11, 3) -- for H / L 3 / 9 and 0 / 0. | 5 | ✓ | ✓ |
| **R-P-ONLY** POSIT changes nothing else: VRAM, LINTTB and CNSDFG as found. | 21 | ✓ | ✓ |
| **R-P-SEVERAL** POSIT changes nothing else, with the inputs at several values: VRAM (the whole sum), LINTTB, CNSDFG, CRTCNT, LINL40 / LINL32 as found. | 17 | ✓ | ✓ |

#### 3. Both

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CP-STATE** Neither changes CRTCNT, LINLEN or SCRMOD. | 39 | ✓ | ✓ |
| **R-CP-AF** A / F on return (not published): the reference's values -- CLS 00 / 54 in SCREEN 0 / 1 without the key line, 00 / 44 with it and in SCREEN 2, 66 / 24 in SCREEN 3, A / F unchanged when Z was clear; POSIT 24 / 30 in SCREEN 0 / 1, 22 / 30 in SCREEN 2 / 3, 48 / 18 with A / F 00 / 00 on entry. | 38 | ✓ | ✗ 35: XS 27, XS 29, XS 31, XS 32, XS 33, XS 34 … (+29) |

Declared NOT evidence (7 cases: XC 12, XC 13, XC 14, XC 25 … (+3)): linlen — SCREEN 2 cases: the setup does not set LINLEN there (INIGRP does not), so its value is the previous case's

Declared NOT evidence (5 cases: XS 36, XS 37, XS 43, XS 47 … (+1)): linlen — SCREEN 2 / 3 cases: the setup does not set LINLEN there (INIGRP / INIMLT do not), so its value is the previous case's

<!-- RULES END -->

## Differences from the reference

| TODO item | rules zerobas fails |
|---|---|
| **D-TEXTAF** (A / F on return) | R-CP-AF |

## On later generations (MSX2, MSX2+)

Measured 2026-11-23 on the HB-F900 and NMS 8250 (MSX2) and the FS-A1WSX (MSX2+): this page's probes through `probes/bios/biosl_run.py --row msx2all` -- [scratchpad/AE_m1on2/xcls.out](../../scratchpad/AE_m1on2/xcls.out), [scratchpad/AE_m1on2/xscr.out](../../scratchpad/AE_m1on2/xscr.out), [scratchpad/AE_m1on2/xscr3.out](../../scratchpad/AE_m1on2/xscr3.out), [scratchpad/AE_m1on2/xscr4.out](../../scratchpad/AE_m1on2/xscr4.out), [scratchpad/AE_m1on2/xscr5.out](../../scratchpad/AE_m1on2/xscr5.out); triage: [scratchpad/m1on2-triage-vdp.md](../../scratchpad/m1on2-triage-vdp.md).

| rule | MSX2 (HB-F900, NMS 8250) | MSX2+ (FS-A1WSX) |
|---|---|---|
| **R-C-SEVERAL** | in SCREEN 2 the colour table's bytes read BAKCLR AND 15 ($16 gives 06, $C5 05) [M] | the same [M] |
| **R-CP-AF** | CLS that draws the key line returns A = the last label character drawn ($41, $43, $59 measured), not 00; F $42 in SCREEN 2 and 3 [M] | the same [M] |
| every other rule | holds [M] | holds [M] |

## Open (not measured)

- **[A]** CLS with the cursor display on (CSRSW); POSIT with it on (is the cursor redrawn?).
- **[A]** CLS in SCREEN 3 with another BAKCLR (only 6 measured: "both nibbles" vs a constant).
- **[A]** CLS in SCREEN 2 / 3 with moved GRPCGP / GRPCOL / MLTCGP cells.
- **[A]** The key line's labels with SHIFT held (needs a keyed probe).
- **[A]** The registers other than A / F on return.
- **[A]** CLS's gate with S / P/V / H / N set on entry (only $00 / $40 / $41 and `cp 1`'s flags
  measured); A other than 0 / 1.
- **[A]** POSIT in range with Z clear; POSIT's limit above 24 being accepted for every row up to it
  (152 measured at one row).
- **[A]** SCREEN 3 with Z clear or CNSDFG on; CLS's key line on a moved table or with
  control-character labels.
- **[A]** VRAM byte by byte outside the rows read: the rest is checked by sums (XCLS: uniform $5A).

## Tests that cover it

**`spec-live`** ([tools/spec_live.py](../../tools/spec_live.py), in every gate): every rule above, run live on zerobas against these cases' measured reference values. It fails if a rule fails that *Differences from the reference* does not name, or a named one holds ([docs/spec-method.md](../spec-method.md) §8).

Also `biosl-acceptance` rung b1text (L3 in tools/bios_levels.py) and the suites `tools/entry_table.py --bios` lists. Which of those older rows the matrix makes redundant is the audit's next step: a row is retired only with mutation evidence.

