<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `KYKLOK` (sub-ROM $0135) — toggle the kana lock (KANAST and the kana lamp); nothing on the NMS 8250

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubkyk.asm](../../../probes/bios/spec/xsubkyk.asm), [scratchpad/AE_xsubkyk_msx2.out](../../../scratchpad/AE_xsubkyk_msx2.out); round 2 [xsubkyk2.asm](../../../probes/bios/spec/xsubkyk2.asm), [scratchpad/AE_xsubkyk2_msx2.out](../../../scratchpad/AE_xsubkyk2_msx2.out); round 3 [xsubkyk3.asm](../../../probes/bios/spec/xsubkyk3.asm), [scratchpad/AE_xsubkyk3_msx2.out](../../../scratchpad/AE_xsubkyk3_msx2.out); decoded by [scratchpad/xsubkyk_decode.py](../../../scratchpad/xsubkyk_decode.py)).

## Summary

A sub-ROM entry of the MSX2 (standard: MSX2; listed in MAP only — the Technical Handbook does not
list it, so no published interface exists). The references **disagree**:

- On the two Japanese machines (HB-F900, FS-A1WSX) it is a kana-lock toggle: KANAST ($FCAC) flips
  between $FF and 0, and PSG R15 bit 7 (the kana lamp's line) follows it — unless MODE ($FAFC) bit 0
  is set, in which case it clears that bit, leaves KANAST alone and sets R15 bit 7. It reads no key:
  the key matrix, NEWKEY / OLDKEY, CAPST and A do not change the result.
- On the European NMS 8250 it does **nothing observable**: no register, flag, work-area byte, PSG
  register or PPI port changes, and interrupts stay off — in all 27 cases, the same as C-BIOS's bare
  `RET` at this address.

C-BIOS has no entry here (its sub-ROM holds `RET` at $0135).

## The specification

Evidence tags: **[KY1 k]** = case k of round 1 (xsubkyk.asm: A / F, KANAST, CAPST, NEWKEY / OLDKEY
row 6 and the key matrix's row 6 — CAPS or KANA / CODE held — varied one at a time, KANAST 0 / $FF);
**[KY2 k]** = round 2 (xsubkyk2.asm: KANAST $01, $40, $80, $FE, 0, $FF with PSG R15 preset to
values whose low bits differ; cases 6-9 MODE bits 7, 0, 4-6 and 1-3 flipped for the call); **[KY3 k]**
= round 3 (xsubkyk3.asm: MODE bit 0 set with KANAST $FF / $5A / 0 and R15 bit 7 preset 0 / 1; case 4
a control). Every case enters with interrupts off, SCNCNT $FF, BC $B1C1, DE $D1E1, HL $4171, and
records every register, the interrupt state (read twice), every changed work-area byte
($F380-$FFFE), port $AA and PSG R15 before / after, and every OUT to $AA, $AB and the PSG data port.
The HB-F900 and FS-A1WSX give the same values in every case [KY1 0-11] [KY2 0-9] [KY3 0-4] (their
MODE differs as booted, $04 / $44; the result does not depend on bit 6).

### Interface (HB-F900, FS-A1WSX)

- **In:** none of the registers. KANAST, PSG R15 and MODE bit 0 decide the result [M KY1, KY2, KY3].
  A / F ($00 / $01 / $FF), CAPST (0 / $FF), NEWKEY and OLDKEY row 6 (KANA or CAPS down) and the key
  matrix's row 6 (KANA / CODE or CAPS held) change nothing [M KY1 0-11].
- **Out:** A := the byte written to PSG R15; F := the flags of that byte as after `OR` (S, Z, bits 5 / 3
  from A, P/V = even parity, H = N = C = 0: $08, $8C, $44, $2C, $00, $84, $AC for A = $4F, $CF, $00,
  $3A, $15, $95, $AA); B := R15 before AND $7F; HL := $FAFC; C, DE, IX, IY and SP kept [M KY1 0-11,
  KY2 0-9, KY3 0-4].
- **Interrupts:** entered off, returned **on** (IFF = 1; one timer interrupt ran inside the call:
  JIFFY +1, INTCNT −1, SCNCNT −1) [M KY1, KY2, KY3, every case]. Entry with interrupts on: [A].

### Behaviour (HB-F900, FS-A1WSX)

- **MODE bit 0 clear:** KANAST := 0 if it was $FF, else $FF (0, $01, $40, $80, $FE → $FF; $FF → 0)
  [M KY1 0-11, KY2 0-6, 8, 9, KY3 4]. PSG R15 is written once: (R15 AND $7F) OR ($80 if the new
  KANAST is 0) — bit 7 = 0 while the kana lock is on, the low seven bits kept ($00, $3A, $15, $4F, $2A
  kept) [M KY1 0-11, KY2 0-6, 8, 9, KY3 4].
- **MODE bit 0 set:** MODE bit 0 := 0 (bit 1 kept), KANAST kept ($FF, $5A and 0 all unchanged), and
  R15 := R15 OR $80 whatever KANAST holds [M KY2 7, KY3 0-3].
- MODE bits 1-7 do not change the result (bits 7, 4-6 and 1-3 flipped gave the plain toggle)
  [M KY2 6, 8, 9].
- **Nothing else:** no OUT to $AA or $AB (port $AA reads the same before and after, so the CAPS lamp
  and the key-row select are untouched; the $AA / $AB logs were armed at the same point as the PSG log,
  which did record, but have no positive control of their own); exactly one PSG data write per call; the work area changes only in KANAST or MODE and by the timer
  interrupt (SCNCNT, JIFFY, INTCNT, STATFL); CAPST is never written [M KY1, KY2, KY3, every case].
- Which R15 bit-7 level lights the lamp on a real machine is not observable here [A]; that bit 7 drives
  the kana lamp is [A].

### NMS 8250 (European)

- Every output equals the input in all 27 cases: A, F, BC, DE, HL, IX, IY and SP kept; interrupts stay
  off; no work-area byte, PSG write or OUT to $AA / $AB; including KANAST $FF / $5A / 0 and MODE bit 0
  set [M KY1 0-11, KY2 0-9, KY3 0-4]. What the entry would do in a state the probes did not reach is
  [A]; from its effects it cannot be told from a `RET`.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) hold `RET` at $0135: nothing is written, every register is
kept, interrupts stay off ([scratchpad/AE_xsubkyk_msx2.out](../../../scratchpad/AE_xsubkyk_msx2.out),
[scratchpad/AE_xsubkyk2_msx2.out](../../../scratchpad/AE_xsubkyk2_msx2.out),
[scratchpad/AE_xsubkyk3_msx2.out](../../../scratchpad/AE_xsubkyk3_msx2.out)).

- **MSX2 JP and MSX2+ JP builds** (against the HB-F900 / FS-A1WSX): no kana toggle — KANAST, MODE bit 0
  and PSG R15 bit 7 are left as they were; A, F, B and HL are not set; interrupts are not turned on.
- **MSX2 EU build** (against the NMS 8250): no difference in any measured case.

## Open (not measured)

- Entry with interrupts on.
- The JP rule with KANAST values other than 0, $01, $40, $80, $FE, $FF, $5A (the toggle's test is
  "= $FF" on every value tried).
- Whether the Japanese machines' keyboard scan (the KANA key) calls this entry: the probes held the
  scan off (SCNCNT $FF) and never pressed the key with the scan running.
- The NMS 8250 in other states (another screen mode, other MODE values than bit 0 / 1 flipped).

## Related pages

MSX1 [CHGCAP](../../bios/CHGCAP.md) (the CAPS lamp, port $AA bit 6); [the input calls' concept page](../../concepts/input-calls.md);
[the clock-and-misc page](../concepts/clock-and-misc.md).

## Tests that cover it

none yet
