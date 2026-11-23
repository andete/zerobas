<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SUBROM` ($015C) — call a sub-ROM routine, with IX on the stack

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`SUBROM` calls the sub-ROM routine at IX, like [EXTROM](EXTROM.md), for a caller that has also pushed
IX: the handbook's pattern is `PUSH IX` / `LD IX,routine` / `JP SUBROM`, so that the caller's IX comes
back and the return goes to the caller's caller. The sub-ROM and EXBRSA are on the
[region page](README.md#the-sub-rom).

## The specification

**Interface.**
- In: IX = the sub-ROM address, with IX also pushed on the stack [P A1]. The entry's wording leaves
  open WHO pushes it; the worked example (INIPAL, in App. 1's notes) has the caller `PUSH IX` (its own
  IX, before loading the target) and then `JP SUBROM` [P A1]. That the example's convention is the
  rule [A].
- Out: whatever the routine returns [P A1]. Registers: the alternate set and IY "reserved", as
  EXTROM [P A1] (meaning unclear, see [EXTROM](EXTROM.md)).
- On return IX holds the word pushed before the jump, and the stack is one word shallower than at
  the jump [A] (what the pattern implies; not stated).
- Interrupt state and slots: as [EXTROM](EXTROM.md) [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

[EXTROM](EXTROM.md)'s cases EX-1 to EX-13, with its stub, run through SUBROM with the published
pattern (`PUSH IX` of a marker / `LD IX,stub` / `JP SUBROM`, from a routine the probe CALLs), each
read against EXTROM's result on the same machine. Records as there, plus the stack words around SP.

| case | inputs | state | separates | F900 | 8250 | WSX |
|---|---|---|---|---|---|---|
| SB-1 | pushed marker $A5A5, then $1234 in a second run | clobber stub | IX on return = the pushed word (popped) vs the target vs the clobber value; the return lands in the probe | ? | ? | ? |
| SB-2 | `LD IX,stub` / `CALL SUBROM`, no push, a safe return address planted under the call's return | marker words on the stack | which stack word SUBROM pops into IX and where it returns (documents misuse) | ? | ? | ? |
| SB-3 | as SB-1 | the stub's dump and clobber, interrupts on / off, stub EI / DI | registers and interrupt state as EXTROM's EX-2 to EX-5, or different | ? | ? | ? |
| SB-4 | as SB-1, from page 1 and page 2 RAM | EX-9's | SUBROM from any page | ? | ? | ? |
| SB-5 | as SB-1 | EX-12's EXBRSA change between calls | EXBRSA read at each call | ? | ? | ? |
| SB-6 | as SB-1 | — | stack depth and time (README methods) | ? | ? | ? |

## Related pages

[region page](README.md), [EXTROM](EXTROM.md), [CHKSLZ](CHKSLZ.md); [CALSLT](../../bios/CALSLT.md),
[slots](../../concepts/slots.md).

## Tests that cover it

None yet.
