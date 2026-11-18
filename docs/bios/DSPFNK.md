<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# `DSPFNK` ($00CF) — show the function-key line

> **Spec:** FINAL (2026-11-18), the core rule: the fourth review's pass was CLEAN (docs/spec-method.md
> §7); the open items stay [A] and do not hold up the fixes. After three earlier test-writer reviews. Measured on the Philips VG-8020 by
> calling the call directly, the inputs written by the probe to several values. The page states ERAFNK
> ($00CC, erase the key line) and FNKSB ($00C9, show it if it is on) too: the three share the key line.
> [ERAFNK's](ERAFNK.md) and [FNKSB's](FNKSB.md) pages point here.

## Summary

`DSPFNK` turns the function-key line on (CNSDFG := 255) and draws the first five keys' labels on
row CRTCNT, inside the width's span. If the cursor is ON that row, it first scrolls the text rows up
by one, LINTTB with them, and moves the cursor up. `ERAFNK` turns it off (CNSDFG := 0), clears that
span, marks the row in LINTTB, and returns LINLEN in A. All three draw where the mode's call set the
name table up, not where TXTNAM points later. `FNKSB` draws the line when CNSDFG is non-zero and, when it is 0, changes nothing on the screen or in
the work-area cells read (CNSDFG, CRTCNT, the cursor, LINLEN, SCRMOD, LINL40 / LINL32, LINTTB); only
A / F.
In SCREEN 2 all three only set the flag.

zerobas does all of it the same, apart from:
- it shows function keys 6–10 instead of 1–5 (D-KEYLINESHIFT);
- it always draws on row 24 and sets CRTCNT to 24, and writes the whole row, margins included
  (D-INITEDGES);
- it does not scroll when the cursor is on the key line's row (D-DSPFNKSCROLL);
- it writes no LINTTB marks (D-LINTTBVAL);
- its A / F on return differ (D-TEXTAF).

## The specification

Reference: the Philips VG-8020's main BIOS. Ours: the C-BIOS repack. The key line's other writer is
INITXT / INIT32 ([INITXT.md](INITXT.md)); what the calls touch is on
[the shared-state map](shared-state.md).

**Re-runs (2026-11-18).** The rules read zerobas's side of each probe below re-run, unchanged, on the 2026-11-18 build: [`XKEY_fix2.out`](../../scratchpad/XKEY_fix2.out), [`XSCR_fix3.out`](../../scratchpad/XSCR_fix3.out), [`XSCR3_fix3.out`](../../scratchpad/XSCR3_fix3.out), [`XSCR4_fix3.out`](../../scratchpad/XSCR4_fix3.out), [`XSCR5_fix3.out`](../../scratchpad/XSCR5_fix3.out), and XFSW's run 2 [`XFSW_run2.out`](../../scratchpad/XFSW_run2.out). The runs cited below are the ones the rules were written from; the reference's side is the same machine and setup.

**Evidence.** **[XK n]**: case `n` of the XKEY matrix, run 1,
[`scratchpad/XKEY_run1.out`](../../scratchpad/XKEY_run1.out). The case list, the setup and the record
are in `probes/bios/spec/xkey_cases.py`, which also generates `probes/bios/spec/xkey.asm` and decodes
the run.
- The matrix: each call in SCREEN 0 (widths 40, 37, 39), SCREEN 1 (widths 32, 29) and SCREEN 2.
  CNSDFG is 0, 1 or $80 and CRTCNT 24 or 13. FNKSB also runs with FNKFLG 1 / $FF, and DSPFNK with odd
  labels.
- **A separating setup:**
  - the screen is set up by INITXT / INIT32 / INIGRP with the key line off, then LINL40 := LINL32 := 77,
    so the width used is LINLEN's;
  - the labels are written to FNKSTR ("key0".."key9", or the odd set);
  - the name table is filled with $5A garbage, and the cursor is put at (7, 5).
- Each record ends in a sentinel byte that the decoder requires.
- **[XS n]**: case `n` of the XSCR supplement, run 2,
  [`scratchpad/XSCR_run2.out`](../../scratchpad/XSCR_run2.out), shared with [CLS's page](CLS.md). The cases, the
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
- A / F on return are the one exception to "from the case's inputs alone": R-K-AF checks them against
  the reference's own per-case values (ERAFNK's F, BB / B3 / 9B at the measured widths 40 / 37 / 32 /
  29, is not modelled: it may copy LINLEN's bits 5 / 3, $93 OR (LINLEN AND $28), unseparated).
- **[XS5 n]**: the second confirming pass's XSCR5 ([`XSCR5_run2.out`](../../scratchpad/XSCR5_run2.out),
  `probes/bios/spec/xscr5_cases.py`). LINLEN set after the mode's call, separating "LINLEN as found"
  from "the width the mode's call was given". Also ERAFNK / FNKSB with TXTNAM changed late, DSPFNK
  with T32NAM changed late, and FNKSB in SCREEN 2 read whole.
- **[XS4 n]**: the confirming pass's XSCR4 ([`XSCR4_run1.out`](../../scratchpad/XSCR4_run1.out),
  `probes/bios/spec/xscr4_cases.py`). Four scroll cases that also read rows 12 and CRTCNT − 1: the
  scroll's middle rows were pinned only by sums.

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/bios/spec/xkey_rules.py -- do not edit; `python3 tools/spec_rules.py probes/bios/spec/xkey_rules.py --write` -->

**17 rules; 17 hold on the reference. Of the 16794 recorded outputs (each case's cursor, cells, A, table entries ...): 16785 read by a rule's check, 9 declared NOT evidence (below), 0 unread.**

#### 1. DSPFNK ($00CF): show the key line

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-K-DSP** DSPFNK sets CNSDFG to 255 (from 0, 1 or $80) and draws the key line on row CRTCNT (24 or 13; NOT row 24 when CRTCNT is 13). Within the width's span (LINLEN cells from the left margin (columns − width + 1) ÷ 2, the cells outside it left as found): spaces, then the FIRST five labels from column margin + k × slot, slot = (width + 1) ÷ 5 (8 at 40, 7 at 37, 6 at 32 / 29), each cut to slot − 1 cells. Every other cell of the name table is left as found. | 11 | ✓ | ✗ 6: XK 03, XK 04, XK 07, XK 08, XK 09, XK 11 |
| **R-K-LABELS** A label shows as its bytes, with a $01 prefix making the next character a graphic one (its code − $40 for $40..$5F: `$01 'A'` shows cell 01; R-K-LABELS2 for the rest), a control character below $20 (CR, ESC) as a space, DEL as itself, and the label cut to slot − 1 cells ('abcdefghijklmno' shows 'abcdefg' at width 40, 'abcde' at 32); an empty label leaves its slot blank. | 3 | ✓ | ✗ 3: XK 43, XK 44, XK 45 |
| **R-K-SCROLL** With the cursor ON the key line's row (CSRY = CRTCNT: 24, or 13), DSPFNK -- and FNKSB when it draws -- first scrolls the text rows up by one: row k takes row k + 1's cells for k up to CRTCNT − 2, row CRTCNT − 1 comes in BLANK (spaces; width 40 measured) and its LINTTB entry becomes 175; LINTTB's entries move up with their rows (XSCR3's address-dependent entries: 41 42 … 56 AF, entry 24 kept); the cursor moves up a row (CSRX kept). Then it draws the key line. With the cursor one row higher nothing scrolls. XSCR4 reads row 12 and row CRTCNT − 1 too: the middle rows moved and the blank row is blank, not only in the sums. | 9 | ✓ | ✗ 9: XS 00, XS 04, XS 54, XS3 05, XS3 06, XS4 00 … (+3) |
| **R-K-LABELS2** More label bytes: TAB and BS show as spaces (as CR and ESC); $80, $FF and DEL as themselves; a $01 at a label's end shows nothing; `$01 'a'` shows 'a' -- the graphic prefix acts only on $40..$5F ('A' gave 01); a 16-byte label with no terminating 0 is cut like any other (to slot − 1). | 3 | ✓ | ✗ 2: XS 20, XS 21 |
| **R-K-LINLEN** The width the key-line calls use is LINLEN AS FOUND, not the width the mode's call was given: with LINLEN set to 37 after a width-40 INITXT (29 after a width-32 INIT32), DSPFNK draws with margin 2 and slot 7 (2 and 6) and ERAFNK clears that span; and ERAFNK / FNKSB with TXTNAM changed late, DSPFNK with T32NAM changed late, all use the base the mode's call set up. The label cut is slot − 1 at every width: 15-letter labels show 6 cells at width 37, 7 at 39, 5 at 29 -- not width ÷ 5 − 1, not a fixed 7 / 5 (XSCR5 run 2). | 10 | ✓ | ✗ 8: XS5 00, XS5 01, XS5 02, XS5 03, XS5 04, XS5 08 … (+2) |
| **R-K-NOLT** DSPFNK -- and FNKSB when it draws -- without a scroll leave LINTTB untouched, the key line's own entry included (ERAFNK marks it: R-K-ERALT). | 25 | ✓ | ✓ |
| **R-K-FNKSWI** DSPFNK does NOT take the label set from FNKSWI ($FBCD): with no SHIFT held it shows keys 1-5 whatever FNKSWI held (0, 1, $5A, $FF) and leaves FNKSWI = 1. The set follows the keyboard; FNKSWI is written, not read. | 4 | ✓ | ✓ |

#### 2. ERAFNK ($00CC): erase the key line

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-K-ERA** ERAFNK sets CNSDFG to 0 and clears the key line's row (row CRTCNT) to spaces WITHIN the width's span only -- at width 37 / 39 / 29 the margin cells are left as found. Every other cell is left as found. | 11 | ✓ | ✗ 6: XK 16, XK 17, XK 20, XK 21, XK 22, XK 24 |
| **R-K-ERALT** ERAFNK also marks the key line's row in LINTTB: its entry becomes 175 (from $55, $AA and address-dependent garbage alike), whatever CNSDFG was (0 too), in SCREEN 0 and 1; in SCREEN 2 LINTTB is left alone; the other entries stay. | 13 | ✓ | ✗ 12: XS 02, XS 03, XS 07, XS 09, XS 19, XS 24 … (+6) |
| **R-K-ERA-A** ERAFNK returns A = LINLEN in SCREEN 0 / 1 (40 → 28, 37 → 25, 32 → 20, 29 → 1D) -- LINLEN as found: set to 37 / 29 after a width-40 / 32 INITXT / INIT32 it gives 25 / 1D (XSCR5). | 12 | ✓ | ✗ 11: XS 02, XS 03, XS 07, XS 09, XS 19, XS 24 … (+5) |

#### 3. FNKSB ($00C9): show it if it is on

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-K-SB-ON** FNKSB with CNSDFG non-zero (1, $80) is DSPFNK: CNSDFG 255 and the key line drawn. | 9 | ✓ | ✗ 4: XK 29, XK 30, XK 34, XK 37 |
| **R-K-SB-OFF** FNKSB with CNSDFG 0 does NOTHING: it does not erase; the name table keeps its garbage and CNSDFG stays 0. | 6 | ✓ | ✓ |
| **R-K-FNKFLG** FNKFLG (the ten function-key trap flags, 1 or $FF) makes no difference to FNKSB. | 4 | ✓ | ✓ |

#### 4. All three

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-K-GRP** In SCREEN 2 all three only set CNSDFG (DSPFNK 255, ERAFNK 0, FNKSB 255 if it was non-zero) and leave the name table as found. | 6 | ✓ | ✓ |
| **R-K-STATE** None of them moves the cursor (CSRX 7, CSRY 5 stay; the cursor ON the key line's row is the exception: R-K-SCROLL), or changes CRTCNT, LINLEN or SCRMOD. | 46 | ✓ | ✗ 5: XK 09, XK 11, XK 22, XK 24, XK 37 |
| **R-K-SEVERAL** Every rule above holds with the inputs at several values (XSCR): the name table moved (TXTNAM $1000, T32NAM $1C00 -- drawn there); CNSDFG $FF, 2 and $40 counted as on (FNKSB draws, CNSDFG becomes 255); FNKSB with CNSDFG 0 doing nothing, also with the cursor on the key line's row (no scroll); TXTNAM changed AFTER INITXT -- the line goes where the mode's call set the table up, not where TXTNAM now points; widths 33 / 38 / 30 (SCREEN 0) and 28 (SCREEN 1), which pin slot = (width + 1) ÷ 5 against (width + 2) ÷ 5; CRTCNT 13 in SCREEN 1 at width 29 and in SCREEN 0 at 37; FNKFLG $FF; a second garbage set (cursor, LINTTB, an address-dependent name table that no write of a space or a label reproduces) -- every cell, the cursor, LINTTB, LINL40 / LINL32 and the whole VRAM's sum as the model says. | 26 | ✓ | ✗ 11: XS 13, XS 14, XS 15, XS 16, XS 17, XS 18 … (+5) |
| **R-K-AF** The whole A / F on return (not published): the reference's values -- DSPFNK / FNKSB 00 / 44 when they draw (00 / 54 for FNKSB with CNSDFG 0), ERAFNK LINLEN with F BB / B3 / 9B, 02 / 42 in SCREEN 2. | 51 | ✓ | ✗ 48: XS 00, XS 01, XS 02, XS 03, XS 04, XS 05 … (+42) |

Declared NOT evidence (9 cases: XK 10, XK 12, XK 23, XK 25 … (+5)): linlen — SCREEN 2 cases: the setup does not set LINLEN there (INIGRP does not), so its value is the previous case's

<!-- RULES END -->

## Differences from the reference

| TODO item | rules zerobas fails |
|---|---|
| **D-KEYGRAPH** (a label's $01 graphic prefix: zerobas shows a space and the letter) | R-K-LABELS, R-K-LABELS2 |
| **D-INITEDGES** (the key line's row: zerobas row 24 and CRTCNT := 24; the whole row written, margins included) | R-K-DSP, R-K-SB-ON, R-K-ERA, R-K-STATE, R-K-SEVERAL, R-K-LINLEN |
| **D-DSPFNKSCROLL** (no scroll with the cursor on the key line's row) | R-K-SCROLL |
| **D-LINTTBVAL** (LINTTB: no $AF marks written) | R-K-SCROLL, R-K-ERALT, R-K-LINLEN |
| **D-TEXTAF** (A / F on return; ERAFNK's A is not LINLEN on zerobas) | R-K-AF, R-K-ERA-A |

## Open (not measured)

- **[A]** The key line with a key HELD (SHIFT: the VG-8020 should then show keys 6–10).
- **[A]** Widths below 28 or above 40, CRTCNT other than 13 and 24.
- **[A]** The scroll at a width below the screen's (is the blank row the whole row or the span?), and
  with the cursor below the key line's row.
- **[A]** The mode decided by SCRMOD or by the VDP's registers, when the two disagree.
- **[A]** FNKFLG with different flags per key (all ten were always set the same).
- **[A]** The graphic prefix's exact range (only $41 and $61 measured: $40, $5F, $60 and $3F open) and
  control codes other than $08 / $09 / $0D / $1B; a label's bytes after its terminator.
- **[A]** CNSDFG values with only bits 2–5 set ($04, $20); entry A / F for the key calls.
- **[A]** The scroll in SCREEN 1, and DSPFNK's scroll with CNSDFG already non-zero (FNKSB with
  CNSDFG 1 does scroll); SCREEN 2 with the cursor on row CRTCNT; "one row higher nothing scrolls" at
  CRTCNT 13; FNKSB / ERAFNK with T32NAM moved before the mode's call.
- **[A]** The label cut in cells vs bytes with several $01 prefixes in one label; a $01 before the
  terminator with non-zero bytes after it; FNKSB's scroll at CRTCNT 13; ERAFNK / FNKSB with T32NAM
  changed after INIT32; FNKSTR / FNKFLG after the calls (not read back).
- **[A]** Entry HL / BC / DE for the key calls; NAMBAS vs RG2SAV as "the base the mode's call set
  up" (they coincide in every late case).
- **[A]** A scroll's rows other than 1, 12, CRTCNT − 1, CRTCNT and 24 are read only through sums (at
  CRTCNT 24: rows 2–11 and 13–22); whether the moved
  rows' margins move at a width below the screen's; a 16-byte label's bound is not observable (the
  cut uses at most 14 bytes).
- **[A]** The registers and flags on return; the hooks H.DSPF / H.ERAF.
- **[A]** SCREEN 3.

## Tests that cover it

`biosl-acceptance` rung b1text (L3 in tools/bios_levels.py). The rules above join a gate through the
test audit ([docs/spec-method.md](../spec-method.md) §8) once this page is FINAL.
