<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# The earlier generations' probes on the turbo R — first pass

**Measured 2026-11-23** (D-TRSPEC; the rule: nothing is assumed unchanged from an earlier generation). Every existing
BIOS probe — `probes/bios/spec/*.asm` (MSX1, MSX2 and MSX2+) and `probes/bios/biosl/*.asm`, 206 in all — was run on
both turbo R references with [`biosl_run.py --row turbor`](../../probes/bios/biosl_run.py) ("ref" = FS-A1GT,
"ours" = FS-A1ST), one file per probe in [scratchpad/AE_trall/](../../scratchpad/AE_trall/), by
[scratchpad/trall_run.py](../../scratchpad/trall_run.py) (each run in an isolated instance with empty clock-chip state).
[scratchpad/trall_cmp.py](../../scratchpad/trall_cmp.py) sets the A1GT's capture against the reading the page is based
on — the VG-8020's committed run for an MSX1 probe (the `disk` row, VG-8020 + NMS 1200, for a `; @disk` probe), the
FS-A1WSX's committed run for an MSX2 / MSX2+ probe — and, for an MSX1 probe, also against the FS-A1WSX's reading of
the same probe source ([scratchpad/AE_m1on2/](../../scratchpad/AE_m1on2/), D-MSX1ON2), so a difference the MSX2+
already has is told apart from one that is new on the turbo R. Each difference was then decoded by case and field from
the probe's header, case table and decoder: [disk / BDOS](../../scratchpad/trall-triage-disk.md),
[MSX1 non-disk](../../scratchpad/trall-triage-msx1.md), [MSX2 / MSX2+](../../scratchpad/trall-triage-msx2.md) — those
files carry the per-byte evidence for every line below.

Clean room: only captures (RAM the probes write, VRAM, I/O through the probes' own code) were read; no ROM byte.

## Verdicts

| class | n | meaning |
|---|---|---|
| SAME | 53 | byte-identical to the baseline (MSX1: the VG-8020 — and to the A1WSX; MSX2: the A1WSX). 3 of them (xva, xva2, xva14) have one A1GT-vs-A1ST byte, a log slot no case writes |
| AS-MSX2+ | 44 | differs from the VG-8020 exactly as the FS-A1WSX does: the MSX1 page's "On later generations" MSX2+ column holds on the turbo R |
| AS-MSX2+ + non-behaviour bytes | 30 | as the A1WSX in every call result; the rest is power-on RAM, the clock chip's time of day (FMAKE / FCLOSE stamps) or work-area addresses (the turbo R's disk work area sits elsewhere) |
| CONFIG | 17 | the machine, not the call: PSG R14 bit 7 (no cassette input) reads 0, slot 0's secondary register $00, TRGFLG's boot value $89, $FFF8 / $FFFD-$FFFE, R#36, the BASIC banner |
| TIMING / CLOCK | 21 | VDP S#2 read at a random moment, JIFFY / INTCNT / SCNCNT, a key scan inside the case or not, PSG-log timestamps, the RTC's time of day, a calibrated loop |
| POWER-ON | 16 | only cells no case writes (the capture's last byte, unused log slots): the turbo R's power-on RAM pattern |
| **NEW-TR** | 21 | the turbo R's BIOS / I/O behaves differently — listed below (18 in the first pass; xtap1, xtap5 and b7tape since `@tape` runs without a cassette port, below) |
| APPARATUS | 1 | xva13 needs a 64 KB-VRAM machine config ([scratchpad/xva13_run.py](../../scratchpad/xva13_run.py)); run on the stock 128 KB turbo Rs it says nothing |
| turbo R probe | 3 | xchgcpu / xgetcpu / xtrboot are this generation's own ([CHGCPU](main/CHGCPU.md), [GETCPU](main/GETCPU.md)) |

**`@tape` without a cassette port** (2026-11-23, tr4): in the first pass xtap1 / xtap5 / b7tape gave no reading — the
harness started the machine with `cassetteplayer new`, the turbo R has no cassette player, the Tcl script stopped there
and openMSX ran into biosl_run.py's 600 s timeout. [biosl_run.py](../../probes/bios/biosl_run.py)'s `@tape` now catches
that: nothing is recorded or played, TAPEREADY is acknowledged with 2 (the probes wait for non-zero), and the output
says `TAPE ref/ours: no cassette port (There is no cassetteplayer available.)`. On a machine with a port nothing
changes: xtap1 on the `nodisk` row gives a byte-identical output with the old and the new harness
([AE_xtap1_tapefix_nodisk.out](../../scratchpad/AE_xtap1_tapefix_nodisk.out); its VG-8020 capture equals
XTAP1_run2.out's). The three probes were then re-run on the turbo R row (item 6).

**Re-checked with the pages' own rules** (2026-11-23, tr4): every MSX1 finding below was re-decoded by running the
page's executable rules (`probes/bios/spec/*_rules.py`) on the turbo R capture in the reference's place, and on the
FS-A1WSX's capture of the same probe source, by [scratchpad/trnew_recheck.py](../../scratchpad/trnew_recheck.py)
([AE_trnew_recheck.out](../../scratchpad/AE_trnew_recheck.out): per rule, the cases that fail on the A1GT, the A1ST and
the A1WSX, then every decoded field that differs); the MSX2 findings were re-decoded from the run files by the probes'
record layouts (xf4port, xrdres's 32-byte records, xsubpad_body.inc's 16-byte records, the CHKSLZ VRAM log). All 18
are confirmed; two first-pass details were corrected (items 5 and 7). Each finding is now on its call's page, in an
"On the turbo R" bullet or section.

**A1GT vs A1ST:** they agree on every behavioural byte except two: CHKSLZ (below) and one DSKRST case (below). Every
other disagreement between the two is power-on RAM, timing, the clock's seconds, a boot leftover (BUF holds "512" on the
A1GT, "256" on the A1ST), the disk work area's position (5 bytes lower on the A1GT) or the BASIC banner ("MSX BASIC
version 4.1" on the A1GT, "4.0" on the A1ST).

## What is new on the turbo R

1. **Port $F4 / RDRES / WRRES have the opposite sense to the FS-A1WSX** ([RDRES](../msx2/main/RDRES.md),
   [WRRES](../msx2/main/WRRES.md); [xf4port.out](../../scratchpad/AE_trall/xf4port.out),
   [xrdres.out](../../scratchpad/AE_trall/xrdres.out)). Port $F4 reads bit 7 = the bit written, bit 5 = 1, the rest 0
   ($A0 / $20; the A1WSX: $FF / $7F; at INIT $A0 vs the A1WSX's $7F). RDRES returns A = the port as read, F unchanged;
   WRRES sets port bit 7 := A's bit 7 and keeps A / F (the A1WSX: bit 7 := NOT A's bit 7, A / F change). Both models.
2. **A soft reset through $0000 never gets back to the cartridge** ([RDRES](../msx2/main/RDRES.md) RR-7,
   [WRRES](../msx2/main/WRRES.md) WR-3; [xf4reset.out](../../scratchpad/AE_trall/xf4reset.out)): no reading on either
   model; the capture, JIFFY, SCNCNT and NEWKEY read $FF at the 120 s dump. **Explained (tr6, a VRAM-log probe:
   [xtrreset0](../../probes/bios/spec/xtrreset0.asm) / [xtrreset1](../../probes/bios/spec/xtrreset1.asm),
   [AE_xtrreset0_tr.out](../../scratchpad/AE_xtrreset0_tr.out), [AE_xtrreset1_tr.out](../../scratchpad/AE_xtrreset1_tr.out)):
   port $F4 bit 7 decides it.** With bit 7 = 1 JP $0000 boots again into the cartridge (51 frames), VRAM not cleared;
   with bit 7 = 0 -- xf4reset's first step -- it never comes back: both models stop with interrupts off, the A1GT with
   every page on slot 0-0 (hence the $FF reads), the A1ST at another PC. Both models alike.
3. **CHKSLZ: the FS-A1GT never returns** ([CHKSLZ](../msx2/main/CHKSLZ.md);
   [xchkslz0.out](../../scratchpad/AE_trall/xchkslz0.out), [xchkslzd.out](../../scratchpad/AE_trall/xchkslzd.out),
   reproduced in [rerun/xchkslz0.out](../../scratchpad/AE_trall/rerun/xchkslz0.out)): its VRAM log holds only 'B'
   (before the call), no 'R', no re-entry of our INIT; the FS-A1ST, like the FS-A1WSX, re-boots and enters our INIT
   twice. The only model-dependent call behaviour found in the MSX2 probes.
4. **NEWPAD / GTPAD functions 0-11 (touch pad, light pen) do nothing** ([NEWPAD](../msx2/sub/NEWPAD.md),
   [GTPAD](../bios/GTPAD.md); [xsubpad.out](../../scratchpad/AE_trall/xsubpad.out), xsubpadb / xsubpadm / xsubpadx /
   xsubpads): A = $00, F = $44, BC / DE / HL as entered, on both models; the A1WSX computes values. Functions 12 and up
   (mouse, track ball) are as on the A1WSX. Through GTPAD with A = 1 / 2 entered under DI, the turbo R returns with
   interrupts ON (the A1WSX keeps them off), and DE / HL hold other working values (E $00 not $68, HL $2400)
   ([xinp1.out](../../scratchpad/AE_trall/xinp1.out)).
5. **GTPDL does nothing** ([GTPDL](../bios/GTPDL.md); [xinp1.out](../../scratchpad/AE_trall/xinp1.out) cases 60-63):
   A $00, F $44, every register kept, PSG R15 not written, DI kept. The VG-8020 and the A1WSX return A $FF, write R15's
   port bit and enable interrupts: R-PD-A, R-PD-PORT and R-PD-EI fail on the turbo R; R-PD-KEEP holds except for
   R14 ($7F: no cassette input — the machine; the A1WSX's $FF fails it the same way). (First pass: "R-PD-KEEP holds".)
6. **The cassette entries are stubs** ([STMOTR](../bios/STMOTR.md), [TAPOON](../bios/TAPOON.md),
   [TAPOOF](../bios/TAPOOF.md), [TAPIOF](../bios/TAPIOF.md), [TAPION](../bios/TAPION.md), [TAPIN](../bios/TAPIN.md),
   [TAPOUT](../bios/TAPOUT.md); [xtap1.out](../../scratchpad/AE_trall/xtap1.out),
   [xtap2.out](../../scratchpad/AE_trall/xtap2.out), [xtap3.out](../../scratchpad/AE_trall/xtap3.out),
   [xtap4.out](../../scratchpad/AE_trall/xtap4.out), [xtap5.out](../../scratchpad/AE_trall/xtap5.out),
   [b7tape.out](../../scratchpad/AE_trall/b7tape.out); step by step beside the VG-8020 and the A1WSX:
   [AE_trtap_decoded.out](../../scratchpad/AE_trtap_decoded.out) by
   [trtap_decode.py](../../scratchpad/trtap_decode.py)): STMOTR returns A / F as entered and never moves port C's
   motor bit; TAPOON / TAPOOF / TAPIOF return with the carry set, A / BC / DE / HL and port C kept, the interrupt state
   kept (the A1WSX enables them after TAPOOF / TAPIOF, disables them in TAPOON). The `@tape` probes (no cassette port,
   nothing played) add: **TAPION** returns with the carry set, A / BC / DE / HL as entered, port C as found (no motor,
   the key-row nibble not set to 7), the interrupt state kept; **TAPOUT** and **TAPIN** return with the carry set and A
   as entered on every call — no byte written or read; F is the entry F with the carry set ($00 → $01, $FF → $ED, $09
   kept); b7tape's round trip gets the carry on all four kinds of call and no byte back. Both models alike. The rules
   that fail: R-SM-MOTOR / R-SM-AF, R-TN-OK / MOTOR / PORT, R-TO-*, R-TI-*, R-TA-OK / MOTOR / PORT, R-TP-A, R-TU-OK;
   R-SM-KEEP and R-TN-DE hold. Whether TAPOON writes a leader cannot be measured: there is no port to hear it.
7. **The function-key line at out-of-range widths** ([INITXT](../bios/INITXT.md) R-I-W0 / R-I-KEYEDGE / R-I-EDGE4,
   [INIT32](../bios/INIT32.md); [xinit.out](../../scratchpad/AE_trall/xinit.out),
   [xinit4.out](../../scratchpad/AE_trall/xinit4.out)): INIT32 at width 255 with the key line on draws "key0" only —
   every earlier machine also draws "key1" at column 34 (name-table sum $5849, A1WSX $6AD1); INITXT at width 255 keeps
   the cells read but its whole-VRAM sum is $1288 lower, the same deficit (XJ4 18; cause not separated); at width 0 with
   the key line on the **name-table** sum differs from the A1WSX's (INITXT $6595 / $6683, INIT32 $5290 / $59BC). The
   pattern sums agree (first pass: "name / pattern sums differ" — a misread offset; the decoder reads patsum equal).
   In-range widths are identical.
8. **BEEP leaves C = $29** instead of $D0 ([BEEP](../bios/BEEP.md); [xsnd1.out](../../scratchpad/AE_trall/xsnd1.out),
   [xsnd1b.out](../../scratchpad/AE_trall/xsnd1b.out)). An unpublished register.
9. **DSKRST after SELDSK 1 returns with interrupts OFF on the FS-A1GT**, ON on the FS-A1ST and the A1WSX
   ([SYSTEM](../bdos/SYSTEM.md); [xbsys2.out](../../scratchpad/AE_trall/xbsys2.out) case 14, reproduced in
   [rerun/xbsys2.out](../../scratchpad/AE_trall/rerun/xbsys2.out) and a third time in
   [rerun/xbsys2_tr4.out](../../scratchpad/AE_trall/rerun/xbsys2_tr4.out)); with drive A current (xbsys1 case 12) all
   three return with interrupts on. One case, model-dependent. **Narrowed down (tr6,
   [AE_xtrdsk_decoded.out](../../scratchpad/AE_xtrdsk_decoded.out)): the DI is real at the return (the debugger's IFF
   at the instruction after CALL BDOS, xbsys2's code byte for byte: [xtrdsk2e](../../probes/bios/spec/xtrdsk2e.asm)),
   but nothing that moves the code reproduces it** -- the same calls in another frame, drive B / A / C, repeats, EI
   entry, waits, the R800 modes, a 2400-step frame-phase sweep: EI on both models every time. A timing coincidence
   of that run, not a rule; the disk-rotation phase is the untested candidate ([SYSTEM](../bdos/SYSTEM.md)).

The turbo R's disk ROM matches the FS-A1WSX in every measured disk-ROM entry
and BDOS call result, on both models — interrupts left on, IY $0314 after BDOS, MTOFF's A = 4, past-the-end answers
$0C / F $55, FMAKE's date stamp — see [trall-triage-disk.md](../../scratchpad/trall-triage-disk.md).

## Where each finding is on its call's page

Done 2026-11-23 (tr4): an "On the turbo R" bullet (MSX1 pages: under "On later generations"; MSX2 pages: a section
before "Open"), [M], citing the AE_trall run file and, for the MSX1 pages, the rules re-check:
[GTPDL](../bios/GTPDL.md), [GTPAD](../bios/GTPAD.md), [STMOTR](../bios/STMOTR.md), [TAPOON](../bios/TAPOON.md),
[TAPOOF](../bios/TAPOOF.md), [TAPIOF](../bios/TAPIOF.md), [TAPION](../bios/TAPION.md), [TAPIN](../bios/TAPIN.md),
[TAPOUT](../bios/TAPOUT.md), [INITXT](../bios/INITXT.md), [INIT32](../bios/INIT32.md), [BEEP](../bios/BEEP.md),
[SYSTEM](../bdos/SYSTEM.md), [RDRES](../msx2/main/RDRES.md), [WRRES](../msx2/main/WRRES.md),
[CHKSLZ](../msx2/main/CHKSLZ.md), [NEWPAD](../msx2/sub/NEWPAD.md).

Done 2026-11-23 (tr5), from the run files and the triage files above, nothing re-run: **every other verdict is now on
its call's page** — one "On the turbo R" line, [M], citing the AE_trall files (MSX1 / disk / BDOS pages: a paragraph
at the end of "On later generations"; MSX2 / MSX2+ pages: an "On the turbo R" section before "Open"), with the
verdict's caveat where one applies (the machine's cells, timing, the clock's time of day, power-on RAM). 171 pages:
96 under docs/bios, docs/bdos and docs/disk, 75 under docs/msx2. That includes the pages served by xinp1 (BREAKX,
CHGCAP, CKCNTC, GTSTCK, GTTRIG, ISCNTC, KILBUF, SNSMAT) and xsnd1 (CHGSND, GETVC2, GETVCP, GICINI, LFTQ, PUTQ, RDPSG,
STRTMS, WRTPSG): those probes are NEW-TR for GTPAD / GTPDL and for BEEP's C only, and the other calls they serve read as
on the A1WSX apart from the machine's R14 bit 7 and the key-row timing. Not given a line: the overview pages
([bios/shared-state.md](../bios/shared-state.md): b2vdp, b3int, b5sound, b6slots; [msx2/main/README.md](../msx2/main/README.md):
xva; the docs/msx2/concepts pages); b4input and b8save, which no page cites; INITXT (b1text, xinit3), SYSTEM and
NEWPAD (xsubpadg), whose pages already carry a turbo R section; xva13 (APPARATUS).

Still to do:
- ~~SYSTEM (DSKRST)~~ narrowed down and recorded on [SYSTEM](../bdos/SYSTEM.md) (tr6); ~~xf4reset~~ answered by
  xtrreset0 / 1 on [RDRES](../msx2/main/RDRES.md) / [WRRES](../msx2/main/WRRES.md) (tr6).
- **Machine facts** for the pages that print them (CONFIG rows): PSG R14 bit 7 = 0, slot 0 expanded with secondary
  register $00, TRGFLG $89 at boot, $FFFD-$FFFE = $F054 (CHGCPU's temporary SP), BUF's boot leftover.

Comparison caveats: 26 disk-probe VG-8020 baselines and several MSX1 ones are older than their probe source
(`trall_cmp.py` flags "probe newer than baseline"); for those the A1WSX column (same source, run the same day) is the
reliable one. xdent5 / xdent6 (drive A deliberately empty, no `; @disk`) are set against the diskless VG-8020 row by
`m1on2_cmp.py`'s rule; their right baseline is the `disk` row of XDENT5_run1.out / XDENT6_run1.out (against which the
A1GT differs only where the A1WSX does). Times of day come from the host clock: a rule that pins a time must compare
against GTIME.

## All probes

| probe | gen | baseline | turbo R (A1GT) vs baseline (bytes) | vs A1WSX (bytes) | A1GT vs A1ST (bytes) | class | run |
|---|---|---|---|---|---|---|---|
| b1text | MSX1 | AE_cbios_review_d23.out | DIFFERS (4) | 0 | 0 | AS-MSX2+ | [b1text.out](../../scratchpad/AE_trall/b1text.out) |
| b2vdp | MSX1 | AE_cbios_review_d23.out | DIFFERS (7) | 0 | 0 | AS-MSX2+ | [b2vdp.out](../../scratchpad/AE_trall/b2vdp.out) |
| b3int | MSX1 | AE_cbios_review_d23.out | SAME | 0 | 0 | SAME | [b3int.out](../../scratchpad/AE_trall/b3int.out) |
| b4input | MSX1 | AE_cbios_review_d23.out | SAME | 0 | 0 | SAME | [b4input.out](../../scratchpad/AE_trall/b4input.out) |
| b5sound | MSX1 | AE_cbios_review_d23.out | DIFFERS (2) | 1 | 0 | CONFIG | [b5sound.out](../../scratchpad/AE_trall/b5sound.out) |
| b6slots | MSX1 | AE_cbios_review_d23.out | DIFFERS (2) | 0 | 0 | AS-MSX2+ | [b6slots.out](../../scratchpad/AE_trall/b6slots.out) |
| b7tape | MSX1 | AE_cbios_review_d23.out | DIFFERS (20) | 20 | 0 | **NEW-TR** (@tape, no cassette port) | [b7tape.out](../../scratchpad/AE_trall/b7tape.out) |
| b8save | MSX1 | AE_cbios_review_d23.out | SAME | 0 | 0 | SAME | [b8save.out](../../scratchpad/AE_trall/b8save.out) |
| xbabs1 | MSX1 | XBABS1_run0_past.out | DIFFERS (152) | 160 | 152 | AS-MSX2+ + POWER-ON / CLOCK | [xbabs1.out](../../scratchpad/AE_trall/xbabs1.out) |
| xbabs2 | MSX1 | XBABS2_run1.out | DIFFERS (228) | 240 | 228 | AS-MSX2+ + POWER-ON / CLOCK | [xbabs2.out](../../scratchpad/AE_trall/xbabs2.out) |
| xbblk1 | MSX1 | XBBLK1_run1.out | DIFFERS (68) | 51 | 33 | AS-MSX2+ + POWER-ON / CLOCK | [xbblk1.out](../../scratchpad/AE_trall/xbblk1.out) |
| xbblk10 | MSX1 | XBBLK10_run1.out | DIFFERS (87) | 54 | 22 | AS-MSX2+ + POWER-ON / CLOCK | [xbblk10.out](../../scratchpad/AE_trall/xbblk10.out) |
| xbblk11 | MSX1 | XBBLK11_run1.out | DIFFERS (79) | 52 | 19 | AS-MSX2+ + POWER-ON / CLOCK | [xbblk11.out](../../scratchpad/AE_trall/xbblk11.out) |
| xbblk2 | MSX1 | XBBLK2_run1.out | DIFFERS (87) | 74 | 43 | AS-MSX2+ + POWER-ON / CLOCK | [xbblk2.out](../../scratchpad/AE_trall/xbblk2.out) |
| xbblk3 | MSX1 | XBBLK3_run1.out | DIFFERS (59) | 40 | 20 | AS-MSX2+ + POWER-ON / CLOCK | [xbblk3.out](../../scratchpad/AE_trall/xbblk3.out) |
| xbblk4 | MSX1 | XBBLK4_run1.out | DIFFERS (71) | 46 | 25 | AS-MSX2+ + POWER-ON / CLOCK | [xbblk4.out](../../scratchpad/AE_trall/xbblk4.out) |
| xbblk5 | MSX1 | XBBLK5_run1.out | DIFFERS (75) | 48 | 33 | AS-MSX2+ + POWER-ON / CLOCK | [xbblk5.out](../../scratchpad/AE_trall/xbblk5.out) |
| xbblk6 | MSX1 | XBBLK6_run1.out | DIFFERS (75) | 48 | 23 | AS-MSX2+ + POWER-ON / CLOCK | [xbblk6.out](../../scratchpad/AE_trall/xbblk6.out) |
| xbblk7 | MSX1 | XBBLK7_run1.out | DIFFERS (75) | 48 | 19 | AS-MSX2+ + POWER-ON / CLOCK | [xbblk7.out](../../scratchpad/AE_trall/xbblk7.out) |
| xbblk8 | MSX1 | XBBLK8_run1.out | DIFFERS (71) | 46 | 22 | AS-MSX2+ + POWER-ON / CLOCK | [xbblk8.out](../../scratchpad/AE_trall/xbblk8.out) |
| xbblk9 | MSX1 | XBBLK9_run1.out | DIFFERS (63) | 42 | 30 | AS-MSX2+ + POWER-ON / CLOCK | [xbblk9.out](../../scratchpad/AE_trall/xbblk9.out) |
| xbcon1 | MSX1 | XBCON1_run1.out | DIFFERS (1) | 1 | 0 | AS-MSX2+ + POWER-ON / CLOCK | [xbcon1.out](../../scratchpad/AE_trall/xbcon1.out) |
| xbcon2 | MSX1 | XBCON2_run1.out | DIFFERS (1) | 1 | 0 | AS-MSX2+ + POWER-ON / CLOCK | [xbcon2.out](../../scratchpad/AE_trall/xbcon2.out) |
| xbcon3 | MSX1 | XBCON3_run1.out | DIFFERS (1) | 1 | 0 | AS-MSX2+ + POWER-ON / CLOCK | [xbcon3.out](../../scratchpad/AE_trall/xbcon3.out) |
| xbf | MSX2 | AE_xbf_msx2.out | SAME | - | 0 | SAME | [xbf.out](../../scratchpad/AE_trall/xbf.out) |
| xbfile1 | MSX1 | XBFILE1_run1.out | DIFFERS (31) | 26 | 19 | AS-MSX2+ + POWER-ON / CLOCK | [xbfile1.out](../../scratchpad/AE_trall/xbfile1.out) |
| xbfile2 | MSX1 | XBFILE2_run1.out | DIFFERS (76) | 73 | 59 | AS-MSX2+ + POWER-ON / CLOCK | [xbfile2.out](../../scratchpad/AE_trall/xbfile2.out) |
| xbfile3 | MSX1 | XBFILE3_run1.out | DIFFERS (48) | 28 | 8 | AS-MSX2+ + POWER-ON / CLOCK | [xbfile3.out](../../scratchpad/AE_trall/xbfile3.out) |
| xbfile4 | MSX1 | XBFILE4_run1.out | DIFFERS (68) | 47 | 25 | AS-MSX2+ + POWER-ON / CLOCK | [xbfile4.out](../../scratchpad/AE_trall/xbfile4.out) |
| xbrec1 | MSX1 | XBREC1_run1.out | DIFFERS (96) | 69 | 42 | AS-MSX2+ + POWER-ON / CLOCK | [xbrec1.out](../../scratchpad/AE_trall/xbrec1.out) |
| xbrec2 | MSX1 | XBREC2_run1.out | DIFFERS (103) | 68 | 22 | AS-MSX2+ + POWER-ON / CLOCK | [xbrec2.out](../../scratchpad/AE_trall/xbrec2.out) |
| xbrec3 | MSX1 | XBREC3_run1.out | DIFFERS (67) | 48 | 27 | AS-MSX2+ + POWER-ON / CLOCK | [xbrec3.out](../../scratchpad/AE_trall/xbrec3.out) |
| xbsys1 | MSX1 | XBSYS1_run1.out | DIFFERS (67) | 12 | 5 | AS-MSX2+ + CONFIG (addresses) | [xbsys1.out](../../scratchpad/AE_trall/xbsys1.out) |
| xbsys2 | MSX1 | XBSYS2_run1.out | DIFFERS (58) | 11 | 7 | AS-MSX2+ + CONFIG; **GT/ST: DSKRST interrupts** | [xbsys2.out](../../scratchpad/AE_trall/xbsys2.out) |
| xbsys3 | MSX1 | XBSYS3_run1.out | DIFFERS (63) | 12 | 2 | AS-MSX2+ + CONFIG (addresses) | [xbsys3.out](../../scratchpad/AE_trall/xbsys3.out) |
| xcalslt | MSX1 | AE_xcalslt_nodisk.out | DIFFERS (30) | 0 | 0 | AS-MSX2+ | [xcalslt.out](../../scratchpad/AE_trall/xcalslt.out) |
| xchg | MSX1 | XCHG_fix1.out | SAME | 0 | 0 | SAME | [xchg.out](../../scratchpad/AE_trall/xchg.out) |
| xchg2 | MSX1 | XCHG2_fix1.out | DIFFERS (18) | 14 | 0 | TIMING / CLOCK | [xchg2.out](../../scratchpad/AE_trall/xchg2.out) |
| xchgcpu | TR | - | TR PROBE | - | 500 | turbo R probe | [xchgcpu.out](../../scratchpad/AE_trall/xchgcpu.out) |
| xchgw | MSX1 | XCHGW_fix1.out | SAME | 0 | 0 | SAME | [xchgw.out](../../scratchpad/AE_trall/xchgw.out) |
| xchknew | MSX2 | AE_xchknew_msx2.out | DIFFERS (1) | - | 0 | POWER-ON | [xchknew.out](../../scratchpad/AE_trall/xchknew.out) |
| xchkslz0 | MSX2 | AE_xchkslz0_msx2.out | DIFFERS (1) | - | 9 | **NEW-TR**, **GT/ST DIFF** | [xchkslz0.out](../../scratchpad/AE_trall/xchkslz0.out) |
| xchkslzd | MSX2 | AE_xchkslzd_msx2.out | DIFFERS (1) | - | 10 | **NEW-TR**, **GT/ST DIFF** | [xchkslzd.out](../../scratchpad/AE_trall/xchkslzd.out) |
| xchoice1 | MSX1 | XCHOICE1_run1.out | DIFFERS (23) | 3 | 0 | AS-MSX2+ + CONFIG (addresses) | [xchoice1.out](../../scratchpad/AE_trall/xchoice1.out) |
| xchoice2 | MSX1 | XCHOICE2_run1.out | DIFFERS (19) | 3 | 0 | AS-MSX2+ + CONFIG (addresses) | [xchoice2.out](../../scratchpad/AE_trall/xchoice2.out) |
| xchput | MSX1 | XCH_fix1.out | SAME | 0 | 0 | SAME | [xchput.out](../../scratchpad/AE_trall/xchput.out) |
| xchput2 | MSX1 | XCH2_fix1.out | SAME | 0 | 0 | SAME | [xchput2.out](../../scratchpad/AE_trall/xchput2.out) |
| xchput3 | MSX1 | XCH3_fix1.out | SAME | 0 | 0 | SAME | [xchput3.out](../../scratchpad/AE_trall/xchput3.out) |
| xchput4 | MSX1 | XCH4_fix1.out | SAME | 0 | 0 | SAME | [xchput4.out](../../scratchpad/AE_trall/xchput4.out) |
| xchput5 | MSX1 | XCH5_fix1.out | SAME | 0 | 0 | SAME | [xchput5.out](../../scratchpad/AE_trall/xchput5.out) |
| xchrgtr | MSX1 | XCHRGTR_run4.out | SAME | 0 | 0 | SAME | [xchrgtr.out](../../scratchpad/AE_trall/xchrgtr.out) |
| xchrgtr2 | MSX1 | XCHRGTR2_run1.out | SAME | 0 | 0 | SAME | [xchrgtr2.out](../../scratchpad/AE_trall/xchrgtr2.out) |
| xclk | MSX2 | AE_xclk_msx2.out | DIFFERS (48) | - | 11 | TIMING / CLOCK | [xclk.out](../../scratchpad/AE_trall/xclk.out) |
| xclr | MSX1 | XCLR_run5.out | DIFFERS (486) | 0 | 0 | AS-MSX2+ | [xclr.out](../../scratchpad/AE_trall/xclr.out) |
| xcls | MSX1 | XCLS_fix1.out | SAME | 0 | 0 | SAME | [xcls.out](../../scratchpad/AE_trall/xcls.out) |
| xcnv | MSX1 | XCNV_run1.out | SAME | 0 | 0 | SAME | [xcnv.out](../../scratchpad/AE_trall/xcnv.out) |
| xcnv2 | MSX1 | XCNV2_run2.out | SAME | 0 | 0 | SAME | [xcnv2.out](../../scratchpad/AE_trall/xcnv2.out) |
| xdcompr | MSX1 | XDCOMPR_run1.out | SAME | 0 | 0 | SAME | [xdcompr.out](../../scratchpad/AE_trall/xdcompr.out) |
| xdent1 | MSX1 | XDENT1_run1.out | DIFFERS (21) | 0 | 0 | AS-MSX2+ | [xdent1.out](../../scratchpad/AE_trall/xdent1.out) |
| xdent2 | MSX1 | XDENT2_run1.out | DIFFERS (16) | 0 | 0 | AS-MSX2+ | [xdent2.out](../../scratchpad/AE_trall/xdent2.out) |
| xdent3 | MSX1 | XDENT3_run1.out | DIFFERS (23) | 0 | 0 | AS-MSX2+ | [xdent3.out](../../scratchpad/AE_trall/xdent3.out) |
| xdent4 | MSX1 | XDENT4_run1.out | DIFFERS (11) | 0 | 0 | AS-MSX2+ | [xdent4.out](../../scratchpad/AE_trall/xdent4.out) |
| xdent5 | MSX1 | XDENT5_run1.out | DIFFERS (52) | 1 | 1 | AS-MSX2+ + CONFIG (addresses) | [xdent5.out](../../scratchpad/AE_trall/xdent5.out) |
| xdent6 | MSX1 | XDENT6_run1.out | DIFFERS (58) | 2 | 2 | AS-MSX2+ + CONFIG (addresses) | [xdent6.out](../../scratchpad/AE_trall/xdent6.out) |
| xdent7 | MSX1 | XDENT7_run1.out | DIFFERS (1) | 0 | 0 | AS-MSX2+ | [xdent7.out](../../scratchpad/AE_trall/xdent7.out) |
| xdfmt1 | MSX1 | XDFMT1_run1.out | DIFFERS (59) | 0 | 0 | AS-MSX2+ | [xdfmt1.out](../../scratchpad/AE_trall/xdfmt1.out) |
| xdfmt2 | MSX1 | AE_m1on2_vgdisk_xdfmt.out | DIFFERS (37) | 0 | 0 | AS-MSX2+ | [xdfmt2.out](../../scratchpad/AE_trall/xdfmt2.out) |
| xdfmt3 | MSX1 | AE_m1on2_vgdisk_xdfmt.out | DIFFERS (16) | 0 | 0 | AS-MSX2+ | [xdfmt3.out](../../scratchpad/AE_trall/xdfmt3.out) |
| xdrvtbl | MSX1 | XDRVTBL_run1.out | DIFFERS (2) | 0 | 0 | AS-MSX2+ | [xdrvtbl.out](../../scratchpad/AE_trall/xdrvtbl.out) |
| xdsk1 | MSX1 | XDSK1_run2.out | DIFFERS (25) | 0 | 0 | AS-MSX2+ | [xdsk1.out](../../scratchpad/AE_trall/xdsk1.out) |
| xdsk2 | MSX1 | XDSK2_run1.out | DIFFERS (19) | 0 | 0 | AS-MSX2+ | [xdsk2.out](../../scratchpad/AE_trall/xdsk2.out) |
| xdsk3 | MSX1 | AE_xdsk3_disk.out | DIFFERS (36) | 0 | 0 | AS-MSX2+ | [xdsk3.out](../../scratchpad/AE_trall/xdsk3.out) |
| xdsk4 | MSX1 | XDSK4_run1.out | DIFFERS (35) | 0 | 0 | AS-MSX2+ | [xdsk4.out](../../scratchpad/AE_trall/xdsk4.out) |
| xdsk5 | MSX1 | XDSK5_run2.out | DIFFERS (33) | 0 | 0 | AS-MSX2+ | [xdsk5.out](../../scratchpad/AE_trall/xdsk5.out) |
| xdsk6 | MSX1 | XDSK6_run1.out | DIFFERS (16) | 0 | 0 | AS-MSX2+ | [xdsk6.out](../../scratchpad/AE_trall/xdsk6.out) |
| xdskio1 | MSX1 | XDSKIO1_run1.out | DIFFERS (25) | 0 | 0 | AS-MSX2+ | [xdskio1.out](../../scratchpad/AE_trall/xdskio1.out) |
| xdskio2 | MSX1 | XDSKIO2_run1.out | DIFFERS (14) | 0 | 0 | AS-MSX2+ | [xdskio2.out](../../scratchpad/AE_trall/xdskio2.out) |
| xdskio2p | MSX1 | XDSKIO2P_run1.out | DIFFERS (14) | 0 | 0 | AS-MSX2+ | [xdskio2p.out](../../scratchpad/AE_trall/xdskio2p.out) |
| xenaslt | MSX1 | XENASLT_run4.out | DIFFERS (22) | 10 | 0 | CONFIG | [xenaslt.out](../../scratchpad/AE_trall/xenaslt.out) |
| xenaslt2 | MSX2 | xenaslt2.out | SAME | - | 0 | SAME | [xenaslt2.out](../../scratchpad/AE_trall/xenaslt2.out) |
| xeol | MSX2 | AE_xeol_msx2.out | DIFFERS (1) | - | 1 | POWER-ON | [xeol.out](../../scratchpad/AE_trall/xeol.out) |
| xextrom | MSX2 | AE_xextrom_msx2.out | DIFFERS (1) | - | 0 | POWER-ON | [xextrom.out](../../scratchpad/AE_trall/xextrom.out) |
| xextrom0 | MSX2 | AE_xextrom0_msx2.out | DIFFERS (1) | - | 1 | POWER-ON | [xextrom0.out](../../scratchpad/AE_trall/xextrom0.out) |
| xextromnx | MSX2 | AE_xextromnx_msx2.out | DIFFERS (1) | - | 1 | POWER-ON | [xextromnx.out](../../scratchpad/AE_trall/xextromnx.out) |
| xf4port | MSX2 | AE_xf4port_msx2.out | DIFFERS (31) | - | 22 | **NEW-TR** | [xf4port.out](../../scratchpad/AE_trall/xf4port.out) |
| xf4reset | MSX2 | AE_xf4reset_msx2.out | DIFFERS (22) | - | 0 | **NEW-TR**, no reading | [xf4reset.out](../../scratchpad/AE_trall/xf4reset.out) |
| xfnk | MSX1 | XFNK_fix1.out | DIFFERS (14) | 0 | 0 | AS-MSX2+ | [xfnk.out](../../scratchpad/AE_trall/xfnk.out) |
| xfnk2 | MSX1 | XFNK2_run1.out | DIFFERS (10) | 0 | 0 | AS-MSX2+ | [xfnk2.out](../../scratchpad/AE_trall/xfnk2.out) |
| xfnk3 | MSX1 | XFNK3_run2.out | DIFFERS (45) | 0 | 0 | AS-MSX2+ | [xfnk3.out](../../scratchpad/AE_trall/xfnk3.out) |
| xfsw | MSX1 | XFSW_run1.out | SAME | 0 | 0 | SAME | [xfsw.out](../../scratchpad/AE_trall/xfsw.out) |
| xgetcpu | TR | - | TR PROBE | - | 18 | turbo R probe | [xgetcpu.out](../../scratchpad/AE_trall/xgetcpu.out) |
| xgetypr | MSX1 | XGETYPR_run3.out | SAME | 0 | 0 | SAME | [xgetypr.out](../../scratchpad/AE_trall/xgetypr.out) |
| xgfx1 | MSX1 | XGFX1_run5.out | DIFFERS (79) | 0 | 0 | AS-MSX2+ | [xgfx1.out](../../scratchpad/AE_trall/xgfx1.out) |
| xgfx2 | MSX1 | XGFX2_run7.out | DIFFERS (145) | 0 | 0 | AS-MSX2+ | [xgfx2.out](../../scratchpad/AE_trall/xgfx2.out) |
| xgfx3 | MSX1 | XGFX3_fix1.out | DIFFERS (178) | 0 | 0 | AS-MSX2+ | [xgfx3.out](../../scratchpad/AE_trall/xgfx3.out) |
| xgfx4 | MSX1 | XGFX4_run2.out | DIFFERS (38) | 0 | 0 | AS-MSX2+ | [xgfx4.out](../../scratchpad/AE_trall/xgfx4.out) |
| xgfx5 | MSX1 | XGFX5_run3.out | DIFFERS (193) | 0 | 0 | AS-MSX2+ | [xgfx5.out](../../scratchpad/AE_trall/xgfx5.out) |
| xgfx5b | MSX1 | XGFX5B_run1.out | DIFFERS (30) | 0 | 0 | AS-MSX2+ | [xgfx5b.out](../../scratchpad/AE_trall/xgfx5b.out) |
| xgfx6 | MSX1 | XGFX6_run10.out | DIFFERS (179) | 0 | 0 | AS-MSX2+ | [xgfx6.out](../../scratchpad/AE_trall/xgfx6.out) |
| xinig | MSX1 | XINIG_run3.out | DIFFERS (866) | 0 | 0 | AS-MSX2+ | [xinig.out](../../scratchpad/AE_trall/xinig.out) |
| xinit | MSX1 | XINIT_fix1.out | DIFFERS (1132) | 10 | 0 | **NEW-TR** | [xinit.out](../../scratchpad/AE_trall/xinit.out) |
| xinit3 | MSX1 | AE_xinitguard_nodisk.out | DIFFERS (657) | 4 | 0 | CONFIG | [xinit3.out](../../scratchpad/AE_trall/xinit3.out) |
| xinit4 | MSX1 | AE_xinitguard_nodisk.out | DIFFERS (1412) | 22 | 0 | **NEW-TR** | [xinit4.out](../../scratchpad/AE_trall/xinit4.out) |
| xinitio | MSX1 | XINITIO_run3.out | DIFFERS (68) | 43 | 0 | CONFIG | [xinitio.out](../../scratchpad/AE_trall/xinitio.out) |
| xinitio2 | MSX1 | XINITIO2_run2.out | DIFFERS (30) | 5 | 0 | CONFIG | [xinitio2.out](../../scratchpad/AE_trall/xinitio2.out) |
| xinitio3 | MSX1 | XINITIO3_run2.out | DIFFERS (37) | 6 | 0 | CONFIG | [xinitio3.out](../../scratchpad/AE_trall/xinitio3.out) |
| xinitio4 | MSX1 | XINITIO4_run1.out | DIFFERS (23) | 5 | 0 | CONFIG | [xinitio4.out](../../scratchpad/AE_trall/xinitio4.out) |
| xinitio5 | MSX1 | XINITIO5_run4.out | DIFFERS (23) | 9 | 0 | CONFIG | [xinitio5.out](../../scratchpad/AE_trall/xinitio5.out) |
| xinitio6 | MSX1 | XINITIO6_run4.out | DIFFERS (10) | 10 | 0 | TIMING / CLOCK | [xinitio6.out](../../scratchpad/AE_trall/xinitio6.out) |
| xinitio7 | MSX1 | XINITIO7_run1.out | DIFFERS (8) | 10 | 0 | TIMING / CLOCK | [xinitio7.out](../../scratchpad/AE_trall/xinitio7.out) |
| xinp1 | MSX1 | XINP1_run3.out | DIFFERS (171) | 145 | 0 | **NEW-TR** | [xinp1.out](../../scratchpad/AE_trall/xinp1.out) |
| xkey | MSX1 | XKEY_fix1.out | SAME | 0 | 0 | SAME | [xkey.out](../../scratchpad/AE_trall/xkey.out) |
| xlin | MSX1 | AE_xlinready_nodisk.out | SAME | 0 | 0 | SAME | [xlin.out](../../scratchpad/AE_trall/xlin.out) |
| xlin2a | MSX1 | AE_xlinready_nodisk.out | SAME | 0 | 0 | SAME | [xlin2a.out](../../scratchpad/AE_trall/xlin2a.out) |
| xlin2b | MSX1 | AE_xlinready_nodisk.out | SAME | 0 | 0 | SAME | [xlin2b.out](../../scratchpad/AE_trall/xlin2b.out) |
| xlin2c | MSX1 | AE_xlinready_nodisk.out | SAME | 0 | 0 | SAME | [xlin2c.out](../../scratchpad/AE_trall/xlin2c.out) |
| xlin3 | MSX1 | XLIN3_run3.out | SAME | 0 | 0 | SAME | [xlin3.out](../../scratchpad/AE_trall/xlin3.out) |
| xlin4 | MSX1 | XLIN4_run1.out | SAME | 0 | 0 | SAME | [xlin4.out](../../scratchpad/AE_trall/xlin4.out) |
| xlin5 | MSX1 | XLIN5_run1.out | SAME | 0 | 0 | SAME | [xlin5.out](../../scratchpad/AE_trall/xlin5.out) |
| xlin6 | MSX1 | XLIN6_run1.out | SAME | 0 | 0 | SAME | [xlin6.out](../../scratchpad/AE_trall/xlin6.out) |
| xlpt | MSX1 | XLPT_run2.out | SAME | 0 | 0 | SAME | [xlpt.out](../../scratchpad/AE_trall/xlpt.out) |
| xlpt2 | MSX1 | XLPT2_run1.out | SAME | 0 | 0 | SAME | [xlpt2.out](../../scratchpad/AE_trall/xlpt2.out) |
| xlpt3 | MSX1 | XLPT3_run1.out | SAME | 0 | 0 | SAME | [xlpt3.out](../../scratchpad/AE_trall/xlpt3.out) |
| xmode | MSX2 | AE_xmode_msx2.out | DIFFERS (26) | - | 0 | CONFIG | [xmode.out](../../scratchpad/AE_trall/xmode.out) |
| xmode2 | MSX2 | AE_xmode2_msx2.out | DIFFERS (89) | - | 44 | TIMING / CLOCK | [xmode2.out](../../scratchpad/AE_trall/xmode2.out) |
| xoutdlp | MSX1 | XOUTDLP_run2.out | DIFFERS (4) | 0 | 0 | AS-MSX2+ | [xoutdlp.out](../../scratchpad/AE_trall/xoutdlp.out) |
| xoutdo | MSX1 | XOUTDO_run2.out | SAME | 0 | 0 | SAME | [xoutdo.out](../../scratchpad/AE_trall/xoutdo.out) |
| xplt | MSX2 | AE_xplt_msx2.out | SAME | - | 0 | SAME | [xplt.out](../../scratchpad/AE_trall/xplt.out) |
| xpsgr7 | MSX1 | AE_xpsgr7.out | DIFFERS (11) | 0 | 1 | AS-MSX2+ | [xpsgr7.out](../../scratchpad/AE_trall/xpsgr7.out) |
| xrdres | MSX2 | AE_xrdres_msx2p.out | DIFFERS (85) | - | 0 | **NEW-TR** | [xrdres.out](../../scratchpad/AE_trall/xrdres.out) |
| xrdslt | MSX1 | XRDSLT_run5.out | DIFFERS (80) | 5 | 5 | CONFIG | [xrdslt.out](../../scratchpad/AE_trall/xrdslt.out) |
| xrdslt2 | MSX2 | xrdslt2.out | SAME | - | 0 | SAME | [xrdslt2.out](../../scratchpad/AE_trall/xrdslt2.out) |
| xrrnd1 | MSX1 | XRRND1_run1.out | DIFFERS (55) | 38 | 19 | TIMING / CLOCK | [xrrnd1.out](../../scratchpad/AE_trall/xrrnd1.out) |
| xrslreg | MSX1 | XRSLREG_run2.out | SAME | 0 | 0 | SAME | [xrslreg.out](../../scratchpad/AE_trall/xrslreg.out) |
| xscank | MSX1 | XSCANK_run2.out | DIFFERS (467) | 266 | 69 | CONFIG | [xscank.out](../../scratchpad/AE_trall/xscank.out) |
| xscr | MSX1 | XSCR_fix1.out | DIFFERS (63) | 0 | 0 | AS-MSX2+ | [xscr.out](../../scratchpad/AE_trall/xscr.out) |
| xscr3 | MSX1 | XSCR3_fix1.out | DIFFERS (5) | 0 | 0 | AS-MSX2+ | [xscr3.out](../../scratchpad/AE_trall/xscr3.out) |
| xscr4 | MSX1 | XSCR4_fix1.out | DIFFERS (4) | 0 | 0 | AS-MSX2+ | [xscr4.out](../../scratchpad/AE_trall/xscr4.out) |
| xscr5 | MSX1 | XSCR5_fix1.out | DIFFERS (8) | 0 | 0 | AS-MSX2+ | [xscr5.out](../../scratchpad/AE_trall/xscr5.out) |
| xset | MSX1 | XSET_run4.out | DIFFERS (889) | 0 | 0 | AS-MSX2+ | [xset.out](../../scratchpad/AE_trall/xset.out) |
| xsetw | MSX1 | AE_xsetw_nodisk.out | DIFFERS (1) | 1 | 0 | POWER-ON | [xsetw.out](../../scratchpad/AE_trall/xsetw.out) |
| xsnd1 | MSX1 | XSND1_run4.out | DIFFERS (133) | 126 | 11 | **NEW-TR** (minor: BEEP's C) | [xsnd1.out](../../scratchpad/AE_trall/xsnd1.out) |
| xsnd1b | MSX1 | XSND1B_run1.out | DIFFERS (56) | 42 | 0 | **NEW-TR** (minor: BEEP's C) | [xsnd1b.out](../../scratchpad/AE_trall/xsnd1b.out) |
| xspr | MSX1 | XSPR_run3.out | SAME | 0 | 0 | SAME | [xspr.out](../../scratchpad/AE_trall/xspr.out) |
| xspr2 | MSX2 | AE_xspr2_msx2.out | SAME | - | 0 | SAME | [xspr2.out](../../scratchpad/AE_trall/xspr2.out) |
| xspr3 | MSX2 | AE_xspr3_msx2.out | SAME | - | 0 | SAME | [xspr3.out](../../scratchpad/AE_trall/xspr3.out) |
| xsubbeep | MSX2 | AE_xsubbeep_msx2.out | DIFFERS (7243) | - | 4492 | CONFIG | [xsubbeep.out](../../scratchpad/AE_trall/xsubbeep.out) |
| xsubblt | MSX2 | AE_xsubblt_msx2.out | DIFFERS (7) | - | 4 | TIMING / CLOCK | [xsubblt.out](../../scratchpad/AE_trall/xsubblt.out) |
| xsubbltd | MSX2 | AE_xsubbltd_msx2.out | DIFFERS (108) | - | 98 | CONFIG | [xsubbltd.out](../../scratchpad/AE_trall/xsubbltd.out) |
| xsubbox | MSX2 | AE_xsubbox_msx2.out | DIFFERS (3) | - | 2 | TIMING / CLOCK | [xsubbox.out](../../scratchpad/AE_trall/xsubbox.out) |
| xsubbox2 | MSX2 | AE_xsubbox2_msx2.out | DIFFERS (2) | - | 4 | TIMING / CLOCK | [xsubbox2.out](../../scratchpad/AE_trall/xsubbox2.out) |
| xsubcls | MSX2 | AE_xsubcls_msx2.out | SAME | - | 0 | SAME | [xsubcls.out](../../scratchpad/AE_trall/xsubcls.out) |
| xsubctx | MSX2 | AE_xsubctx_msx2.out | DIFFERS (6) | - | 8 | POWER-ON | [xsubctx.out](../../scratchpad/AE_trall/xsubctx.out) |
| xsubdln | MSX2 | AE_xsubdln_msx2.out | DIFFERS (1) | - | 1 | POWER-ON | [xsubdln.out](../../scratchpad/AE_trall/xsubdln.out) |
| xsubdln2 | MSX2 | AE_xsubdln2_msx2.out | DIFFERS (769) | - | 769 | POWER-ON | [xsubdln2.out](../../scratchpad/AE_trall/xsubdln2.out) |
| xsubdln3 | MSX2 | AE_xsubdln3_msx2.out | DIFFERS (769) | - | 769 | POWER-ON | [xsubdln3.out](../../scratchpad/AE_trall/xsubdln3.out) |
| xsubdln4 | MSX2 | AE_xsubdln4_msx2.out | DIFFERS (1) | - | 0 | POWER-ON | [xsubdln4.out](../../scratchpad/AE_trall/xsubdln4.out) |
| xsubfnk | MSX2 | AE_xsubfnk_msx2.out | SAME | - | 0 | SAME | [xsubfnk.out](../../scratchpad/AE_trall/xsubfnk.out) |
| xsubgc | MSX2 | AE_xsubgc_msx2.out | SAME | - | 0 | SAME | [xsubgc.out](../../scratchpad/AE_trall/xsubgc.out) |
| xsubgc2 | MSX2 | AE_xsubgc2_msx2.out | DIFFERS (6) | - | 2 | TIMING / CLOCK | [xsubgc2.out](../../scratchpad/AE_trall/xsubgc2.out) |
| xsubgpp | MSX2 | AE_xsubgpp_msx2.out | SAME | - | 0 | SAME | [xsubgpp.out](../../scratchpad/AE_trall/xsubgpp.out) |
| xsubgpp2 | MSX2 | AE_xsubgpp2_msx2.out | SAME | - | 0 | SAME | [xsubgpp2.out](../../scratchpad/AE_trall/xsubgpp2.out) |
| xsubknj | MSX2 | AE_xsubknj_msx2.out | DIFFERS (7) | - | 6 | TIMING / CLOCK | [xsubknj.out](../../scratchpad/AE_trall/xsubknj.out) |
| xsubkyk | MSX2 | AE_xsubkyk_msx2.out | DIFFERS (89) | - | 18 | TIMING / CLOCK | [xsubkyk.out](../../scratchpad/AE_trall/xsubkyk.out) |
| xsubkyk2 | MSX2 | AE_xsubkyk2_msx2.out | DIFFERS (85) | - | 16 | TIMING / CLOCK | [xsubkyk2.out](../../scratchpad/AE_trall/xsubkyk2.out) |
| xsubkyk3 | MSX2 | AE_xsubkyk3_msx2.out | DIFFERS (51) | - | 6 | TIMING / CLOCK | [xsubkyk3.out](../../scratchpad/AE_trall/xsubkyk3.out) |
| xsubkyk4 | MSX2 | AE_xsubkyk4_msx2.out | DIFFERS (84) | - | 15 | TIMING / CLOCK | [xsubkyk4.out](../../scratchpad/AE_trall/xsubkyk4.out) |
| xsubmv | MSX2 | AE_xsubmv_msx2.out | SAME | - | 0 | SAME | [xsubmv.out](../../scratchpad/AE_trall/xsubmv.out) |
| xsubmv2 | MSX2 | AE_xsubmv2_msx2.out | SAME | - | 0 | SAME | [xsubmv2.out](../../scratchpad/AE_trall/xsubmv2.out) |
| xsubpad | MSX2 | AE_xsubpad_msx2.out | DIFFERS (35) | - | 0 | **NEW-TR** | [xsubpad.out](../../scratchpad/AE_trall/xsubpad.out) |
| xsubpadb | MSX2 | AE_xsubpadb_msx2.out | DIFFERS (28) | - | 0 | **NEW-TR** | [xsubpadb.out](../../scratchpad/AE_trall/xsubpadb.out) |
| xsubpadg | MSX2 | AE_xsubpadg_msx2.out | DIFFERS (1) | - | 0 | CONFIG | [xsubpadg.out](../../scratchpad/AE_trall/xsubpadg.out) |
| xsubpadm | MSX2 | AE_xsubpadm_msx2.out | DIFFERS (33) | - | 0 | **NEW-TR** | [xsubpadm.out](../../scratchpad/AE_trall/xsubpadm.out) |
| xsubpads | MSX2 | AE_xsubpads_msx2.out | DIFFERS (592) | - | 314 | **NEW-TR** | [xsubpads.out](../../scratchpad/AE_trall/xsubpads.out) |
| xsubpadx | MSX2 | AE_xsubpadx_msx2.out | DIFFERS (47) | - | 0 | **NEW-TR** | [xsubpadx.out](../../scratchpad/AE_trall/xsubpadx.out) |
| xsubpch | MSX2 | AE_xsubpch_msx2.out | DIFFERS (1) | - | 1 | POWER-ON | [xsubpch.out](../../scratchpad/AE_trall/xsubpch.out) |
| xsubpch2 | MSX2 | AE_xsubpch2_msx2.out | DIFFERS (1) | - | 1 | POWER-ON | [xsubpch2.out](../../scratchpad/AE_trall/xsubpch2.out) |
| xsubpch3 | MSX2 | AE_xsubpch3_msx2.out | DIFFERS (1) | - | 1 | POWER-ON | [xsubpch3.out](../../scratchpad/AE_trall/xsubpch3.out) |
| xsubpmt | MSX2 | AE_xsubpmt_msx2.out | DIFFERS (405) | - | 411 | POWER-ON | [xsubpmt.out](../../scratchpad/AE_trall/xsubpmt.out) |
| xsubpvr | MSX2 | AE_xsubpvr_msx2.out | DIFFERS (96) | - | 15 | TIMING / CLOCK | [xsubpvr.out](../../scratchpad/AE_trall/xsubpvr.out) |
| xsubpvr2 | MSX2 | AE_xsubpvr2_msx2.out | DIFFERS (56) | - | 3 | TIMING / CLOCK | [xsubpvr2.out](../../scratchpad/AE_trall/xsubpvr2.out) |
| xsubpvr3 | MSX2 | AE_xsubpvr3_msx2.out | DIFFERS (93) | - | 15 | TIMING / CLOCK | [xsubpvr3.out](../../scratchpad/AE_trall/xsubpvr3.out) |
| xsubsc2 | MSX2 | AE_xsubsc2_msx2.out | DIFFERS (22) | - | 5 | TIMING / CLOCK | [xsubsc2.out](../../scratchpad/AE_trall/xsubsc2.out) |
| xsubscan | MSX2 | AE_xsubscan_msx2.out | SAME | - | 0 | SAME | [xsubscan.out](../../scratchpad/AE_trall/xsubscan.out) |
| xsubscan2 | MSX2 | AE_xsubscan2_msx2.out | SAME | - | 0 | SAME | [xsubscan2.out](../../scratchpad/AE_trall/xsubscan2.out) |
| xsubscr | MSX2 | AE_xsubscr_msx2.out | DIFFERS (12) | - | 7 | TIMING / CLOCK | [xsubscr.out](../../scratchpad/AE_trall/xsubscr.out) |
| xsubset | MSX2 | AE_xsubset_msx2.out | DIFFERS (83) | - | 42 | CONFIG | [xsubset.out](../../scratchpad/AE_trall/xsubset.out) |
| xsynchr | MSX1 | XSYNCHR_run1.out | SAME | 0 | 0 | SAME | [xsynchr.out](../../scratchpad/AE_trall/xsynchr.out) |
| xsynchr2 | MSX1 | XSYNCHR2_run1.out | SAME | 0 | 0 | SAME | [xsynchr2.out](../../scratchpad/AE_trall/xsynchr2.out) |
| xtap1 | MSX1 | XTAP1_run2.out | DIFFERS (91) | 92 | 0 | **NEW-TR** (@tape, no cassette port) | [xtap1.out](../../scratchpad/AE_trall/xtap1.out) |
| xtap2 | MSX1 | XTAP2_run1.out | DIFFERS (52) | 52 | 0 | **NEW-TR** | [xtap2.out](../../scratchpad/AE_trall/xtap2.out) |
| xtap3 | MSX1 | XTAP3_run1.out | DIFFERS (47) | 47 | 0 | **NEW-TR** | [xtap3.out](../../scratchpad/AE_trall/xtap3.out) |
| xtap4 | MSX1 | XTAP4_run1.out | DIFFERS (31) | 31 | 0 | **NEW-TR** | [xtap4.out](../../scratchpad/AE_trall/xtap4.out) |
| xtap5 | MSX1 | XTAP5_run1.out | DIFFERS (49) | 49 | 0 | **NEW-TR** (@tape, no cassette port) | [xtap5.out](../../scratchpad/AE_trall/xtap5.out) |
| xtot | MSX1 | XTOT_fix1.out | DIFFERS (120) | 0 | 0 | AS-MSX2+ | [xtot.out](../../scratchpad/AE_trall/xtot.out) |
| xtot2 | MSX1 | XTOT2_fix1.out | DIFFERS (167) | 0 | 0 | AS-MSX2+ | [xtot2.out](../../scratchpad/AE_trall/xtot2.out) |
| xtrboot | TR | - | TR PROBE | - | 124 | turbo R probe | [xtrboot.out](../../scratchpad/AE_trall/xtrboot.out) |
| xva | MSX2 | AE_xva_msx2.out | SAME | - | 1 | SAME (GT/ST: POWER-ON) | [xva.out](../../scratchpad/AE_trall/xva.out) |
| xva13 | MSX2 | AE_xva13_msx2.out | DIFFERS (9) | - | 1 | APPARATUS (needs 64 KB VRAM) | [xva13.out](../../scratchpad/AE_trall/xva13.out) |
| xva14 | MSX2 | AE_xva14_msx2.out | SAME | - | 1 | SAME (GT/ST: POWER-ON) | [xva14.out](../../scratchpad/AE_trall/xva14.out) |
| xva16 | MSX2 | AE_xva16_msx2.out | DIFFERS (862) | - | 871 | TIMING / CLOCK | [xva16.out](../../scratchpad/AE_trall/xva16.out) |
| xva2 | MSX2 | AE_xva2_msx2.out | SAME | - | 1 | SAME (GT/ST: POWER-ON) | [xva2.out](../../scratchpad/AE_trall/xva2.out) |
| xva3 | MSX2 | AE_xva3_msx2.out | DIFFERS (1) | - | 1 | POWER-ON | [xva3.out](../../scratchpad/AE_trall/xva3.out) |
| xvdpreg | MSX1 | AE_xvdpreg_nodisk.out | DIFFERS (410) | 83 | 0 | CONFIG | [xvdpreg.out](../../scratchpad/AE_trall/xvdpreg.out) |
| xvram | MSX1 | XVRAM_run4.out | DIFFERS (12) | 0 | 0 | AS-MSX2+ | [xvram.out](../../scratchpad/AE_trall/xvram.out) |
| xwv | MSX2 | AE_xwv_msx2.out | DIFFERS (338) | - | 189 | CONFIG | [xwv.out](../../scratchpad/AE_trall/xwv.out) |
