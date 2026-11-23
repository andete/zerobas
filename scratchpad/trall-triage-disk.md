# D-TRSPEC triage — disk / BDOS group on the turbo R (48 probes)

The turbo R references (FS-A1GT = "GT", FS-A1ST = "ST", `biosl_run.py --row turbor`) are set against the VG-8020 +
NMS 1200 baseline and against the FS-A1WSX (MSX2+, "WSX") reading of the same probe in `scratchpad/AE_m1on2/` (run
2026-11-23 with the current probe source). Sources: `scratchpad/AE_trall/<probe>.out`, `scratchpad/AE_m1on2/<probe>.out`,
the committed VG run files, the probe headers, and `scratchpad/m1on2-triage-disk.md` (the MSX2 triage of the same probes,
whose decoding this reuses). Clean room: captures and probe sources only; nothing was run for this triage.
Offsets `+N` are into the capture; for the xb* probes the FCB starts at +2 of a record, so record+22/+23 is the FCB
date word and record+24/+25 the time word (FCB+14h / +16h).

## Summary

**Classes (48 probes):**
- **AS-MSX2+, byte-identical to the FS-A1WSX: 18** — xdent1-4, xdent7, xdfmt1-3, xdrvtbl, xdsk1-6, xdskio1, xdskio2,
  xdskio2p. Every disk-ROM entry case (PHYDIO / DSKIO / GETDPB / DSKCHG / DSKFMT / MTOFF / DRVTBL) reads exactly as on
  the WSX, on BOTH turbo R models (GT = ST in every one).
- **AS-MSX2+ apart from POWER-ON / CLOCK-TIME / residue bytes: 23** — xbabs1-2, xbblk1-11, xbcon1-3, xbfile1-4,
  xbrec1-3. The BDOS file / record / block / absolute-sector arithmetic is the WSX's; what differs is power-on RAM in
  fields no case writes (the case FCBs' unused bytes, the last capture byte), the FMAKE/FCLOSE time word (the RTC's
  host time of day), and kernel-buffer residue in three cases already pinned UNSTABLE.
- **AS-MSX2+ + CONFIG (work-area / ROM addresses): 7** — xbsys1-3 (ALLOC IX/IY, DSKRST DE/IX), xdent5-6 (DSKCHG's HL),
  xchoice1-2 (CHOICE's HL). Rules written self-relative (`ix-iy=$0C00`, `DE==IX`, "HL in the disk ROM") hold.
- **NEW-TR (a behaviour the WSX does not show): 0 confirmed.**
- **UNKNOWN: 1 case** — xbsys2 #14 DSKRST (after SELDSK 1) returns with interrupts **OFF on the FS-A1GT** (iff 0),
  ON on the FS-A1ST and the WSX (iff 1); the same DSKRST in xbsys1 #12 (current drive A) returns ON on all three.
  A1GT-only, one case, one run: re-run before calling it behaviour.

**Most important for the pages:** the turbo R disk ROM behaves as the FS-A1WSX's in every measured case, so every
MSX2+ (WSX) finding of `m1on2-triage-disk.md` holds on the turbo R too, on both models: interrupts left ON after BDOS
via $F37D, PHYDIO, DSKCHG, GETDPB, DSKFMT and DSKIO's success path; IY = $0314 after BDOS; DRVTBL / H.PHYD slot $8B;
MTOFF A = 4; C = $3C after a read; CHOICE keeps A / F; PHYDIO / DSKIO past the end of a 720 KB disk answers **$0C /
F $55** (not $02 / $08), B left at 3 on the refused straddling write, "read 2 from $FFFF" answers success with 1 KB of
zeros; PHYDIO media $FF sector 700 reads (A = 0); and FMAKE after `SDATE 2025-06-15` stamps **$5A8F (2025-04-15)**
(xbfile2 #3-#6 on the GT, the same as the WSX). The GT and ST differ only in power-on RAM, run time, buffer residue,
the A1GT's disk work area sitting **5 bytes lower** (ALLOC IX/IY $F180/$E580 vs $F185/$E585; DSKRST IX $F195 vs
$F19A; DSKCHG's HL $EF80 vs $EF85), and the one UNKNOWN above. CHOICE's HL is the turbo R disk ROM's own ($782A on
both models; WSX $7852).

**APPARATUS notes:**
- (a) **xdent5 / xdent6 have no `; @disk` line** (drive A is deliberately empty), so `trall_cmp.py` (and
  `m1on2_cmp.py`'s `pick`) compares them with the **diskless** VG-8020 row, whose records are all 0: their "vs VG"
  counts are meaningless. The right baseline is the `disk` row of `XDENT5_run1.out` / `XDENT6_run1.out` (VG + NMS 1200,
  drive empty). Against it the GT differs only as the WSX does (A, F, iff, HL).
- (b) **Stale baselines:** 26 of the 48 probes were committed after their VG run file (xbabs1-2, xbblk4, 6-11,
  xbfile1-4, xbrec1-3, xchoice1-2, xdfmt1, xdrvtbl, xdsk1, 2, 4, 5, 6, xdskio2p). Their "vs VG" byte lists can include
  probe changes; the WSX column (same probe source, run the same day) is the reliable comparison and is used here.
- (c) The time-of-day differences are not a turbo R fact: the RTC reads the host clock (GT stamps `$AF47` = 21:58:14 on
  2026-11-23, the WSX `$3C85` = 07:36:10 when AE_m1on2 ran). Any rule pinning a time must compare with GTIME.

---

## Per probe

Columns of each entry: class · the bytes that differ from the WSX (by case and field) · GT vs ST.
**POWER-ON** = a field no case writes (its value is the machine's power-on RAM pattern: GT `FF 00 00 FF`-like, ST /
WSX `00 FF FF 00`-like). **CLOCK-TIME** = an RTC stamp or reading. **residue** = kernel-buffer bytes past what a call
wrote, already marked UNSTABLE on the page.

### xbabs1 (66-byte records) · xbabs2 (74)
- AS-MSX2+ + POWER-ON (+ STALE-BASELINE). vs WSX: only the case FCBs' bytes (+2..+38 of every record), POWER-ON. The
  8250's lost first WRABS (m1on2 finding 8) does NOT occur: RDABS / PHYDIO read sector 20 back as written.
- GT vs ST: the same FCB bytes, POWER-ON only.

### xbblk1 (54)
- AS-MSX2+ + POWER-ON + CLOCK-TIME + residue. vs WSX: FCB POWER-ON (#0); the time word of every FCB (e.g. +4E/+4F
  `$AF39` vs `$3C70`); #6 / #8 DTA bytes past the fill (+16D..+170, +1D7..+1E2: residue / RAM, already UNSTABLE); +2BF
  past the 13 records (POWER-ON).
- GT vs ST: the same POWER-ON / residue cells.

### xbblk2 (58) · xbblk3 (62) · xbblk4 (64) · xbblk5-10 (66)
- AS-MSX2+ + POWER-ON + CLOCK-TIME (+ STALE-BASELINE for 4, 6-10). vs WSX: FCB POWER-ON; the FCB time word of every
  record (record+24/+25); xbblk2's spot DTA+512 (n·58+57: `FF` vs `00`, past the 512-byte fill, POWER-ON, the rules
  already check it against the residue) and +3A0..+3AF past the records. No A, F, HL, size, cluster or DTA difference.
- GT vs ST: POWER-ON cells, and the time word's minute / second bits (the two models ran seconds apart: e.g. xbblk5
  +5A `$3B` vs `$3D`).

### xbblk11 (66)
- AS-MSX2+ + POWER-ON + CLOCK-TIME + residue (+ STALE-BASELINE). As xbblk5-10, plus #11 RDBLKV8 spots +30C..+30F
  (`FC 19 40 AA` vs WSX `00 FF FF 00`): the record sector's leftover bytes, already UNSTABLE `XKB 11`.
- GT vs ST: POWER-ON only (the residue cells agree).

### xbcon1 · xbcon2 · xbcon3
- POWER-ON. vs WSX and vs VG: only the capture's last byte (+10F / +1EF / +13F), which no case writes (GT `$FF`).
- GT vs ST: identical.

### xbfile1-4 (52)
- AS-MSX2+ + POWER-ON + CLOCK-TIME (+ STALE-BASELINE). vs WSX: FCB POWER-ON, the FCB time words, tails past the
  records. The FCB DATE words are the WSX's: xbfile2 #3-#6 after `SDATE 2025-06-15` read **$5A8F (2025-04-15)** on the
  GT as on the WSX (m1on2 finding 9 holds on the turbo R); #7 `SDATE 2026-11-22` reads $5D76, correct.
- GT vs ST: POWER-ON cells (and xbfile2's last capture bytes +30C/+30D); no time difference.

### xbrec1-3 (52)
- AS-MSX2+ + POWER-ON + CLOCK-TIME + residue (+ STALE-BASELINE). vs WSX: FCB POWER-ON, time words, tails; xbrec1 #13
  RDRND of a never-written record, DTA +2CB..+2D7, and xbrec2 #11 RDSEQ of a never-written record, DTA +263..+26F (GT
  `19 E5 79 0F 0F 4F CD 2D EF F3 D1 1A 32`, the kernel buffer's leftover; already UNSTABLE `XR 13` / `XR2 11`).
- GT vs ST: POWER-ON, time words (one minute apart), and one residue byte (+2D2 / +26A `$2D` vs `$32`).

### xbsys1 (15-byte records: A F B C D E H L iff IX IY DTA)
- AS-MSX2+ + CLOCK-TIME + CONFIG. vs WSX: #5 ALLOC IX / IY `$F180` / `$E580` (WSX `$F185` / `$E585`; `ix-iy=$0C00`
  holds); #12 DSKRST DE = IX `$F195` (WSX `$F19A`; `DE==IX` holds); BC after GDATE (#6, #8) `$153A` vs `$0724` = the
  RTC's hour:minute at run time. Everything else (VERSION, CURDRV, SELDSK, LOGIN, SETDTA, GDATE's date and weekday,
  STIME's E = 6, the refusals, iff = 1, IY $0314) is the WSX's.
- GT vs ST: the -5 work-area addresses (ST = WSX) and #9 GTIME's seconds (`$18` vs `$17`).

### xbsys2 (23)
- AS-MSX2+ + CLOCK-TIME + CONFIG + **UNKNOWN**. vs WSX: BC after GDATE (#1, #3) hour:minute; #10 / #11 ALLOC IX / IY
  `$F180` / `$E580`; #14 DSKRST DE = IX `$F195`; and **#14's iff = 0** (WSX 1). Record #14 on the GT
  `00 42 9F 0D F1 95 9F 00 00 F1 95 03 14 00 80`, ST and WSX the same with `9A` and iff `01`.
- GT vs ST: #10 / #11 / #14 addresses, and #14's iff (GT 0, ST 1). xbsys1 #12, the same DSKRST with drive A current,
  is iff 1 on the GT: the difference follows SELDSK 1 (#12) before it. UNKNOWN; one run.

### xbsys3 (15)
- AS-MSX2+ + CLOCK-TIME + CONFIG. vs WSX: BC after each GDATE (#1, 3, 5, 7, 10) hour:minute; #13 DSKRST DE = IX
  `$F195`. The SDATE / STIME refusals are the WSX's.
- GT vs ST: the DSKRST address only.

### xchoice1 (30) · xchoice2 (41)
- AS-MSX2+ + CONFIG (+ STALE-BASELINE). vs WSX: CHOICE's L only (+07 in x1 #0 / x2 #0, and its repeats +25, +43 /
  +30, +D4): HL = `$782A` (WSX `$7852`), a pointer into the turbo R's own disk ROM. A / F kept, MTOFF A = 4, DSKIO's
  C / iff: the WSX's.
- GT vs ST: identical (both `$782A`).

### xdent1 · xdent2 · xdent3 · xdent4 · xdent7
- AS-MSX2+ (byte-identical to the WSX). The VG differences are the WSX's: GETDPB A = 1 / 0 / 2 (working registers),
  DSKCHG F `$2A`, iff = 1, MTOFF A = 4; DSKCHG answers B = 1 "unchanged" within the window (no HB-F900 quirk); GETDPB
  for $FF/$FE/$FC/$FD returns a proper DPB.
- GT vs ST: identical.

### xdent5 · xdent6 (drive A EMPTY; no `@disk`)
- AS-MSX2+ + CONFIG; baseline APPARATUS (a). vs WSX: DSKCHG's L only (xdent5 #1 +25, xdent6 #0 +07 and #1 +25):
  HL = `$EF80` (WSX `$EF85`, VG `$EF97`), a work-area pointer. Against the right VG row (`disk`, drive empty): GETDPB
  on the empty drive returns the same DPB with A = 1, F = 0, iff 1 (VG A = 2, F $20, iff 0); DSKCHG answers A = 2
  (not ready) with F `$45` (VG `$91`), iff 1 — all as the WSX.
- GT vs ST: the same L byte (ST `$85` = WSX).

### xdfmt1 · xdfmt2 · xdfmt3
- AS-MSX2+ (byte-identical to the WSX) (+ STALE-BASELINE for xdfmt1). Choice 0 refused with A = $0C, formats return
  A = 0 with the WSX's BPB / FAT bytes; xdfmt2 / xdfmt3 now have readings on both sides (m1on2 apparatus (b) is closed
  for the turbo R). Baseline for 2 / 3: `AE_m1on2_vgdisk_xdfmt.out`.
- GT vs ST: identical.

### xdrvtbl
- AS-MSX2+ (byte-identical) (+ STALE-BASELINE). DRVTBL slot and H.PHYD's slot byte `$8B` (VG `$81`), 2 drives.
- GT vs ST: identical.

### xdsk1 · xdsk2 · xdsk3 · xdsk4 · xdsk5 · xdsk6 (PHYDIO, 14-byte records)
- AS-MSX2+ (byte-identical) (+ STALE-BASELINE for 1, 2, 4, 5, 6). The VG differences are exactly the WSX's: iff 1 after
  every case; C `$3C` after a read; past-end / straddle cases A `$0C` F `$55` (x1 #3, 4, 10; x2 #14, 15, 17; x4 #51,
  53; x5 #64 with B = 3, #68; x6 #71); x6 #73 "read 2 from $FFFF" A = 0 with zeros; x4 #49 media $FF sector 700 A = 0.
  xdsk3 completed on both turbo R models (it hung on the 8250 / HB-F900 in AE_m1on2).
- GT vs ST: identical.

### xdskio1 · xdskio2 · xdskio2p
- AS-MSX2+ (byte-identical) (+ STALE-BASELINE for xdskio2p). iff 1, C `$3C`, past-end A `$0C` / F `$55` (x1 #3, 4,
  10; x2 / x2p #0, #4) as the WSX.
- GT vs ST: identical.
