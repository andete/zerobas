# D-TRSPEC triage: MSX1 non-disk probes on the turbo R

The probes come from `scratchpad/trall_cmp.py`'s list. Each one either differs from the FS-A1WSX (MSX2+) reading or has
the A1GT and the A1ST disagreeing. That covers 25 MSX1 probes, plus the three MSX2 probes whose verdict was "SAME +
GT/ST DIFF" (xva, xva2, xva14). The disk / BDOS probes belong to another triage, except xrrnd1, which was in this
list.

Sources:
- the turbo R run: `scratchpad/AE_trall/<probe>.out` (`CAP ref` = A1GT, `CAP ours` = A1ST);
- the A1WSX reading: `scratchpad/AE_m1on2/<probe>.out` (row `msx2p`, current probe), or `AE_<probe>_msx2.out`;
- the VG-8020's committed reading, which `trall_cmp.py` picks.

Each byte is decoded by case and field from the probe's header and case table or its `*_cases.py` decoder. The
D-MSX1ON2 triage files (`m1on2-triage-{vdp,gfx,slots}.md`) were reused. Clean room: captures and probe sources only,
and nothing was run.

Classes:
- **AS-MSX2+**: the turbo R reads as the A1WSX.
- **NEW-TR**: the turbo R BIOS does something else.
- **CONFIG**: the machine differs, not the call (slot map, no cassette port, input wiring, boot leftovers).
- **TIMING-CPU**: an interrupt or key scan that happened or did not, JIFFY, the RTC time. Every run here was in Z80
  mode at the dump (`cpu=z80`).
- **POWER-ON**: a RAM cell the probe never writes.
- **STALE-BASELINE**: the baseline predates the probe.

## Summary

Counts: 28 probes. Classes are combined per probe, and each probe counts once under its most important class:
- **NEW-TR: 8** (xinit, xinit4, xinp1, xtap2, xtap3, xtap4, xsnd1, xsnd1b; the last two only for BEEP's C)
- **CONFIG: 11** (xenaslt, xrdslt, xinit3, xinitio, xinitio2, xinitio3, xinitio4, xinitio5, xscank, xvdpreg, b5sound)
- **TIMING-CPU: 4** (xchg2, xinitio6, xinitio7, xrrnd1)
- **POWER-ON: 1** (xsetw)
- **AS-MSX2+: 4** (xpsgr7, xva, xva2, xva14; their only A1GT-vs-A1ST byte is POWER-ON)
- UNKNOWN: 0
- STALE-BASELINE: none affects this triage. It was done against the A1WSX reading, which was run with the current
  probes; several VG-8020 baselines are flagged "probe newer than baseline" by trall_cmp.py.

**The new turbo R differences (the BIOS, not the machine):**
1. **The cassette entries are stubs** (xtap2 / xtap3 / xtap4). Pages: docs/bios/STMOTR.md, TAPOON.md, TAPOOF.md,
   TAPIOF.md.
   - STMOTR returns A and F as entered and does not touch port C's motor bit (R-SM-MOTOR / R-SM-AF fail).
   - TAPOON, TAPOOF and TAPIOF return at once with the carry SET (F $01, or $09 with entry F $00). BC, DE, HL and port
     C are kept, and interrupts are NOT enabled (WSX: EI after TAPIOF / TAPOOF). TAPOON returns A $00 / F $01 and does
     not write the leader or start the motor (R-TN-OK / MOTOR / PORT fail).
   - TAPION / TAPIN / TAPOUT were not read: xtap1 / xtap5 cannot run, because the harness's `@tape` needs a cassette
     player.
2. **GTPDL does nothing** (xinp1 cases 60-63; docs/bios/GTPDL.md).
   - It returns A $00, F $44. BC, DE and HL are kept ($1357 / $9BDF / $2468), PSG R15 is not written ($CF), and the
     interrupt state is kept: DI stays DI.
   - The WSX (and the VG-8020) read the paddle: A $FF, the working values in BC / DE, R15's port bit set, and EI.
   - R-PD-A, R-PD-PORT and R-PD-EI fail. R-PD-KEEP holds, and more than holds.
3. **GTPAD's side effects** (xinp1 cases 54-59, 64, 65, 94; docs/bios/GTPAD.md). A is as on the WSX in every case.
   - The working registers differ: E $00 not $68, HL $2400 not $FFFF / $0CEC / $03D3, L $00 not $68.
   - A = 1 / 2 entered with DI return with interrupts ON on the turbo R. The WSX keeps DI.
4. **INITXT / INIT32 key line at the out-of-range widths** (xinit cases 1, 23, 39; xinit4 16, 19, 20;
   docs/bios/INITXT.md R-I-KEYEDGE / R-I-W0 / R-I-EDGE4, and INIT32.md).
   - INIT32 with LINL32 = 255 and the key line on: row 13 shows only "key0" at column 18. Every earlier machine (VG-8020,
     HB-F900, NMS 8250, FS-A1WSX) shows "key0" and then "key1" at column 34.
   - At width 0 with the key line on (INITXT and INIT32), the name-table and pattern-table sums differ from the WSX's
     (e.g. INITXT w0: namesum $8301 → $9501, patsum $AA66 → $AA65).
   - At the in-range widths nothing differs.
5. **BEEP leaves C = $29**, not $D0 (xsnd1 73 / 74, xsnd1b 11-13; docs/bios/BEEP.md). The register is unpublished.
   Everything else BEEP leaves is as on the WSX.

**Machine facts that show in many probes (CONFIG, not the calls):**
- PSG R14 bit 7 (the cassette input) reads 0 on the turbo R; the WSX reads 1. It shows in xinitio*, xinp1, xsnd1*,
  b5sound and RDPSG(14) (xsnd1 13).
- **Slot 0 is expanded and its secondary register reads $00** (SLTTBL slot 0 = $00; the WSX has $F0). RAM is 3-0
  ($83), as on the WSX.
- The A1GT and the A1ST differ in boot leftovers: BUF ($F55E) holds "512" on the A1GT and "256" on the A1ST, which
  fits their RAM sizes in KB. They also differ in power-on RAM content.
- TRGFLG's boot value is $89 (WSX $9F).
- $FCB1 = $02 and $FFFD / $FFFE (CHGCPU's temporary SP) differ from the WSX's work area (xscank).

**A1GT vs A1ST:** every disagreement in these 28 probes is POWER-ON (a cell no case writes), TIMING (whether the timer
interrupt ran: port C's key-row nibble, R15 after WRTPSG, NEWKEY), or a boot leftover. Not one is a call behaving
differently on the two models.

## Per probe

Offsets are into the turbo R capture (`CAP` + 1). "WSX → GT" gives the value on the FS-A1WSX and then on the FS-A1GT.

**xchg2** — TIMING-CPU. GT = ST.
- Field 60 of the 83-byte record is the byte before KEYBUF, $FBEF = NEWKEY row 10. The probe presets it to $A5, and
  the key scan writes $FF.
- WSX and GT flip between $A5 and $FF in different cases (records 0-13), i.e. whether a key scan ran inside the case.
- The work-area change counts (+64) follow it. CHGET / CHSNS's own outputs are identical to the WSX's.

**xenaslt** — CONFIG. GT = ST.
- Header +06 and each record's +5: SLTTBL slot 0 is $F0 on the WSX and $00 on the GT. Slot 0 is expanded on both
  (EXPTBL $80), so the probe leaves no junk there, and the live secondary register differs.
- ENASLT's A, F, IFF, the witnesses and `moved` are as on the WSX.

**xrdslt** — CONFIG + POWER-ON.
- +06: SLTTBL 0 $F0 → $00 (as xenaslt).
- +4C, +F4, +130, +190 are field +B, the pre-witness: the RAM byte before WRSLT, i.e. power-on RAM.
- GT vs ST: +1C, +F4, +130, +190, +1B4, all the same pre-witness field: POWER-ON.
- RDSLT / WRSLT's results are as on the WSX.

**xinit** — NEW-TR. GT = ST.
- Case 1 (INITXT width 0, key on): namesum $8301 → $9501, patsum $AA66 → $AA65.
- Case 23 (INIT32 width 0, key on): namesum $BC01 → $9001, patsum $AA59 → $AA52.
- Case 39 (INIT32 width 255, key on): namesum $D101 → $4901, and row 13 loses its second label ("key1" at column
  34). Every other case is identical.
- docs/bios/INITXT.md R-I-W0 / R-I-KEYEDGE, INIT32.md.

**xinit3** — CONFIG. GT = ST.
- Cases 0 / 1 (INITXT width 40, copies $5A): vsum (all 16 KB) and col[0] (the VRAM byte at RG3SAV x $40 = $1680)
  differ.
- These cells already differ among the MSX2s (8250, F900 and WSX all differ), which fits a machine-specific VRAM
  content such as the font. The rules' cells are identical.

**xinit4** — NEW-TR + CONFIG. GT = ST.
- Cases 16 (INITXT w0 key on), 19 (INIT32 w0 key on) and 20 (INIT32 w255 key on): the name / pattern sums and the
  missing "key1" (rows 13 and CRTCNT) are xinit's finding.
- vsum / col[0] in 16, 18, 19 and 20 are xinit3's CONFIG.

**xinitio** — CONFIG + TIMING-CPU. GT = ST.
- R14 (record field 28 in the 105-byte record from +1): $FF → $7F in all 5 cases. Bit 7 is the cassette input.
- Case 0 changed 21 work-area cells, not 20: $F3E7 (STATFL) := $9F. A VDP status read by an interrupt; STATFL is not
  in this round's skip list.
- INITIO's PSG R0-R13, R15, port $AA and the queue cells are as on the WSX.

**xinitio2 / xinitio3** — CONFIG. GT = ST. Only R14 bit 7 differs (field 35 of each 224-byte record).

**xinitio4** — CONFIG + TIMING-CPU. GT = ST.
- R14 bit 7 differs.
- Port $AA (field 37) is $35 → $3A in record 0 and $CA → $C3 in record 1. Only the low nibble (the key row) differs:
  where the last key scan before the window left it. It is not INITIO's.

**xinitio5** — CONFIG + TIMING-CPU. GT = ST.
- R14 bit 7 differs.
- The JIFFY witnesses (before / after, low byte) are $37 / $38 / $39 / $3A → $36 / $37 / $38: boot timing. No case's
  window was dirty on either machine.

**xinitio6** — TIMING-CPU. GT = ST. JIFFY before / after, low byte: $37 → $36 in all 5 records. Everything else is
identical.

**xinitio7** — TIMING-CPU. GT = ST.
- JIFFY low: $38 / $39 → $36.
- Tries (+4): the WSX's case 0 and case 3 took 2 tries, the turbo R's 1. The recorded try's results are identical.

**xinp1** — NEW-TR + CONFIG. GT = ST.
- R14 (field 14 of the 48-byte record) $FF → $7F in all 95 cases (CONFIG).
- GTPDL, cases 60-63: A $FF → $00, F $BA → $44, BC $01FF / $20FF → $1357, DE $03AF / $4C9F → $9BDF (all kept), IFF
  1 → 0 when entered DI (60-62), R15 $8F → $CF (the port select not written).
- GTPAD:
  - A 0 / 3 / 4 / 7 (cases 54, 57, 58, 59, 64): E $68 → $00, HL → $2400.
  - A 1 / 2 (55, 56, 65, 94): L $68 → $00, and IFF 0 → 1 (55, 56: interrupts on after the call on the turbo R).
- SNSMAT, KILBUF, CHGCAP, GTSTCK, GTTRIG, BREAKX, ISCNTC and CKCNTC are identical to the WSX's.

**xrrnd1** (a BDOS probe) — TIMING-CPU + POWER-ON.
- The FCB's time field (+22 / +23) in every record: $3CA8 (07:37) on the WSX, $ADA6 (21:45) on the GT. That is the
  RTC time of day when the file was made; the date ($5D77, 2026-11-23) is the same.
- Header +02..+25: an alternating $00 / $FF pattern that no case writes (POWER-ON). It also differs GT vs ST.
- The records' data bytes are identical. This disk probe is otherwise outside this triage.

**xscank** — CONFIG + TIMING-CPU (+ POWER-ON GT vs ST).
- SCANR's HL is identical in all 3 cases. The work-area dump ($F380-$FFFF) differs only in machine cells:
  - BUF $F55E-$F609: boot leftovers. "512" on the GT, "256" on the ST.
  - $FAFF, $FB01.
  - SCNCNT $F3F6, JIFFY $FC9E, $FCA2: timing.
  - $FCB1 = $02: the turbo R's CHGCPU byte.
  - SLTTBL 0 $FCC5: $F0 → $00.
  - $FEFF, $FFF8.
  - $FFFD / $FFFE: CHGCPU's temporary SP.
- GT vs ST: BUF "512" / "256", and the power-on bytes past the third record (+2589..+25FF).

**xsnd1** — CONFIG + TIMING-CPU + NEW-TR (minor).
- R14 bit 7 in every record. RDPSG(14) in case 13 returns A $FF → $7F.
- Port $AA's key-row nibble (field 29) flips $50 ↔ $5A / $D0 ↔ $DA (timing).
- BEEP (cases 73, 74): C $D0 → $29.
- GT vs ST:
  - port $AA's nibble (records 72-80, 104-106);
  - R15 after WRTPSG R15 := $80 / $C0 (cases 105 / 106): GT $CF / $C0, ST $80 / $CF. WRTPSG.md already says R15 after
    the call is the timer interrupt's (interrupts are on afterwards), so this is TIMING.

**xsnd1b** — CONFIG + TIMING-CPU + NEW-TR (minor). GT = ST.
- R14 bit 7.
- Port $AA nibble flips.
- BEEP (cases 11-14 here): C $D0 → $29.

**xtap2** — NEW-TR. GT = ST. All 19 records are of the form A, F, BC, DE, HL, IFF, port C.
- **STMOTR** (records 0-10):
  - A and F come back as entered (WSX: A $09 / $08, F $54 / $10 / $38).
  - Port C keeps the preset: $A0, $E0, $F0, $50, $40 stay. On the WSX the motor bit moves: $A0 → $B0, $50 → $40.
- **TAPIOF / TAPOOF** (records 11-18):
  - F $09 / $01 (carry set), not $00.
  - IFF stays 0 (WSX 1).
  - Port C is kept (WSX: bit 4 := 1, motor stopped).

**xtap3** — NEW-TR. GT = ST.
- STMOTR as in xtap2: A / F as entered, port C kept.
- TAPOON (records 9, 11): A $00 / $FF, F $01 (carry: error). BC and HL are kept (WSX: $0000 / $0000, A / F $10). DE is
  kept on both. Port C is kept (WSX: $47, motor on).
- TAPOOF (10, 12): F $01, IFF 0, port C kept.

**xtap4** — NEW-TR. GT = ST.
- STMOTR as above.
- TAPOON with port C $E0 / $A5: carry set, port C kept (WSX: $C7 / $87).
- TAPOOF: F $01, DI kept, port C kept.

**xvdpreg** — CONFIG. GT = ST.
- Header +01 and field 15 of every 32-byte record: $F3E8 (TRGFLG, the boot copy the probe restores) is $9F on the WSX
  and $89 on the GT. That is the machine's trigger / port-A input state.
- WRTVDP, DISSCR, ENASCR and RDVDP are identical to the WSX's.

**b5sound** — CONFIG. GT = ST. +0E: RDPSG(14) as the cartridge finds it, $FF → $7F (R14 bit 7).

**xpsgr7** — AS-MSX2+. GT vs ST: +0E, $FF / $00, a cell past the sentinel that the probe does not write (POWER-ON).

**xsetw** — POWER-ON. GT = ST. +00 is not written by the probe: VG $00, WSX $FF, turbo R $00. Everything else is as
on the WSX.

**xva / xva2 / xva14** (MSX2 probes) — AS-MSX2+ (identical to the A1WSX).
- GT vs ST: +0C, $00 / $FF. That is the 5th slot of record 0's port-$99 write log, and record 0 made only 4 writes, so
  the slot is never written: POWER-ON.
