<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SUBROM` ($015C) — call a sub-ROM routine, with IX on the stack

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX (the same on all three;
> [xextrom.asm](../../../probes/bios/spec/xextrom.asm) cases 7-11 and 15,
> [scratchpad/AE_xextrom_msx2.out](../../../scratchpad/AE_xextrom_msx2.out), decoded by `scratchpad/xextrom_decode.py`).
> Goldfish pass 1 (test writer) 2026-11-23: 1 finding (the stack contrast with EXTROM was a counting convention),
> wording corrected; nothing new measured, the rest is EXTROM's.

## Summary

`SUBROM` calls the sub-ROM routine at IX, like [EXTROM](EXTROM.md), for a caller that has also pushed
IX: the handbook's pattern is `PUSH IX` / `LD IX,routine` / `JP SUBROM`, inside a routine the program
CALLs. The pushed word comes back in IX and SUBROM returns to the caller's caller, so the pattern
leaves the stack balanced. Everything else is EXTROM's behaviour. The sub-ROM and EXBRSA are on the
[region page](README.md#the-sub-rom).

## The specification

**Interface.**
- In: IX = the sub-ROM address, with IX also pushed on the stack [P A1]; the worked example (INIPAL, in
  App. 1's notes) has the caller `PUSH IX` and then `JP SUBROM` [P A1].
- Out: whatever the routine returns [P A1]. The alternate set and IY "reserved", as EXTROM [P A1].

**Measured** [M] (the published pattern, from a routine the probe CALLs; identical on all three references):
- **IX on return = the word pushed before the jump** -- $A5A5 in cases 7, 9-11, 15, $1234 in case 8 -- not the target
  and not the routine's IX; the return lands in the code that CALLed the pattern, with SP back at its value before that
  CALL [M 7-11, 15].
- **Everything else as [EXTROM](EXTROM.md):** A, F, BC, DE, HL and IX (= the target) reach the routine, IY and the
  alternates do not; AF, BC, DE, HL come back from the routine, IY and the alternates are the caller's; the routine
  runs with interrupts off and only page 0 switched; on return interrupts are on if they were on at entry (case 9),
  else the routine's state (off in case 7, on after the routine's EI in case 10); the slots as before [M 7-11].
- With the real sub-ROM: GETPLT through SUBROM gives B $A3, C $06 (the palette set by SETPLT through EXTROM) and IX the
  pushed $A5A5 [M 15]. From page 2 RAM the same (case 11) [M 11].
- **Stack:** the routine's SP is 28 bytes below the SP at the `JP SUBROM` (the pushed IX already on it) [M 7-11] --
  the same 28 as EXTROM's below the SP at its `CALL` instruction (an expanded EXBRSA slot); counted from the last word
  the caller put on the stack (the pushed IX here, the CALL's return address there), the two are 28 and 26.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) match every rule above. The only measured difference is the stack depth:
C-BIOS's routine runs 24 bytes below the SP at the `JP SUBROM` (the references' 28), and GETPLT through it went 32
deep (the references' 40) [M 7-11, 15].

## Open (not measured)

- SB-2: SUBROM entered without the pushed word (a CALL SUBROM, or JP with nothing pushed) -- documents misuse only.
- The time it takes (the harness has no T-state counter).

## Related pages

[region page](README.md), [EXTROM](EXTROM.md), [CHKSLZ](CHKSLZ.md); [CALSLT](../../bios/CALSLT.md),
[slots](../../concepts/slots.md).

## Tests that cover it

None yet.
