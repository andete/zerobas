<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `STROUT` (BDOS $09) — write a `$`-terminated string to the console

> **Spec:** DRAFT 4 (2026-11-17), as differences from [CONOUT](CONOUT.md).

## Summary

`STROUT` writes the string at DE, up to its first `$`, as if each character went through
`CONOUT`. zerobas differs exactly where CONOUT does.

## The specification

Read [CONOUT.md](CONOUT.md) first; its §4.2
rule is final. The evidence tags and units are the same:
- **[XM n]**: the matrix, [`scratchpad/XM_table.out`](../../scratchpad/XM_table.out); STROUT is
  mode 2, cases 512–767.
- **[L n]**: [`scratchpad/XL_table.out`](../../scratchpad/XL_table.out).
- **[A]**: not measured.

In: C = $09, DE = the string, ending at the first `$` ($24).

- **Each byte before the `$` changes the count as CONOUT's rule says, and a TAB is expanded from
  the live cell.** This is measured for every byte value but `$`, each as a ONE-BYTE string from
  the desynced idle state [XM 512–767]. With the cell set to 5, a TAB gives 8 [XM 1282].
- **Inside a string, after an ESC or the prefix:** only `ESC Y #` [L 83] was measured. **[A]** The
  other bytes in those states inside one string; the CONOUT sweeps (modes 3 and 4) were separate
  calls.
- **Only `$` ($24) ends the string.** $A4 does not: it is written and counted, and the string runs
  on to the `$` [XM 676: count 4, CSRX 22].
- **The `$` is neither written nor counted** [L 77]. (XM 548 is a skipped case: no STROUT was
  made there, and its A is the probe's own; see the table header.)
- **A on return is `$` ($24)** [XM 512–767 except 548, 1282]: the terminator, not the last byte
  written.
- Open:
  - **[A]** The other registers, the flags, and DE on return, i.e. whether DE is left past the
    `$`.
  - **[A]** An empty string (`$` at DE).
  - **[A]** A `$` that falls inside a pending escape (a bare ESC, `ESC x`, `ESC Y` row or column)
    or right after the prefix 1.
  - **[A]** Strings in page 0 or page 1 (where the disk ROM is paged in during the call), and DE
    wrapping past $FFFF. The probe's strings were in page 0's TPA ($01xx).
  - **[A]** The console checks during the string (Ctrl-S / Ctrl-C / Ctrl-P / STOP): see CONOUT §3.

zerobas: the count differs as CONOUT §4.4 says, for the same bytes; A on return matches
[XM 512–767].
