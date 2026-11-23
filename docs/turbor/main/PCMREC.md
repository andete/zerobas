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
> ([scratchpad/AE_xpcmrec_tr_decoded.out](../../../scratchpad/AE_xpcmrec_tr_decoded.out)); the goldfish pass's cases:
> [xpcmrec2.asm](../../../probes/bios/spec/xpcmrec2.asm), [scratchpad/AE_xpcmrec2_tr.out](../../../scratchpad/AE_xpcmrec2_tr.out)
> ([decoded](../../../scratchpad/AE_xpcmrec2_tr_decoded.out) with `--entryf`). All timing is openMSX's model.
> Goldfish pass 1 (test writer) 2026-11-23: 8 findings, 3 measured, 2 moved to open.
> **With a known input** (2026-11-23, tr6): WAV files fed into the PCM input through openMSX's `wavinput`
> (biosl_run's `@wavin`; the files built by [scratchpad/xpcmwav_mk.py](../../../scratchpad/xpcmwav_mk.py), never
> committed): probes [xpcmwav.inc](../../../probes/bios/spec/xpcmwav.inc) + xpcmwavsq / st / bu / ru / rd / gp / ll,
> all decoded in [scratchpad/AE_xpcmwav_decoded.out](../../../scratchpad/AE_xpcmwav_decoded.out) by
> [xpcmwav_decode.py](../../../scratchpad/xpcmwav_decode.py) — the section "With a known input" below.

Main-ROM entry, turbo R only. Listed by MAP's "MSX turbo R BIOS Entries" ([index](../index.md)); C-BIOS has no
turbo R build.

## Summary

`PCMREC` converts the PCM input one sample at a time — eight writes to port $A4 per sample, a successive
approximation — and stores one byte per sample from HL on, in RAM or VRAM. With no input, every sample reads $80, so
a recording fills the area with $80. Rate code 0 (A bits 1-0 = 0) is accepted only in R800 DRAM mode: in R800 ROM
mode, and from the Z80 (which the call switches to R800 ROM mode), it is refused with A = 1 and carry set, nothing
written. STOP (with or without CTRL) ends it with A = 2 and carry set, in every CPU mode, into RAM or VRAM. With a threshold (A bits 6-3) or the compression bit (A bit 2) and
this silent input, the call never returns unless STOP is pressed. Every register is changed; it returns with
interrupts enabled. With a real input (below): a sample is stored as offset binary (input / 256 + $80), $00 stored as $01; a
threshold t starts the recording at the first sample with |sample − $80| ≥ 8t; compression stores a run of n
samples of exactly $80 as the two bytes $00, n ($00, $00 = 256), a single one as $80.

## The specification

**Interface** [P MAP]: input `A = v t t t t c x x` (v = VRAM; tttt = "threshold"; c = "zero-data compression"; xx = "quality parameter (speed: 0 = fast)"), HL / BC / D / E as for PCMPLY. Output: carry set when aborted with CTRL-STOP. Registers: all.

**Evidence.** `[XR n]` = case n of xpcmrec (26 cases): per case CHGCPU to the start mode, the buffer $8000-$80FF
:= $5A, the VDP interrupt off, the keyboard matrix set through `@keyset` (none, CTRL+STOP, STOP, CTRL — held from
before the call to after it), every register loaded (A, HL, BC, D, E per case, F $00, the rest distinct garbage),
CALL $0189; then every register, the interrupt state, R#6, IN $A4 / $A5, the buffer's first 48 bytes, VRAM
$04000-$0403F (the `@vram` span), every OUT to $A4, $A5, $E4, $E5, $A7 during the call (counts; the first 64 / 16 /
8 bytes), the emulated time across the call. `[XT n]` = xpcmthr case n (case 0 a control, case 1 a threshold).
D = E = 0 and F = $00 on entry in every case of xpcmrec. `[XR2 n]` = case n of xpcmrec2 (13 cases, the same code and
record plus the entry F per case: STOP from the Z80, R800 ROM mode and into VRAM; entry F $FF / $28 / $44; D = E =
$FE).

**What a recording does** (R800 DRAM mode, A = 0-3) [M]:
- **Per sample, eight OUTs to $A4**: `C0 A0 90 88 84 82 81 80` — a successive approximation, one bit per write from
  bit 6 down, ending on the result [XR 0-8]. With nothing plugged in, no tested bit is kept and the result is $80 for
  every sample. That the comparator is read on port $A5 bit 7 is [A] (IN $A5 reads $83 after the call [XR]; before
  a call only xpcmply read it, also $83 — [PCMPLY](PCMPLY.md)).
- **Port $A5**: OUT $A5,$0C first, then two OUTs per conversion — `18 08` for the first four, `1C 0C` after — and
  OUT $A5,$03 last [XR 0-8, 12]. What the bits mean [A].
- **Five extra conversions, split 4 + 1**: a length of n makes n + 5 conversions (OUT $A4: 2 + 8 × (n + 5) — 50 for
  n = 1, 170 for 16, 426 for 48) and stores n bytes [XR 0-8, 12]. The $A5 log splits them: four conversions with
  `18 08`, then n + 1 with `1C 0C` (n = 1: 4 + 2 [XR 12]; n = 16: 4 + 17 [XR 0]), and a STOP held at entry ends after
  exactly the four `18 08` ones [XR 18]. So four conversions come before any storing kind, and one of the n + 1 is not
  stored [M]; which one (the first or the last) needs a real input [A] — the stored bytes are all $80 either way.
- **Stored**: n bytes of $80 from HL; the byte after the area keeps its $5A [XR 0-7, 12]. VRAM (A bit 7 = 1, HL =
  $4000, E = 0): VRAM $04000-$0400F := $80, $04010 on keeps its $5A [XR 8]. D = E = $FE in RAM records the same 16
  bytes [XR2 11]; D and E with VRAM were not run.
- **Return**: A = 0, F = $44 (Z, P/V; carry clear) plus **bits 5 and 3 of the entry F**: entry F $00, $44 → $44,
  $28, $FF → $6C [XR 0-8, XR2 6-8, 12]; HL = HL + BC (VRAM: $4010), BC = 0; **D = 0, E kept** (D = E = $FE in RAM
  returns DE = $00FE [XR2 11]; with D = E = 0 that read as DE = 0 [XR 0-8]);
  IX = $7000, IY = $0000 (A = 0-3) / $0100 (A = $80); AF' = $0044, BC' = $F400, DE' = $F300, HL' = $FCC5 (as PCMPLY);
  **interrupts enabled** [XR 0-8, 11-17]. Slots as on entry ($A8 $F4, page 3's secondary $00) [XR].

**The rate code and the CPU** [M]:
- **Rate code 0 is refused outside R800 DRAM mode**: in R800 ROM mode and from the Z80, A = $00 returns at once with
  A = 1, F = $01 (carry set), HL and BC as on entry, nothing stored (the buffer keeps its $5A), IX = $7042; the only
  OUTs are $A4 $80, $80 and $A5 $0C, $03 [XR 9, 10]. Z80 with A = $04 (rate code 0, c = 1) and CTRL+STOP held: the
  same refusal, A = 1 — so the rate-code refusal comes before STOP's A = 2 [XR 24]. In
  DRAM mode rate code 0 records [XR 0, 4]. Rate codes 1-3 record in R800 ROM mode [XR 13-15] and from the Z80 [XR 11,
  16, 17].
- **From the Z80 the call records in R800 ROM mode**, as PCMPLY plays: OUT $E5 = $40, $60, $60, OUT $A7 = $00, $02
  (four OUT $E4,6 when it refuses rate code 0, three otherwise), and it returns in the Z80 [XR 9, 11, 16, 17, 24].
  In the R800 modes: one or two OUT $E4,6 (two for rate code 0), no OUT to $E5 or $A7, R#6 unchanged [XR 0-8, 10,
  12-15].
- **Time per sample** (R800 DRAM, (48 − 16 samples) / 32, FS-A1GT / FS-A1ST): rate code 0 111.9 / 111.5 µs, 1 95.8 /
  95.5, 2 105.6 / 111.4, 3 58.2 / 58.5 [XR 0-7]; a first run (not kept) gave 69 µs for rate code 3. So with this idle
  input the rate code does NOT set the recording rate the way it sets PCMPLY's (63.6 × 1-4 µs), and the figures move
  between runs [M]; why [A]. The control case of xpcmthr (R800 DRAM, rate code 0, 16) records like [XR 0]: 2682 / 2702
  µs, 16 × $80, the same OUTs [XT 0]. From the Z80 there is one length per rate code, so no per-sample figure: rate
  code 1, 16 bytes 3752 / 3881 µs [XR 16]; 2, 16 bytes 4470 / 4174 [XR 17]; 3, 48 bytes 10078 / 8873 [XR 11]. 16
  samples in R800 ROM mode: rate code 1 3437 / 3435 µs, 2 3850 / 3537, 3 4004 / 3499
  [XR 13-15]; in DRAM mode 2447 / 2449, 2706 / 2706, 1949 / 1948 [XR 1-3].

**Threshold and compression with a silent input** [M]:
- A bit 2 (c = 1, "zero-data compression"), no key: the call did not return within 115 s of emulated time [XR 25].
- A = $08 (threshold 1), no key: did not return within 55 s [XT 1]. With MAP's description, a recording that waits
  for the input to cross a threshold, or that stores silence in a compressed form and ends only on a full area, would
  not end on silence [A].
- With CTRL+STOP held, c = 1 [XR 21], threshold 1 [XR 22] and threshold 15 (A = $78) [XR 23] abort like a plain
  recording (below); IY = $0008 / $0078 then.

**STOP** [M]: STOP held at entry, with or without CTRL: four conversions (OUT $A4: 2 + 4 × 8 = 34), nothing stored
(the buffer keeps its $5A), A = 2, F = $45 (carry set; $6D for entry F $FF and $28 — bits 5 and 3 as on a normal
return [XR2 9, 10]), HL and BC as on entry, interrupts enabled — in R800 DRAM mode [XR 18, 19, 21-23], from the Z80
and from R800 ROM mode at rate code 1, CTRL+STOP and STOP alone each [XR2 0-3], and into VRAM ($04000 keeps its $5A)
from R800 DRAM mode and from the Z80 [XR2 4, 5]. From the Z80 the call still switches to R800 ROM mode and back
(OUT $E5 $40, $60, $60; OUT $A7 $00, $02) [XR2 0, 1, 5].
CTRL alone changes nothing (a full recording) [XR 20]. STOP pressed in the middle of a recording was not run (the
harness's `@matrix` presses once per run; PCMPLY's run used it — [xpcmmid.asm](../../../probes/bios/spec/xpcmmid.asm)).

## With a known input (openMSX `wavinput`)

**Set-up** [M]: biosl_run's `@wavin PATH` plugs openMSX's `wavinput` into the turbo R's `pcminput` connector with
`audio-inputfilename` = PATH on both machines before boot; openMSX plays the file once from that moment. Every file:
mono, 16-bit, 44.1 kHz, 60 s. All cases in R800 DRAM mode (so every rate code records), entered DI with D = E = 0, F
$00; `[W? n]` = case n of xpcmwav?: sq = a 1 kHz square at ±16384, st = a staircase of 32 levels 2048 apart (10 ms
each), bu = 5 ms bursts of the square every 500 ms in silence, ru / rd = a ramp up / down from 0 by 256 per 2 ms,
gp = 1 ms marks at distinct levels separated by silences of 0.1 .. 130 ms, ll = small levels ($82 .. $70) between
marks. Both models give the same bytes in every case (up to where in the input a call starts) [M].

- **Return**: as with the silent input — A = 0, F = $44, HL = HL + BC, BC = 0, DE = 0, interrupts enabled — in every
  case that returns [W* all].
- **The value stored** [M]: 128 + input / 256, i.e. 8-bit offset binary: +16384 → $C0, −16384 → $40 [Wsq 0-3];
  the staircase gives $00 (−32768), $08, $10, ... $F8 (+30720), one plateau per level — except that **$00 is stored
  as $01** [Wst 0]. (Only multiples of 256 were fed: the rounding of the low byte is not measured.)
- **The sample period** [M] (from the square's level changes, every 500 µs): rate code 3 63.5 µs, 2 111.3 / 111.6,
  1 95.6 / 95.2, 0 111.6 µs (FS-A1GT / FS-A1ST) [Wsq 0-3]; the staircase: 157 samples per 10 ms (63.7 µs) at rate
  code 3 [Wst 0]. So with an input too the rate code does not give PCMPLY's four rates; the figures match the silent
  input's (above) [M].
- **Threshold** [M]: A bits 6-3 = t ≠ 0 waits, storing nothing, until a sample lies **8t or more from $80, either
  way**, and stores from that sample on: rising ramp t = 1, 2, 3, 4, 8, 15 → first byte $88, $90, $98, $A0, $C0,
  $F8 [Wru 0-5]; falling ramp → $78, $70, $68, $60, $40, $08 [Wrd 0-5]; after the start every sample is stored, also
  silence ($80) [Wbu 3]. A square of ±64 never reaches t = 15 (8 × 15 = 120): the call did not return in 40 s [Wsq
  6] — so a threshold the input never reaches is the "never returns" of the silent case.
- **Compression** (A bit 2) [M]: only samples of exactly **$80** count as silence: $82, $86, $87, $7A ... are stored
  as they are, with threshold 1 as well as without — the threshold does not widen what is compressed [Wll 0-3]. A run
  of n ≥ 2 such samples is stored as **two bytes $00, n** — n = 3, 8, 16, 31, 63, 126, 128, 134, 251 for silences
  the plain recording counts as 3, 8, 15-16, 31-32, 63, 125, 129, 134, 251 samples [Wgp 0, 1] — a run of 256 as $00,
  $00, and a longer run as several pairs: 258 samples → $00 $00 $00 $03 (A1ST) or $00 $00 then a raw $80 (A1GT), a 65 ms
  silence (~1020 samples) → $00 $00 $00 $00 $00 $00 $00 $F8 (3 × 256 + 248), ~0.82 s → 49 × ($00 $00) + $00 $EB [Wgp 1, 3]. **A single
  $80 is stored as $80** [Wgp 1, 2]. Since a stored $00 is always a code ($00 samples are stored as $01), the stream
  can be decoded unambiguously [A]. Rate code 1 compresses the same way (n counted in its own samples) [Wgp 2].
  **After a compressed run, the first 3-4 samples of the sound are not stored**: a 1 ms mark (15-16 samples plain)
  is stored as 11-13, a burst starting with eight $C0 as four [Wgp 1-3, Wbu 1, 2]; why [A]. With compression and
  no threshold a recording starts at once, with the silence it finds [Wbu 1, Wgp 3, Wll 3].
- **The area** is filled exactly: the byte after it keeps its $5A where no later case wrote there [Wsq 5, Wst 0,
  Wru 5, Wll 3].

## What cannot be measured here

A real input is now fed through `@wavin` (above). Still open with it: which comparator results keep a bit of the
approximation (the port log was not armed in the xpcmwav runs), which of the n + 1 storing conversions is not
stored (the input's timing against the call's start is not known to the sample), the rounding of inputs that are not
multiples of 256, compression into VRAM, a run longer than the area, and STOP during a compressed run. Also not run: D / E with VRAM, VRAM lengths above 64 KB,
lengths 0 and > 48, the work-area cells (not compared in this probe), real-hardware timing, and the MSX
Turbo-R Technical Handbook's text (not read; the interface line is MAP's).

## Differences

**FS-A1GT vs FS-A1ST:** none in any output of any case — registers, flags, interrupt state, port writes, stored bytes
— beyond timing (up to 500 µs per call in R800 ROM mode; 1.2 ms on [XR 11]) [XR, XT, XR2], and IN $A4 after the call,
which reads $00 or $03 on one model and the other in [XR 14] (and in two cases of a first xpcmrec2 run, not kept):
what reading the D/A port returns is not known [A], so it is not counted as an output.

**C-BIOS / zerobas:** no turbo R build; nothing to compare.

## Open (not measured)

See "What cannot be measured here" above, plus: STOP pressed during a recording; why rate code 0 needs DRAM mode
(only that it does, in openMSX); which of the n + 1 storing conversions is not stored; what IN $A4 reads; the Z80's
time per sample (two lengths at one rate code); why the first samples after a compressed run are lost.

## Related pages

[turbo R index](../index.md); [PCMPLY](PCMPLY.md); [CHGCPU](CHGCPU.md); [GETCPU](GETCPU.md).

## Tests that cover it

None yet.
