<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `CONOUT` (BDOS $02) — write one character to the console

> **Spec:** DRAFT 4 (2026-11-17); §4.2 (the column rule) FINAL. Reviewed three times
> (docs/spec-method.md).

## Summary

An MSX-DOS program writes one character with `CONOUT` (C = $02, E = the character). The BDOS
passes it to the screen, expands a TAB into spaces itself, and keeps its own count of the column
($F237) for that purpose. zerobas writes the same characters and, since 2026-11-26, counts the
column by the same rule (D-CONCOL, fixed: before, a TAB after a control code landed in the wrong place).

## The specification

**§4.2, the count rule, is FINAL.** The third fresh review found
nothing against it: every cited value checked out, and no pair of rules it could not separate.
The rest stays a draft until its open items (§5) are measured.

Written from measurement on the reference before implementation, then reviewed three times by
fresh reviewers (an implementer and a test writer) who saw only these documents and their
evidence. Findings were answered by MEASURING, not arguing. Round 3 is a full matrix: every byte
value through every output path, from a state where the count and the screen cursor disagree.

What the screen does with a byte — cursor movement, escapes, the graphic prefix, what lands in
VRAM — is the BIOS's CHPUT contract, specified in
[CHPUT](../bios/CHPUT.md). This document covers what the BDOS
adds: TAB expansion, the logical column, and the registers.

Reference: the Panasonic CF-3300 under MSX-DOS 1. Ours: zerobas's disk ROM on the C-BIOS repack.
TODO item **D-CONCOL** (§4): ✅ fixed 2026-11-26 -- BDOSXL is a 0-byte diff against the CF-3300 (scratchpad/AE_concol4.out).

**Evidence tags.**
- **[XM n]**: case `n` of the BDOSXM matrix, [`scratchpad/XM_table.out`](../../scratchpad/XM_table.out)
  (case = mode × 256 + v; extras X0–X6 are cases 1280–1286; read its header for the setup and
  the two skipped cases). Its program is `probes/disk/bdosxm.asm`; the raw captures are
  [`scratchpad/XM_stock.out`](../../scratchpad/XM_stock.out) and
  [`scratchpad/XM_ours.out`](../../scratchpad/XM_ours.out). Each case records the count, CSRX,
  CSRY and A, read at the END of the case's last call.
- **[L n]**: row `n` of the BDOSXL table, [`scratchpad/XL_table.out`](../../scratchpad/XL_table.out).
  Its header lists the rows whose CSRX is contaminated by an unfinished escape.
- **[X9]**: BDOSX9 record 6, CONOUT `'*'`. On the CF-3300 alone:
  [`scratchpad/XL_bx9_stock.out`](../../scratchpad/XL_bx9_stock.out). The record is the 8 bytes from
  memory offset +48: the function number, then A, B, C, D, E, H, L **after** the call (not F; the
  register dump at that file's top is the program's state at its end). Compared on BOTH machines
  in [`scratchpad/bdosx9_run6.out`](../../scratchpad/bdosx9_run6.out): 0 of the 280 captured bytes
  differ.
- **[A]**: assumed, NOT measured.

**Units.**
- The **count** ($F237) is 0-based.
- **CSRX** / **CSRY** are the BIOS's 1-based cursor cells ($F3DD / $F3DC).

Clean room: registers, RAM cells and the screen cursor were read; nothing of the reference's code.

## 1. Interface

In: C = $02, E = the byte. Out:
- **A = E for every byte except TAB (9), where A = 0** [XM 0–255].
- The other registers, from one row only [X9]: E = `'*'` gives B = $A7, C = $02, D = $02,
  E = $2A, H = $A7, L = $2A. Their values before the call were not recorded, so which are preserved
  inputs is not known.

zerobas: A matches on all 256 [XM 0–255], and the [X9] record matches on both machines
(bdosx9_run6.out).

## 2. The screen side, as far as this entry decides it

- **A TAB never reaches CHPUT as 9.** The BDOS writes spaces (§4.2): the cursor moves by exactly
  the number of spaces the count rule gives, from the count and not from the cursor [XM 9: count
  3 → 8 and CSRX 21 → 26]. The BDOS does this even while CHPUT is in the middle of an `ESC Y`
  [L 123, 124].
- **[A]** Every other byte reaches CHPUT UNCHANGED. Only cursor movement consistent with that was
  observed; what CHPUT actually receives (an H.CHPU trace) and what lands in VRAM are CHPUT-spec
  measurements.
- For escapes, the graphic prefix, DEL and `ESC l` (the two measured CHPUT differences between
  the machines), see the CHPUT spec.

## 3. Console checks during output

**[A]** Not measured yet:
- whether CONOUT looks at the keyboard (Ctrl-S pause, Ctrl-C abort, the STOP key / Ctrl-STOP);
- whether it echoes to the printer when Ctrl-P is on;
- what happens to an ordinary key typed during output (kept for the next read, or lost).

## 4. The logical column ($F237)

### 4.1 What it is

One byte in the work area, separate from the screen cursor.
- **It is the cell itself, not a private copy.** A program's POKE between calls takes effect at
  the next call:
  - set to 5, a TAB moves the cursor 3 columns and leaves 8 [XM 1280];
  - set to 250, a TAB moves it 6 and leaves 0 [XM 1281];
  - set to 5, a printable leaves 6 [XM 1284].
- **[A]** Whether the cell is re-read between the spaces of one TAB, or between the bytes of one
  STROUT. Only the end of each call is read.
- **TAB counts from the cell, not from the screen cursor.** With the count at 3 and CSRX at 21, a
  TAB ends at count 8 and CSRX 26 [XM 9].
- **It is a plain 8-bit counter that wraps both ways:** −1 from 0 gives 255 [L 58, 118, 119],
  and +1 from 255 gives 0 [L 140].
- **It is not tied to `LINLEN`** (29 here) and is not reset by the screen's line wrap
  [L 61–66, 144].

### 4.2 The rule — FINAL

Each byte CONOUT writes changes the count by its own value. This is measured for every byte value
0–255 in three CHPUT states:
- idle [XM 0–255];
- right after a bare ESC [XM 768–1023];
- right after the graphic prefix 1 [XM 1024–1279].

Each starts from a desynced state (count 3, CSRX 21), so "unchanged" cannot be confused with
"follows the cursor". Inside an `ESC Y` or `ESC x` parameter it is measured for the sampled
bytes only: `#`, `*`, TAB and `5` [L 41–44, 40, 123, 124]. **[A]** beyond those.

| byte E | count after (end of the call) |
|---|---|
| 32–126, 128–255 | +1 |
| 8 (BS), 29 (cursor left), 127 (DEL) | −1, mod 256 |
| 11 (home), 12 (clear), 13 (CR) | 0 |
| 9 (TAB) | the next multiple of 8 above it (mod 256; at least +1), written as that many spaces |
| 0–7, 10, 14–28, 30, 31 | unchanged |

- **ESC (27) is "unchanged".** So `ESC Y r c` adds 3, and `ESC BS` subtracts 1 [L 41–44, 120;
  XM 776].
- **The −1 for BS, 29 and DEL is the byte's own rule, not the cursor's.** After an ESC, CHPUT takes
  each of them as the escape's parameter and the cursor stays at CSRX 21, yet the count still goes
  3 → 2 [XM 776, 797, 895].
- **[A]** Whether a TAB's spaces each step the cell (+1 per space) or the cell is set once. Only
  the end value is measured.

### 4.3 Persistence

- CONST ($0B) and DIRIO input ($06, E = $FF), with nothing typed, leave the count as it was at the
  end of the call, even desynced [XM 1285, 1286]. Both returned A = 0 there.
- DIRIO output leaves it too ([DIRIO.md](DIRIO.md)).
- **[A]** "Never written" versus "saved and restored inside the call" for these three; only a
  mid-call observer separates them.
- At program entry the count was 0 [L head; XM head].

### 4.4 zerobas, and the difference (D-CONCOL) -- ✅ FIXED 2026-11-26

**Now:** zerobas's `ce_col` (`disk/runtime.asm`) applies §4.2's rule -- printable +1; CR, FF and HOME
0; BS, cursor-left and DEL −1; every other control code unchanged -- and DIRIO-out leaves the count
(DIRIO.md). Every BDOSXL row is SAME (scratchpad/AE_concol_cap2.out, AE_concol4.out). What follows
is the difference as it was, kept as the record of what the fix changed.

**Before the fix:** zerobas's CONOUT (`conout_emit_e`, `disk/runtime.asm`, read from our own source) zeroed
the count on CR, left it on LF, and added 1 for every other byte. Its TAB counts from the cell as the
reference's does [XM 1280, 1281: identical on both machines].

Per class, the BDOSXL rows that show it:
- **8, 29, 127:** zerobas +1, the reference −1.
  - From column 0 or after a printable: L 8, 28, 31, 58, 118, 119.
  - After a 36-printable desync: L 111, 113, 115.
  - After an ESC / the prefix: L 120, 126.
- **11 and 12:** zerobas +1, the reference 0 [L 11, 12, 107, 109].
- **The other "unchanged" bytes except LF:** zerobas +1, the reference none.
  - From column 3: L 0–7, 14–27, 29, 30.
  - After a desync: L 91, 93, 97, 99, 101, 117.

In the MATRIX zerobas's counts are not comparable class by class with the reference's. zerobas
counts the setup's ESC, so each case starts at 4 instead of 3, and in modes 3 and 4 it also counts
the ESC or the prefix byte 1. Read the matrix's zerobas column only together with its own rule.

The visible effect is wherever a TAB follows on the same line. For `XYZ` FF `A` TAB `B`, the
CF-3300 writes B at CSRX 9 and zerobas at 5; the cursor after B is 10 against 6 [L 143].

## 5. Not measured (open)

- **The registers:**
  - **[A]** §1: the flags and every register but A, and their values on entry.
  - **[A]** The interrupt state (EI / DI) on return.
  - **[A]** The stack: the caller's stack or the BDOS's own, and how deep.
- **The console:**
  - **[A]** §3: Ctrl-S / Ctrl-C / Ctrl-P / STOP during CONOUT, and an ordinary key typed during
    output.
  - **[A]** CONST / DIRIO input with a key WAITING; only "nothing typed" was measured.
- **The count's lifecycle beyond one call:**
  - **[A]** Its value at cold boot, after a warm boot (BDOS $00), and after a program returns to
    COMMAND.COM. Only "0 at program entry" is measured, which cannot tell "reset on load" from
    "already 0".
  - **[A]** Whether the BDOS's own prompts move it, e.g. "Insert diskette for drive B:"
    (D-DOSDRVB) and the disk-error prompts.
  - **[A]** Whether non-console BDOS calls (file I/O, SELDSK) touch it.
- **The count in other screen states:**
  - **[A]** Bottom-line scrolling (an LF on the last row, a wrap on the last row).
  - **[A]** SCREEN 0 at width 40.
  - **[A]** The graphic modes, where CHPUT may draw nothing.
- **Order:** **[A]** whether the count is updated before or after each CHPUT, which matters to a
  hooked CHPUT (H.CHPU) that reads $F237.
- **Other paths:**
  - **[A]** The $F37D BDOS under BASIC: whether the same count is kept.
  - **[A]** LSTOUT ($05) and AUXOUT ($04): whether either touches the count.
  - **[A]** The CONIN ($01) and BUFIN ($0A) echo: whether echoed bytes move the count by this
    rule.
