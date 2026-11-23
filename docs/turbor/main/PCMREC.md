<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `PCMREC` ($0189) — record through the PCM into a memory area

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the Panasonic FS-A1GT and FS-A1ST (identical in every output but
> timing jitter), in openMSX with NOTHING plugged into the PCM's input — every recorded byte below is what openMSX's
> idle input gives. Probes and runs: [xpcmrec.asm](../../../probes/bios/spec/xpcmrec.asm),
> [scratchpad/AE_xpcmrec_tr.out](../../../scratchpad/AE_xpcmrec_tr.out); a threshold with no key:
> [xpcmthr.asm](../../../probes/bios/spec/xpcmthr.asm), [scratchpad/AE_xpcmthr_tr.out](../../../scratchpad/AE_xpcmthr_tr.out);
> both decoded by [scratchpad/xpcmrec_decode.py](../../../scratchpad/xpcmrec_decode.py)
> ([scratchpad/AE_xpcmrec_tr_decoded.out](../../../scratchpad/AE_xpcmrec_tr_decoded.out)). All timing is openMSX's model.
> No goldfish pass yet.

Main-ROM entry, turbo R only. Listed by MAP's "MSX turbo R BIOS Entries" ([index](../index.md)); C-BIOS has no
turbo R build.

## Summary

`PCMREC` converts the PCM input one sample at a time — eight writes to port $A4 per sample, a successive
approximation — and stores one byte per sample from HL on, in RAM or VRAM. With no input, every sample reads $80, so
a recording fills the area with $80. Rate code 0 (A bits 1-0 = 0) is accepted only in R800 DRAM mode: in R800 ROM
mode, and from the Z80 (which the call switches to R800 ROM mode), it is refused with A = 1 and carry set, nothing
written. STOP ends it with A = 2 and carry set. With a threshold (A bits 6-3) or the compression bit (A bit 2) and
this silent input, the call never returns unless STOP is pressed. Every register is changed; it returns with
interrupts enabled.

## The specification

**Interface** [P MAP]: input `A = v t t t t c x x` (v = VRAM; tttt = "threshold"; c = "zero-data compression"; xx = "quality parameter (speed: 0 = fast)"), HL / BC / D / E as for PCMPLY. Output: carry set when aborted with CTRL-STOP. Registers: all.

**Evidence.** `[XR n]` = case n of xpcmrec (26 cases): per case CHGCPU to the start mode, the buffer $8000-$80FF
:= $5A, the VDP interrupt off, the keyboard matrix set through `@keyset` (none, CTRL+STOP, STOP, CTRL — held from
before the call to after it), every register loaded (A, HL, BC, D, E per case, F $00, the rest distinct garbage),
CALL $0189; then every register, the interrupt state, R#6, IN $A4 / $A5, the buffer's first 48 bytes, VRAM
$04000-$0403F (the `@vram` span), every OUT to $A4, $A5, $E4, $E5, $A7 during the call (counts; the first 64 / 16 /
8 bytes), the emulated time across the call. `[XT 1]` = xpcmthr case 1. D = E = 0 in every case.

**What a recording does** (R800 DRAM mode, A = 0-3) [M]:
- **Per sample, eight OUTs to $A4**: `C0 A0 90 88 84 82 81 80` — a successive approximation, one bit per write from
  bit 6 down, ending on the result [XR 0-8]. With nothing plugged in, no tested bit is kept and the result is $80 for
  every sample. That the comparator is read on port $A5 bit 7 (IN $A5 reads $83 before and after) is [A].
- **Port $A5**: OUT $A5,$0C first, then two OUTs per conversion — `18 08` for the first four, `1C 0C` after — and
  OUT $A5,$03 last [XR 0-8, 12]. What the bits mean [A].
- **Five extra conversions**: a length of n makes n + 5 conversions (OUT $A4: 2 + 8 × (n + 5) — 50 for n = 1, 170
  for 16, 426 for 48) and stores n bytes [XR 0-8, 12]. Whether the first five are discarded or the last [A]; the
  stored bytes are all $80 either way.
- **Stored**: n bytes of $80 from HL; the byte after the area keeps its $5A [XR 0-7, 12]. VRAM (A bit 7 = 1, HL =
  $4000, E = 0): VRAM $04000-$0400F := $80, $04010 on keeps its $5A [XR 8]. D and E as in [PCMPLY](PCMPLY.md) were
  not run.
- **Return**: A = 0, F = $44 (Z, P/V; carry clear) for entry F $00; HL = HL + BC (VRAM: $4010), BC = 0, DE = 0;
  IX = $7000, IY = $0000 (A = 0-3) / $0100 (A = $80); AF' = $0044, BC' = $F400, DE' = $F300, HL' = $FCC5 (as PCMPLY);
  **interrupts enabled** [XR 0-8, 11-17]. Slots as on entry ($A8 $F4, page 3's secondary $00) [XR].

**The rate code and the CPU** [M]:
- **Rate code 0 is refused outside R800 DRAM mode**: in R800 ROM mode and from the Z80, A = $00 returns at once with
  A = 1, F = $01 (carry set), HL and BC as on entry, nothing stored (the buffer keeps its $5A), IX = $7042; the only
  OUTs are $A4 $80, $80 and $A5 $0C, $03 [XR 9, 10]. Z80 with A = $04 (rate code 0, c = 1): the same [XR 24]. In
  DRAM mode rate code 0 records [XR 0, 4]. Rate codes 1-3 record in R800 ROM mode [XR 13-15] and from the Z80 [XR 11,
  16, 17].
- **From the Z80 the call records in R800 ROM mode**, as PCMPLY plays: OUT $E5 = $40, $60, $60, OUT $A7 = $00, $02
  (four OUT $E4,6 when it refuses rate code 0, three otherwise), and it returns in the Z80 [XR 9, 11, 16, 17, 24].
  In the R800 modes: one or two OUT $E4,6 (two for rate code 0), no OUT to $E5 or $A7, R#6 unchanged [XR 0-8, 10,
  12-15].
- **Time per sample** (R800 DRAM, (48 − 16 samples) / 32, FS-A1GT / FS-A1ST): rate code 0 111.9 / 111.5 µs, 1 95.8 /
  95.5, 2 105.6 / 111.4, 3 58.2 / 58.5 [XR 0-7]; a first run (not kept) gave 69 µs for rate code 3. So with this idle
  input the rate code does NOT set the recording rate the way it sets PCMPLY's (63.6 × 1-4 µs), and the figures move
  between runs [M]; why [A]. 16 samples in R800 ROM mode: rate code 1 3437 / 3435 µs, 2 3850 / 3537, 3 4004 / 3499
  [XR 13-15]; in DRAM mode 2447 / 2449, 2706 / 2706, 1949 / 1948 [XR 1-3].

**Threshold and compression with a silent input** [M]:
- A bit 2 (c = 1, "zero-data compression"), no key: the call did not return within 115 s of emulated time [XR 25].
- A = $08 (threshold 1), no key: did not return within 55 s [XT 1]. With MAP's description, a recording that waits
  for the input to cross a threshold, or that stores silence in a compressed form and ends only on a full area, would
  not end on silence [A].
- With CTRL+STOP held, c = 1 [XR 21], threshold 1 [XR 22] and threshold 15 (A = $78) [XR 23] abort like a plain
  recording (below); IY = $0008 / $0078 then.

**STOP** [M]: STOP held at entry, with or without CTRL: four conversions (OUT $A4: 2 + 4 × 8 = 34), nothing stored
(the buffer keeps its $5A), A = 2, F = $45 (carry set), HL and BC as on entry, interrupts enabled [XR 18, 19, 21-23].
CTRL alone changes nothing (a full recording) [XR 20]. STOP pressed in the middle of a recording was not run (the
harness's `@matrix` presses once per run; PCMPLY's run used it — [xpcmmid.asm](../../../probes/bios/spec/xpcmmid.asm)).

## What cannot be measured here

Everything that needs a real input signal: the bytes a sound records, when a threshold starts the recording, the
format of a compressed recording (c = 1 never ends on silence), which comparator results keep a bit of the
approximation. openMSX does have a pluggable wave-file input for the turbo R PCM (`wavinput` and the
`audio-inputfilename` setting, by the openMSX binary's own strings), but
[biosl_run.py](../../../probes/bios/biosl_run.py) has no directive to feed it a file; a later unit can add one
(`@plug` plugs a device but cannot name the file). Also not run: D / E in RAM and VRAM, VRAM lengths above 64 KB,
lengths 0 and > 48, entry F $FF, the work-area cells (not compared in this probe), real-hardware timing, and the MSX
Turbo-R Technical Handbook's text (not read; the interface line is MAP's).

## Differences

**FS-A1GT vs FS-A1ST:** none in any output of any case — registers, flags, interrupt state, port writes, stored bytes
— beyond timing (up to 500 µs per call in R800 ROM mode) [XR, XT].

**C-BIOS / zerobas:** no turbo R build; nothing to compare.

## Open (not measured)

See "What cannot be measured here" above, plus: STOP pressed during a recording; why rate code 0 needs DRAM mode
(only that it does, in openMSX).

## Related pages

[turbo R index](../index.md); [PCMPLY](PCMPLY.md); [CHGCPU](CHGCPU.md); [GETCPU](GETCPU.md).

## Tests that cover it

None yet.
