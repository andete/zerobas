<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `CHGCPU` ($0180) — switch the turbo R between the Z80 and the R800

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the Panasonic FS-A1GT and FS-A1ST (identical in every output but
> timing jitter; [xchgcpu.asm](../../../probes/bios/spec/xchgcpu.asm),
> [scratchpad/AE_xchgcpu_tr.out](../../../scratchpad/AE_xchgcpu_tr.out), decoded by
> [scratchpad/xchgcpu_decode.py](../../../scratchpad/xchgcpu_decode.py); the boot:
> [xtrboot.asm](../../../probes/bios/spec/xtrboot.asm), [scratchpad/AE_xtrboot_tr.out](../../../scratchpad/AE_xtrboot_tr.out)).
> No goldfish pass yet.

Main-ROM entry, turbo R only. Listed by MAP's "MSX turbo R BIOS Entries" ([index](../index.md)); C-BIOS has no
turbo R build.

## Summary

`CHGCPU` selects the CPU: A bits 1-0 = 0 for the Z80, 1 for the R800 with the BIOS in ROM, 2 for the R800 with the
BIOS copied to DRAM; bit 7 asks for the turbo LED to follow the CPU. Any other A — mode 3, or any of bits 6-2 set —
is ignored without a trace: no register, flag, port or RAM changes, and the interrupt state stays. An accepted call
writes the mode to the S1990's register 6 (every time, even when the mode is already current), writes port $A7 from a
RAM copy at $FCB1, keeps every register, and returns with interrupts ENABLED whatever the entry state was. The
machine boots in the Z80 — a cartridge's INIT runs in it — and the boot ends in R800 DRAM mode with the LED on.

## The specification

**Interface** [P MAP]: A = `L 0 0 0 0 0 x x`, xx = 00 Z80 (ROM) mode, 01 R800 ROM mode, 10 R800 DRAM mode; L = "the
Turbo LED is switched with the CPU". Output none; registers: none.

**Evidence.** `[XC n]` = case n of xchgcpu (40 cases; table in the probe). Each case: CHGCPU(start) to reach the
start mode, DI, every register loaded with a distinct value (A and F per case), DI or EI, CALL $0180; then the
registers, the IFF (read twice), port $A7, the S1990's registers 0-15 (OUT $E4 / IN $E5), GETCPU, every work-area
cell $F380-$FFFE that changed, the OUTs to $A7 / $E4 / $E5 during the call (openMSX watchpoints), the active CPU
(`@cpusnap`), and three timed loops. `[XC INIT]` = the state at cartridge INIT before any call, `[XC END]` = a closing
CHGCPU($82) from R800 DRAM. `[XB]` = xtrboot.

**Which A is accepted** [M]:
- A = $00, $01, $02 and $80, $81, $82 switch the mode, from each of the three start modes (start with and without the
  LED bit) [XC 0-17, 24-29, 33-36].
- **Everything else is ignored:** A = $03, $83 (mode 3), $04, $05, $06 (bit 2), $41 (bit 6), $7E, $FD, $FF [XC 18-23,
  30-32, 37-39]. Then: no OUT to $A7, $E4 or $E5; no work-area cell changes ($FFFD / $FFFE included); the mode stays
  (GETCPU and the S1990 unchanged); every register comes back as it went in, F included (F $00 → $00 [XC 18],
  F $FF → $FF [XC 37]); the interrupt state is kept (DI stays DI [XC 18-23, 30-32, 37, 39], EI stays EI [XC 38]).
  There is no error indication [M]. The measured accept set is exactly "A AND $7F is 0, 1 or 2" [M, the cases above];
  A values not run [A].

**What an accepted call does** [M]:
- **The S1990's register 6** := $60 (Z80), $40 (R800 ROM), $00 (R800 DRAM): one OUT $E4 = 6, then OUT $E5 = the value
  — once for the R800 modes, twice ($60, $60) for the Z80 [XC 0-17]. It does so even when the mode is already the
  current one [XC 7, 14, 17]. The active CPU (openMSX's, `@cpusnap` right after the call) follows: z80 for $60, r800 for
  $40 / $00 [XC 0-17]. The other S1990 registers read the same in every case and both modes: R#0-R#4 $FF, R#5 $00,
  R#7-R#12 $FF, R#13 $03, R#14 $2F, R#15 $8B [XC 0-39].
- **Port $A7 and $FCB1:** one OUT $A7 per call, and the byte written equals $FCB1 after the call [XC 0-17, 24-29,
  33-36]. The new $FCB1 is the old one with **bit 1 := 1 for the Z80, 0 for the R800**, and **bit 7 := 1 for the R800,
  0 for the Z80 when A bit 7 is set**, kept when A bit 7 is clear; bits 6-2 and 0 are kept: $80 → $82 (A $00), $7D →
  $7D (A $01), $7D → $7F (A $80), $FF → $FD (A $01), $02 → $80 (A $81), $80 → $02 (A $80), $02 → $00 (A $01)
  [XC 33-36, 4, 9, 1]. The kept bit 7 comes from $FCB1, not from the port: $FCB1 := $80 with the LED never set by a
  call gives OUT $A7 $82 [XC 33]. Port $A7 reads $00 in every case, before and after [XC 0-39]: the LED state cannot be
  read back from the port. That bit 7 of port $A7 is the turbo LED (and bit 0 the pause LED) is not from a source read
  here [A].
- **$FFFD / $FFFE** (MAP: "temporary stack pointer for CHGCPU") := $E7E8 in every accepted case, from garbage that
  differs per case [XC 0-17, 24-29, 33-36]. The probe's SP before the CALL was $E800 in every case, so the cell is
  SP − $18, a stack address inside the call [M, one SP]; that it always tracks the caller's SP [A].
- **Nothing else in $F380-$FFFE changes** but SCNCNT ($F3F6), JIFFY ($FC9E) and $FCA2, which the timer interrupt
  writes (they change only in cases where an interrupt was taken) [XC 0-39].
- **Registers:** AF, BC, DE, HL, IX, IY and AF', BC', DE', HL' are all kept, F included (entry F $00 and $FF), the
  primary slot register ($A8 = $F4) and page 3's secondary register too [XC 0-39].
- **Interrupts: an accepted call returns with interrupts ENABLED**, entered DI [XC 0-17, 24, 28, 29, 33-36] or EI
  [XC 25-27] — unlike a rejected one.

**The CPU really switches — timing** [M] (the S1990's system timer, ports $E6 / $E7, reset by OUT $E6, ticks of
3.911 µs as openMSX models it; and the emulated time between two `@cpusnap` breakpoints around the RAM loop; ranges
over both machines and every case of the mode):

| loop | Z80 | R800 ROM | R800 DRAM |
|---|---|---|---|
| 2000 × `dec de / ld a,d / or e / jr nz` in RAM (page 3) — timer ticks | 4290-4291 | 490-492 | 491-494 |
| the same, emulated µs between the snapshots | 16812-16813 | 1936-1938 | 1937-1950 |
| the same loop in the probe cartridge (slot 1, page 1) — ticks | 4290-4291 | 1706-1708 | 1706-1708 |
| 200 × CALL GETCPU (page-0 ROM code) — ticks | 1945-1946 | 924-926 | 971-973 |

The R800 runs the RAM loop 8.7× faster than the Z80, and the external cartridge's code 2.5× faster [M]. On these
page-0 calls DRAM mode is NOT faster than ROM mode in openMSX (GETCPU 5 % slower; KILBUF the same, on
[GETCPU](GETCPU.md)) [M]; why, and whether real hardware agrees [A].

**The boot** [M]: at cartridge INIT (t ≈ 4.9 s) the CPU is the Z80: R#6 $60, $FCB1 $02, port $A7 $00, GETCPU 00
[XC INIT] [XB]. The S1990's register 6 during the boot (polled each 0.1 s) goes $60 (from 0.1 s) → $40 (0.6-0.7 s) →
$60 (1.9 s) → $00 at 13.2 s (FS-A1GT) / 11.4 s (FS-A1ST); at 25 s the machine is in R800 DRAM mode with $FCB1 = $80
[XB]. So the boot itself switches to the R800 and back before the cartridge INITs, and ends in R800 DRAM mode with the
LED bit set and bit 1 clear.

**What CHGCPU does that a register write does not** [M, mechanism A]: writing the S1990's register 6 directly
(OUT $E4,6 / OUT $E5,$60) from the R800 hands control to a Z80 that does not continue after the OUT: in xgetcpu a later
CHGCPU($82) resumed the R800 right after the OUT where the direct write had stopped it, and the probe ran its last
case a second time ([GETCPU](GETCPU.md), the run-on record). The turbo R's two CPUs each keep their own registers;
CHGCPU passes the stack pointer across (in $FFFD, by MAP's description) and the call returns normally on the new CPU
[XC 0-17]. The exact hand-over is not observable without reading ROM [A].

## Differences

**FS-A1GT vs FS-A1ST:** none in any measured output of the 40 cases — registers, flags, interrupt state, port writes,
S1990 registers, $FCB1, $FFFD, work-area changes, GETCPU, active CPU — beyond interrupt-timing cells and ±2 timer ticks
[XC 0-39]. The boot switches to R800 DRAM later on the FS-A1GT (13.2 s vs 11.4 s) [XB].

**C-BIOS / zerobas:** no turbo R build; nothing to compare.

## Open (not measured)

- The memory side of DRAM mode: which RAM holds the ROM copy, what the memory mapper ($FC-$FF) shows, whether the
  copy is write-protected, and how much RAM a program loses.
- A values not run (the accept rule "A AND $7F in 0-2" is measured on the 17 values above only).
- $FFFD with another caller SP; a stack in pages 0-2; CHGCPU called from code in page 0-2 or from another slot.
- CHGCPU's own duration and stack depth; whether interrupts are taken during the switch; the pause key and port $A7
  bit 0.
- The LED itself (openMSX's LED state was not read; only the OUT to $A7 and $FCB1).
- Real-hardware timing (all timing above is openMSX's model).
- The MSX Turbo-R Technical Handbook's text for CHGCPU (not read; the interface line is MAP's).

## Related pages

[turbo R index](../index.md); [GETCPU](GETCPU.md); [spec method](../../spec-method.md).

## Tests that cover it

None yet.
