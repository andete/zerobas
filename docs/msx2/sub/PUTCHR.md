<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `PUTCHR` (sub-ROM $0139) — put a character into the key buffer (interface unpublished)

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubpch.asm](../../../probes/bios/spec/xsubpch.asm), [xsubpch2.asm](../../../probes/bios/spec/xsubpch2.asm); [scratchpad/AE_xsubpch_msx2.out](../../../scratchpad/AE_xsubpch_msx2.out), [scratchpad/AE_xsubpch2_msx2.out](../../../scratchpad/AE_xsubpch2_msx2.out); round 3 [xsubpch3.asm](../../../probes/bios/spec/xsubpch3.asm), [scratchpad/AE_xsubpch3_msx2.out](../../../scratchpad/AE_xsubpch3_msx2.out); decoded by [scratchpad/xsubpch_decode.py](../../../scratchpad/xsubpch_decode.py)). **The references disagree:** the NMS 8250 does nothing.
>
> Goldfish pass 1 (test writer) 2026-11-23: 3 findings, 2 measured, 0 moved to open.

## Summary

An entry at sub-ROM $0139, named PUTCHR by the MSX Assembly Page's list only; the MSX2 Technical
Handbook does not list it. Despite the name it draws nothing: on the HB-F900 and the FS-A1WSX it
stores the character in A in the keyboard buffer (KEYBUF, $FBF0, 40 bytes) at PUTPNT ($F3F8) and
advances PUTPNT, wrapping at the buffer's end and not advancing when the buffer is full, so that the
next CHGET returns the character, as if it had been typed. On the NMS 8250 the call changes nothing
at all. C-BIOS has no routine here: the call returns at once, which is what the NMS 8250 does.

## The specification

Case numbers `[M r n]` are the decoders': r = `xsubpch` (round 1: the screen, cases 0-19), `xsubpch2` (round 2:
the key buffer, cases 0-10) or `xsubpch3` (round 3: other BC / DE, pointers outside the buffer, cases 0-3). Rounds 2
and 3 fill KEYBUF[i] with $80 + i and $FC18-$FC1A with $E1-$E3, and set PUTPNT / GETPNT ($F3FA) per case; rounds 1
and 2 enter with BC $B1C2, DE $4E5F, round 3 with BC 0 / DE $FFFF, BC $1234 / DE $5678 and BC $B1C2 / DE $4E5F.

**Interface.**
- Not published: the handbook's sub-ROM listing goes from VDPSTA ($0131) to SETPAG ($013D) [P App. 1, SUB-ROM].
  An entry on all three references [M xsubpch 0-19].
- In: **A = the character** (stored as given: $51, $52, $00, $0D, $FF, ...) [M xsubpch2 0, 1, 5, 6, 7]. HL, the
  cursor and the screen mode are not inputs: in every round-1 case, whatever HL, cursor or mode, HL comes back one
  higher than in the case before ($FBF1, $FBF2, ... $FC04) — PUTPNT advanced once per call [M xsubpch 0-19].
- Out (HB-F900, FS-A1WSX): **HL = PUTPNT + 1, wrapped** (PUTPNT $FC17 → $FBF0, $FB17 → $FBF0), also when the
  buffer is full and PUTPNT is not advanced [M xsubpch2 0-4, 9, 10; xsubpch3 0-3]; A = the low byte of GETPNT
  ($F0, $00, $F6, $10, $19 for GETPNT $FBF0, $FC00, $FBF6, $FC10, $FB19) [M xsubpch2 0-10; xsubpch3 0-3];
  **F = the flags of `CP L`** with that A and L = the low byte of the new HL — Z set exactly when the buffer was
  full (F $62 and $4A full; $B3, $92, $23, $93, $9A otherwise; all 15 values are those flags, bits 5 / 3 from L)
  [M xsubpch2 0-10; xsubpch3 0-3]. BC, DE, IX ($0139) and IY kept (BC $B1C2 / $0000 / $1234, DE $4E5F / $FFFF /
  $5678) [M xsubpch2 0-10; xsubpch3 0-3].
- Interrupts on return (HB-F900, FS-A1WSX): **ON**, entered with DI or EI [M xsubpch 0-19; xsubpch2 0-10; xsubpch3 0-3].

**Behaviour** (HB-F900 and FS-A1WSX; the same on both).
- **(PUTPNT) := A, always** — also when the buffer is full (PUTPNT + 1 = GETPNT, also across the wrap): the byte
  at PUTPNT is written there too, and PUTPNT stays [M xsubpch2 0-7, 9, 10; xsubpch3 0-3 ($FB17 too); full: xsubpch2 3, 4; xsubpch3 1, 2]. That slot is not part of
  the waiting characters (GETPNT .. PUTPNT − 1), so a full buffer loses the new character and keeps the old ones
  [M xsubpch2 3, 4: CHGET then returns the oldest one, $86 / $80].
- **PUTPNT := PUTPNT + 1**, and $FBF0 when the new value's **low byte** is $18 (PUTPNT $FC17 → $FBF0 [M xsubpch2
  2]; also PUTPNT $FB17 → $FBF0, so the test is not "= $FC18" [M xsubpch3 3]); unless the new value's **low byte**
  equals GETPNT's low byte (full), then PUTPNT is kept [M xsubpch2 3, 4]: with PUTPNT $FC18 and GETPNT $FB19 the
  buffer counts as full and PUTPNT stays $FC18, so the test is not a 16-bit compare [M xsubpch3 2]. Inside the
  buffer ($FBF0-$FC17) the low bytes are all different, so both 8-bit tests give the 16-bit answer there. A PUTPNT
  already past the buffer ($FC18) is not pulled back: A is written at $FC18 and PUTPNT becomes $FC19 [M xsubpch2 9].
- **The character is then read back by CHGET:** CHSNS reports a character waiting, and CHGET returns A when the
  buffer was empty before (A $51, $00, $0D, $FF, $57), GETPNT advancing past it [M xsubpch2 0, 5-8, 10].
- **GETPNT is not changed** by the call [M xsubpch2 0-10]; the rest of KEYBUF and $FC18-$FC1A are not changed
  [M xsubpch2 0-10].
- **No screen output:** in SCREEN 0 (width 40 and 80), SCREEN 1 and SCREEN 5, for printable characters, control
  characters (CR, LF, BS, FF, ESC, DEL, TAB, $01) and the cursor at the last column / bottom right, no VRAM byte of
  the name table (SCREEN 5: the 27136-byte bitmap) changes, and CSRX / CSRY, LINTTB, CNSDFG, ESCCNT, GRPACX and GRPACY
  stay as found [M xsubpch 0-19].

**The NMS 8250** does none of this: every register comes back as it went in (A, F $C5, HL, IX $0139), the
interrupt state is kept (off when entered with DI, on with EI), and KEYBUF, PUTPNT, GETPNT, VRAM and the cells
above are unchanged [M xsubpch 0-19; xsubpch2 0-10; xsubpch3 0-3] — the capture is byte-identical to C-BIOS's on every case
(`SAME` in the msx2eu row of all three run files).

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) have no routine at $0139: the address holds the RET filler of C-BIOS's
`sub.asm`, and the call returns at once with every register and the interrupt state as they were, nothing stored
[M xsubpch 0-19; xsubpch2 0-10; xsubpch3 0-3]. Against the HB-F900 and the FS-A1WSX that is a missing behaviour: the character
does not reach the key buffer, and interrupts stay off when the call is made with DI. Against the NMS 8250 it is
the same.

## Open (not measured)

- Why the NMS 8250 differs (a different sub-ROM revision, or a condition its routine tests) — every input measured
  gave no change there.
- Hooks: whether the routine passes through a hook (none watched).
- Stack depth and time.

## Related pages

The MSX1 [CHGET](../../bios/CHGET.md), [CHSNS](../../bios/CHSNS.md), [KILBUF](../../bios/KILBUF.md) (the key buffer's
reader side).

## Tests that cover it

none yet
