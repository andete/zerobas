<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `EXTROM` ($015F) — call a sub-ROM routine

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`EXTROM` calls the sub-ROM routine at the address in IX, in the sub-ROM's slot (EXBRSA), and
returns what that routine returns. It is the usual way to reach the sub-ROM: `LD IX,routine` /
`CALL EXTROM`. The sub-ROM and EXBRSA are on the [region page](README.md#the-sub-rom).

## The specification

**Interface.**
- In: IX = the sub-ROM address to call [P A1]; the other registers as the routine takes them [A].
- Out: whatever the routine returns [P A1].
- Registers: the handbook lists "the alternate registers and IY" as **reserved** [P A1] — whether
  that means kept or destroyed is not clear [A]; CALSLT, which an inter-slot call is built on,
  destroys IX, IY and the alternate set [P 5§7.2].
- The interrupt state on return is the one at entry (MSX2 inter-slot calls) [P 5§7.2] [A] (said of
  inter-slot calls in general, not of EXTROM).
- The page-0 slot is put back on return [A]. Not for use under MSX-DOS [P 5§7.2.2].

## Differences from the reference

Not measured yet.

## Open (not measured)

**The stub.** Most cases point EXBRSA at a RAM slot whose page 0 holds a probe stub at IX (planted
with WRSLT; RAM stubs are allowed, no ROM byte is read). The stub stores every register it receives
— A, F, BC, DE, HL, IX, IY, the alternate set, SP, the interrupt state (twice), port $A8 — into page-3
RAM, then (in the "clobber" variant) loads EVERY register, IX, IY and the alternates with clobber
values unlike the entry ones, and returns. So a register after EXTROM equal to its ENTRY value was
preserved by EXTROM; equal to the CLOBBER value, passed out untouched; anything else, destroyed.
Records after the return: every register, IX, IY, the alternates, SP, the interrupt state (twice),
port $A8, the secondary slot register of each expanded slot, EXBRSA, EXPTBL; the 128 bytes below SP
(marker words).

| case | inputs | state | separates | F900 | 8250 | WSX |
|---|---|---|---|---|---|---|
| EX-1 | IX = stub; A, F, BC, DE, HL, IY, alternates distinctive | S-REGS, dump-only stub | which registers reach the routine (the stub's record) | ? | ? | ? |
| EX-2 | as EX-1 | clobber stub | per register: preserved by EXTROM / passed out / destroyed — "reserved" settled for IY and the alternates | ? | ? | ? |
| EX-3 | as EX-1 | interrupts ON at entry, neutral stub | the state inside the routine (stub's record) and on return: restored / off (MSX1 CALSLT) | ? | ? | ? |
| EX-4 | as EX-1 | interrupts OFF at entry | the same, from off | ? | ? | ? |
| EX-5 | as EX-1 | entry OFF, the stub does EI before RET; and entry ON, the stub does DI | the entry state restored even when the routine changes it, or the routine's state returned | ? | ? | ? |
| EX-6 | IX $2000 / $3ABC (two stub addresses) | clobber stub | IX after: kept, the target, or the clobber value | ? | ? | ? |
| EX-7 | as EX-1 | 128 bytes of marker words below SP | EXTROM's own frame: entry SP minus the SP the stub sees; the lowest marker overwritten | ? | ? | ? |
| EX-8 | as EX-1 | stub records port $A8 and page 1-3 slots during the call | the slots during the call (page 0 only switched?) and after it (all put back) | ? | ? | ? |
| EX-9 | as EX-1, CALL EXTROM from probe code in page 1 RAM, then page 2 RAM | — | EXTROM from any page | ? | ? | ? |
| EX-10 | IX = a real sub-ROM entry with a published register interface (App. 1's SUB-ROM list), its inputs set | EXBRSA as booted | the stub's findings hold on the real sub-ROM (outputs come back) | ? | ? | ? |
| EX-11 | IX = RSLREG ($0138), EXBRSA := $00 | run only where EXPTBL shows the main ROM in slot 0 | what EXBRSA $00 ("no sub-ROM") does: an inter-slot call to slot 0 (A = port $A8 during the call) vs a refusal | ? | ? | ? |
| EX-12 | as EX-1 | EXBRSA := the stub's slot, then changed to another RAM slot with a second stub between two calls | EXBRSA read at each call vs a copy | ? | ? | ? |
| EX-13 | as EX-1 | — | the time it takes (README methods) | ? | ? | ? |

## Related pages

[region page](README.md), [SUBROM](SUBROM.md), [CHKSLZ](CHKSLZ.md); [CALSLT](../../bios/CALSLT.md),
[slots](../../concepts/slots.md).

## Tests that cover it

None yet.
