<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `EXTROM` ($015F) — call a sub-ROM routine

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX (the same on all three;
> [xextrom.asm](../../probes/bios/spec/xextrom.asm), [scratchpad/AE_xextrom_msx2.out](../../scratchpad/AE_xextrom_msx2.out),
> decoded by `scratchpad/xextrom_decode.py`; EXBRSA $00: [xextrom0.asm](../../probes/bios/spec/xextrom0.asm),
> [scratchpad/AE_xextrom0_msx2.out](../../scratchpad/AE_xextrom0_msx2.out)).

## Summary

`EXTROM` calls the sub-ROM routine at the address in IX, in the slot EXBRSA names, and returns what
that routine returns. It is the usual way to reach the sub-ROM: `LD IX,routine` / `CALL EXTROM`. The
routine gets A, F, BC, DE, HL and IX as the caller set them, with interrupts off; on return the caller
gets the routine's AF, BC, DE, HL and IX, but its own IY and alternate registers back, the slots as
they were, and interrupts on if they were on at the call. The sub-ROM and EXBRSA are on the
[region page](README.md#the-sub-rom).

## The specification

**Interface.**
- In: IX = the sub-ROM address to call [P A1]; the other registers as the routine takes them [A].
- Out: whatever the routine returns [P A1].
- Registers: the handbook lists "the alternate registers and IY" as **reserved** [P A1]; CALSLT
  destroys IX, IY and the alternate set [P 5§7.2]. Not for use under MSX-DOS [P 5§7.2.2].

**Measured** [M] (run file above; case numbers are the decoder's; identical on all three references):
- **What reaches the routine** (cases 0-11, a RAM stub at IX in page 0 of the RAM slot): A, F (entry $00 and $FF
  both arrive unchanged), BC, DE, HL as the caller set them; IX = the routine's address ($2000, $3ABC: case 4).
  IY and the alternate set do NOT arrive (the routine sees other values) [M 0-11].
- **What comes back** (the clobber stub, cases 0, 1, 4, 6, 14): AF, BC, DE, HL and IX are the routine's (passed out
  untouched, IX included); IY, AF', BC', DE', HL' are the CALLER's entry values -- EXTROM saves and restores them, so
  "reserved" means *preserved for the caller* [M 0, 1, 4, 6, 14]. The same with the real sub-ROM: SETPLT / GETPLT
  (cases 12, 13) give back the routine's registers (GETPLT palette 5 after SETPLT $A3 / $06: B $A3, C $06) and the
  caller's IY and alternates [M 12, 13].
- **Interrupts.** Inside the routine they are OFF, whatever the caller had [M 0-11]. On return: entry ON gives ON,
  even when the routine did DI (case 3) [M 1, 3]; entry OFF gives the routine's state: off when it returns with
  interrupts off (cases 0, 5), ON when it did EI (case 2) or is a real sub-ROM routine that enables them (SETPLT /
  GETPLT, cases 12, 13) [M 0, 2, 5, 12, 13].
- **Slots.** During the routine only page 0 is switched, to EXBRSA's slot (port $A8 bits 1-0 and, for an expanded
  slot, the secondary register's page-0 bits); pages 1-3 are as at the call [M 0-11]. After the return port $A8 and
  page 3's secondary register are exactly as before the call [M 0-14].
- **EXBRSA is read at every call**, not cached: EXBRSA back to the RAM slot after two calls to the real sub-ROM runs the
  stub again (case 14) [M 14]. EXTROM does not change EXBRSA [M 0-14].
- **EXBRSA $00** (the "no sub-ROM" value) is not refused: with IX = RSLREG ($0138) the call runs the main ROM's RSLREG
  in slot 0 -- A comes back $F4, port $A8 with page 0 at slot 0 -- and BC, DE, HL, IY come back unchanged
  ([xextrom0](../../scratchpad/AE_xextrom0_msx2.out)) [M].
- **From any page:** called from code in page 2 RAM (case 6) it behaves as from page 1 [M 6].
- **Stack:** the routine's SP is 26 bytes below the caller's SP at the `CALL EXTROM` (the return address included); a
  routine that pushes nothing makes the lowest stack byte written 26 below it; SP after the return = SP before the
  CALL [M 0-14]. With the real SETPLT / GETPLT the stack went 42 / 38 bytes deep (44 / 38 on the FS-A1WSX) [M 12, 13].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) match every rule above: registers in and out, IY / alternates preserved,
the interrupt rule, the slots, EXBRSA per call, EXBRSA $00. The only measured difference is the stack: C-BIOS's
EXTROM frame is 22 bytes (the references' 26), and SETPLT / GETPLT went 34 / 30 deep [M 0-14]. Not a contract a
caller can see unless it measures the stack.

(Seen on the way, not EXTROM's: the references' sub-ROM GETPLT returns D = the palette number, C-BIOS's leaves DE
alone [M 13] -- [GETPLT](../sub/GETPLT.md)'s page.)

## Open (not measured)

- The time it takes (EX-13): the harness has no T-state counter.
- A routine that leaves the stack unbalanced, or a target in page 1-3 (IX >= $4000).
- Whether interrupts are switched off INSIDE EXTROM before the slot switch (only the routine's view is measured).

## Related pages

[region page](README.md), [SUBROM](SUBROM.md), [CHKSLZ](CHKSLZ.md); [CALSLT](../../bios/CALSLT.md),
[slots](../../concepts/slots.md).

## Tests that cover it

None yet.
