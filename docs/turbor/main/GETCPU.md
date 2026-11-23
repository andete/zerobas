<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `GETCPU` ($0183) — which CPU mode is the turbo R in?

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the Panasonic FS-A1GT and FS-A1ST (identical in every output but
> timing jitter; [xgetcpu.asm](../../../probes/bios/spec/xgetcpu.asm),
> [scratchpad/AE_xgetcpu_tr.out](../../../scratchpad/AE_xgetcpu_tr.out), decoded by
> [scratchpad/xgetcpu_decode.py](../../../scratchpad/xgetcpu_decode.py); GETCPU after every CHGCPU case:
> [xchgcpu.asm](../../../probes/bios/spec/xchgcpu.asm), [scratchpad/AE_xchgcpu_tr.out](../../../scratchpad/AE_xchgcpu_tr.out);
> at INIT: [xtrboot.asm](../../../probes/bios/spec/xtrboot.asm), [scratchpad/AE_xtrboot_tr.out](../../../scratchpad/AE_xtrboot_tr.out)).
> No goldfish pass yet.

Main-ROM entry, turbo R only. Listed by MAP's "MSX turbo R BIOS Entries" ([index](../index.md)); C-BIOS has no
turbo R build.

## Summary

`GETCPU` returns the current CPU mode in A: 0 = Z80, 1 = R800 ROM mode, 2 = R800 DRAM mode. The answer follows the
S1990's CPU register (the hardware), not CHGCPU's RAM copy at $FCB1. It changes only A and F, keeps the interrupt
state, and writes no RAM. Its flags differ by mode, and in the R800 modes two undocumented flag bits come from the
entry F.

## The specification

**Interface** [P MAP]: output A = `0 0 0 0 0 0 x x`, 00 Z80 (ROM) mode, 01 R800 ROM mode, 10 R800 DRAM mode;
registers: AF.

**Evidence.** `[XG n]` = case n of xgetcpu (18 table cases + 1 run-on record, below). Each case: CHGCPU(mode), DI,
optionally $FCB1 or the S1990's register 6 overwritten, every register loaded with a distinct value (A, F per case),
DI or EI, CALL $0183; then the registers, the IFF (read twice), R#6 and $FCB1, the work-area cells $F380-$FFFE that
changed, and two timed loops. `[XC n]` = xchgcpu, which calls GETCPU (entry A $5A) after each of its 40 CHGCPU cases;
`[XB]` = xtrboot, which calls it at cartridge INIT.

**Result** [M]:
- **A = 0 / 1 / 2 for the S1990's register 6 = $60 / $40 / $00** — set by CHGCPU($80 / $81 / $82) and by CHGCPU($00 /
  $01 / $02) [XG 0-11], and after every CHGCPU case [XC 0-39].
- **It reads the hardware, not $FCB1:** $FCB1 overwritten so that its bit 1 (the Z80 flag CHGCPU keeps there)
  contradicts the mode — $80 in the Z80, $02 in R800 ROM and in DRAM — leaves the answer 0 / 1 / 2, and $FF in the Z80
  leaves 0 [XG 12-15]; R#6 := $40 written directly while $FCB1 says Z80 ($7F) gives 1 [XG 16]; R#6 := $60 directly while $FCB1
  says R800 ($FD) gives 0 [XG 17]. "Reads R#6" and "asks which CPU is running" coincide on every case; ROM vs DRAM
  mode exists only in R#6 [M].
- **The entry A is not used:** $A7, $FF, $00 give the same answer [XG 0-11]; $5A too [XC].
- **F**, entry F $00 / $FF: Z80 $81 / $81 (S and C set); R800 ROM $01 / $29 (C set); R800 DRAM $00 / $28 [XG 0-11].
  So the documented bits are the same for both entry F values (Z80: S = 1, C = 1; R800 ROM: C = 1; DRAM: none set) and
  undocumented bits 5 and 3 are 0 in the Z80 mode but follow the entry F in the R800 modes (only $00 and $FF were
  entered) [M]. Whether that is the R800's flag behaviour or a different path through GETCPU [A].
- **Everything else is kept:** BC, DE, HL, IX, IY, AF', BC', DE', HL', the slot registers [XG 0-17]; the interrupt
  state (DI stays DI [XG 0-8, 12-17], EI stays EI [XG 9-11]).
- **No RAM is written:** no cell of $F380-$FFFE changes but the timer interrupt's (SCNCNT, JIFFY, $FCA2, in the EI
  cases) [XG 0-17]; R#6 and $FCB1 read the same after the call as before [XG 0-17].
- **At cartridge INIT** GETCPU returns 0, with R#6 $60 [XB].

**Time** [M] (200 × CALL in a loop, S1990 timer ticks of 3.911 µs, both machines):

| | Z80 | R800 ROM | R800 DRAM |
|---|---|---|---|
| 200 × GETCPU | 1945-1946 (≈ 38 µs a call) | 924-925 (≈ 18 µs) | 972-973 (≈ 19 µs) |
| 200 × KILBUF ($0156), for comparison | 1588-1589 | 651-652 | 650-652 |

GETCPU takes longer in DRAM mode than in ROM mode, KILBUF the same [M]; why [A].

**The run-on record** [M]: cases 16-17 switch the CPU by writing R#6 directly, bypassing CHGCPU. The run has a 19th
record [XG 18], a copy of case 17's inputs taken in R800 DRAM mode (R#6 $00 before the call, A = 2): the probe's
closing CHGCPU($82), entered on the Z80, handed control to an R800 that continued after case 17's OUT — where the
direct write had stopped it — instead of returning from the call; case 17 then ran again and the table's end came
round a second time. The two CPUs keep their own registers, and only CHGCPU hands the running program across
([CHGCPU](CHGCPU.md)) [M for the record; mechanism A].

## Differences

**FS-A1GT vs FS-A1ST:** none in any output of the 19 records (A, F, every register, IFF, R#6, $FCB1, work area),
the timing within 1-2 ticks [XG 0-18].

**C-BIOS / zerobas:** no turbo R build; nothing to compare.

## Open (not measured)

- R#6 values CHGCPU never writes ($20, $60 with other bits; a direct write to $00 bypassing CHGCPU was not run — it
  would need the DRAM copy prepared).
- Entry F values other than $00 / $FF for the R800 flag bits 5 / 3.
- Stack depth; real-hardware timing.
- The MSX Turbo-R Technical Handbook's text for GETCPU (not read; the interface line is MAP's).

## Related pages

[turbo R index](../index.md); [CHGCPU](CHGCPU.md); [spec method](../../spec-method.md).

## Tests that cover it

None yet.
