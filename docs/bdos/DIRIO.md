<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# `DIRIO` (BDOS $06) — direct console output (and input)

> **Spec:** DRAFT 4 (2026-11-17) for OUTPUT (E ≠ $FF), as differences from [CONOUT](CONOUT.md).
> Input (E = $FF) has no page section yet.

## Summary

With E ≠ $FF, `DIRIO` writes E to the screen directly: no TAB expansion and no column count.
zerobas counts the column there too and expands a TAB itself (TODO D-CONCOL).

## The specification — output

Read [CONOUT.md](CONOUT.md) first. The
evidence tags and units are the same:
- **[XM n]**: the matrix, [`scratchpad/XM_table.out`](../../scratchpad/XM_table.out); DIRIO is
  mode 1, cases 256–510 (511 is the skipped $FF; its A is the probe's own).
- **[L n]**: [`scratchpad/XL_table.out`](../../scratchpad/XL_table.out).
- **[A]**: not measured.

In: C = $06, E = the byte (any value but $FF; $FF is DIRIO's INPUT, a separate spec).

- **The logical column ($F237) is left as it was, for every byte value 0–254**, from the desynced
  start: the count stays at 3 [XM 256–510]. With the cell set to 5, a DIRIO TAB leaves it at 5
  [XM 1283]. **[A]** "Never written" versus "saved and restored inside the call".
- **A TAB moves the cursor to the screen's own next tab stop, not to the count's.** From CSRX 21 it
  ends at 25 [XM 265]; from CSRX 8 at 9, with the count at 36 [L 152].
- **[A]** Whether CHPUT receives the 9 itself, or the BDOS writes spaces counted from the cursor.
  Both give these cursors. Separating it needs an H.CHPU trace or a TAB sent as an `ESC Y`
  parameter: see [CHPUT](../bios/CHPUT.md).
- **[A]** Every other byte reaching CHPUT unchanged: as CONOUT §2.
- **A on return = E for every byte, TAB included** (A = 9 after a TAB) [XM 256–510, 1283]. CONOUT
  returns 0 after a TAB.
- Open:
  - **[A]** The other registers and the flags.
  - **[A]** Whether DIRIO-out skips the console checks (Ctrl-S / Ctrl-C / Ctrl-P / STOP) that
    CONOUT may make (CONOUT §3).

zerobas (part of D-CONCOL), three differences:
- **The count:** DIRIO-out updates it as zerobas's CONOUT does; the reference leaves it
  [XM 256–510; L 70–75, 85, 150, 152].
- **TAB on screen:** zerobas expands a DIRIO TAB from the count. From count 36 / CSRX 8, zerobas
  reaches CSRX 12 and the CF-3300 9 [L 152]. From the matrix's start both land on 25 [XM 265].
- **A after a TAB:** zerobas 0, the CF-3300 9 [XM 265, 1283].
