# D-TRSPEC triage: the MSX2 / MSX2+ probes on the turbo R

Source: the per-probe file in `scratchpad/AE_trall/` (`trall_run.py`: FS-A1GT = "gt", FS-A1ST = "st"), set against the
newest committed FS-A1WSX reading (`msx2p` row, picked by `scratchpad/trall_cmp.py`), and, to see what a byte does on
the MSX2s, the same file's NMS 8250 (eu) and HB-F900 (jp) rows. Values below are written eu/jp/wsx | gt/st. Each byte
was decoded by case and field from the probe's header. Clean room: captures and probe sources only; nothing was run.
`trall_cmp.py` counts raw bytes; most of them are not BIOS differences, and this file says which ones are.

## Summary

67 MSX2 / MSX2+ probes. Classes (each probe once, by its most significant difference):

| class | n | probes |
|---|---|---|
| SAME (gt = st = wsx) | 15 | xbf xenaslt2 xplt xrdslt2 xspr2 xspr3 xsubcls xsubfnk xsubgc xsubgpp xsubgpp2 xsubmv xsubmv2 xsubscan xsubscan2 |
| SAME except gt-vs-st on a power-on byte | 3 | xva xva2 xva14 |
| POWER-ON RAM only (cells no case writes: the capture's last byte, an unused log slot, the tail past the last record) | 15 | xchknew xeol xextrom xextrom0 xextromnx xsubdln xsubdln2 xsubdln3 xsubdln4 xsubpch xsubpch2 xsubpch3 xsubctx xsubpmt xva3 |
| TIMING / CLOCK only (VDP S#2 read at a random moment, JIFFY / INTCNT / SCNCNT counters, PSG-log timestamps, the clock chip's time of day, a calibrated timing sweep), sometimes with a BOOT-STATE byte (R#36) | 17 | xclk xva16 xsubblt xsubknj xsubscr xsubsc2 xsubgc2 xsubbox xsubbox2 xmode2 xsubkyk xsubkyk2 xsubkyk3 xsubkyk4 xsubpvr xsubpvr2 xsubpvr3 |
| CONFIG (the machine: boot state, BASIC version banner, a ROM-internal register left over, PSG port A input); the call behaves as on the A1WSX | 6 | xmode xwv xsubbeep xsubbltd xsubset xsubpadg |
| NEW-TR (the turbo R's BIOS / I/O behaves differently from the MSX2+) | 10 | xf4port xrdres xf4reset xchkslz0 xchkslzd xsubpad xsubpadb xsubpadm xsubpadx xsubpads |
| APPARATUS (not comparable as run) | 1 | xva13 |

GT-vs-ST: they agree on every behavioural byte EXCEPT CHKSLZ (xchkslz0 / xchkslzd); every other gt-vs-st difference is
power-on RAM, VDP S#2 / timing, the clock's seconds, or a ROM-internal leftover (xsubbltd IX, BASIC 4.1 vs 4.0 banner).

The NEW turbo R differences, most important first:

1. **Port $F4 / RDRES / WRRES are inverted relative to the FS-A1WSX** ([RDRES.md](../docs/msx2/main/RDRES.md),
   [WRRES.md](../docs/msx2/main/WRRES.md); xf4port, xrdres). Port $F4 on both turbo Rs reads back bit 7 = the bit
   written, bit 5 = 1, bits 6 / 4-0 = 0 (A0 / 20), where the A1WSX reads bit 7 and 7F in the other bits (FF / 7F)
   and the MSX2s always FF; at INIT the turbo R reads A0 (bit 7 = 1), the A1WSX 7F (bit 7 = 0). RDRES on the turbo R
   returns A = the port as read (A0 / 20) with F unchanged from entry; on the A1WSX A = $80 when the port's bit 7 is 0
   and $00 when 1, F changed (12 / D7 / ...). WRRES on the turbo R leaves A and F as entered and sets the port's bit 7
   := A's bit 7 (A $00 -> port 20, A $80 -> A0); on the A1WSX bit 7 := NOT A's bit 7 and F / A change. Every RR / WR
   rule on those pages names the MSX2+'s sense and needs a turbo R row.
2. **CHKSLZ: the FS-A1GT never returns and never re-boots; the FS-A1ST re-boots as the FS-A1WSX does**
   ([CHKSLZ.md](../docs/msx2/main/CHKSLZ.md); xchkslz0, xchkslzd). The GT's VRAM log holds 'B' (before the call)
   only: no 'R', no INIT re-entry; with EXBRSA $A5 (xchkslzd) its work area is garbage at the dump (JIFFY $E5D5,
   NEWKEY / H.KEYI / H.TIMI overwritten). The ST (like the A1WSX) shows the 'B' wiped and our INIT entered twice
   ('I', 8E F0, F4 twice at $3F20). The NMS 8250 / HB-F900 returned ('R' logged). The only behavioural A1GT-vs-A1ST
   disagreement found in the MSX2 probes.
3. **NEWPAD functions 0-11 (touch pad 0-7, light pen 8-11) do nothing on the turbo R** ([NEWPAD.md](../docs/msx2/sub/NEWPAD.md);
   xsubpad, xsubpadb, xsubpadm, xsubpadx, xsubpads): through the sub-ROM's NEWPAD and the main ROM's GTPAD alike they
   return A = $00, F = $44 and BC / DE / HL as entered ($1357 / $2468 / $369C), on both turbo Rs. The A1WSX returns
   computed values there (e.g. fn 9: A 0 or 1, F $BB, BC $40FF, DE $240F, HL $20DF). Functions 12 and up (mouse /
   track ball, 24-255) match the A1WSX, except which joystick port PSG R15 bit 6 is left selecting after some mouse
   calls (8F vs CF, in either direction; also xsubpadg).
4. **A soft reset by JP $0000 never gets back to the cartridge on the turbo R** ([RDRES.md](../docs/msx2/main/RDRES.md) RR-7,
   [WRRES.md](../docs/msx2/main/WRRES.md) WR-3; xf4reset): no reading on either turbo R; at the 120 s dump the whole
   capture, JIFFY ($FFFF), SCNCNT and NEWKEY read $FF -- not even boot 1's record survived. What the machine is doing
   then cannot be told from this probe (it needs one that logs to VRAM, as xchkslzd does).

Work-area / boot-state facts the turbo R adds (CONFIG, not a call's behaviour): $FFFD-$FFFE = $F054 on both turbo Rs
(MAP's "temporary stack pointer for CHGCPU"; $00 / $FF elsewhere), $FFF8 = $FF (as the HB-F900; $00 on the NMS 8250
and A1WSX), VDP R#16 = $0F and R#36 = $80 as the boot leaves them, PSG port A (R14) reads $7F (bit 7, the cassette
input, 0: the turbo R has no cassette port), SETSCR's banner "MSX BASIC version 4.1" (A1GT) / "4.0" (A1ST).

## Per probe

Offsets are into the capture block, hex; "rec" = the probe's per-case record.

### NEW-TR

- **xf4port** -- NEW-TR. +0 IN $F4 at INIT FF/FF/7F | A0/A0; per written value v (00 FF A5 5A 80 7F 01 FE 00) the
  read-back FF/FF/(7F|FF) | 20 or A0 = bit 7 of v, bit 5 set. +15 onward: past the sentinel, power-on RAM (gt/st
  differ there only). GT = ST.
- **xrdres** -- NEW-TR. Every record's port bytes (rec +3 before, +30 after) 7F/FF on the A1WSX vs 20/A0; RDRES rec
  +28/+29 (F, A) e.g. case 0 (port bit 7 = 0): wsx F $12 A $80 | gt F $00 A $20; WRRES case 5 (A $00): wsx port after
  FF, A $FF F $3A | gt port after 20, A $00 F $00. Registers other than AF identical. GT = ST. (The MSX2s have no
  entry there; their rows are not readings.)
- **xf4reset** -- NEW-TR (no reading). DONE never set on gt and st; all 32 bytes $FF (wsx: 3 stages, port 7F/37...).
  GT = ST.
- **xchkslz0** -- NEW-TR, GT/ST DIFF. VRAM $3F00: wsx 00 (wiped by the re-boot) | gt 'B' / st 00; $3F20-$3F27: wsx
  'I' 8E F0 F4 x 2 | gt 00 / st the same as wsx. CAP +0 (the unwritten capture byte): FF on wsx, 00 on gt and st.
  gt dump: cpu r800, JIFFY $007D, work area sane -- it sits somewhere without returning.
- **xchkslzd** -- NEW-TR, GT/ST DIFF. As xchkslz0 (EXBRSA $A5 instead of $00); the GT's work area is overwritten at
  the dump (cpu z80, JIFFY $E5D5, NEWKEY and the hooks garbage).
- **xsubpad** -- NEW-TR. Records 0-3 and 26-29 (fn 8-11, NEWPAD and GTPAD paths): A/F/BC/DE/HL as stated in the
  summary (item 3); rec 20 (fn 12): R15 after wsx CF | 8F. GT = ST.
- **xsubpadm** -- NEW-TR, the same records as xsubpad with a mouse plugged: fn 8-11 do nothing; fn 12's R15 CF | 8F.
  GT = ST.
- **xsubpadb** -- NEW-TR. Records 11, 12, 14, 16 (fn 9, 10, 0, 9): wsx A $01 (or 0) F $BB/$42 with BC/DE/HL computed
  | A 0, F $44, registers as entered; rec 18 (fn $16) R15 CF | 8F. GT = ST.
- **xsubpadx** -- NEW-TR. Records 0-7 (fn 0-7 through NEWPAD): wsx F $BB/$42/$44, BC $40FF DE $240F HL $20DF | F $44,
  registers as entered; rec 4 R15 8F | CF. Functions 24, 31, $80, $FF: same. GT = ST.
- **xsubpads** -- NEW-TR. All 257 functions: fn 0-11 as above (A 0, F $44, untouched; wsx computes); fn $12 / $24 /
  $36 and a few more: R15 bit 6 differs (also gt vs st on fn $47 / $48); every other function SAME. The record's two
  trailing zero bytes (+14 / +15) are not written by the probe: 00/FF power-on noise on ~190 records.

### CONFIG

- **xmode** -- CONFIG. Rec +57 = $FFF8 (from the $FFE7-$FFFC copy, +40..+61), every case: 00/FF/00 | FF/FF -- the
  boot's value, untouched by every screen-mode call. Nothing else differs. GT = ST.
- **xwv** -- CONFIG + timing. WRTVDP records: +41 ($FFF8) 00/FF/00 | FF/FF; +46 / +47 ($FFFD / $FFFE) 00/FF/FF and
  FF/FF/00 | $54 / $F0 on both (the CHGCPU stack pointer cell); +13 (an unused port-write slot) power-on. Phase 3
  (CAP+$840, 38-byte records): case C $10 enters with VDP R#16 = $0F on the turbo R ($00 on the A1WSX), so B (its own
  value XOR $0F) is $00 there and the work-area diff gains $FFEF; the other phase-3 diffs are SCNCNT ($F3F6), JIFFY,
  INTCNT new values (timing). VDPSTA records: S#2 only. Phase 4 identical. GT vs ST: power-on bytes and the timing
  cells only.
- **xsubbeep** -- CONFIG + timing. All 27 cases: the PSG write sequence (register, byte) is IDENTICAL to the A1WSX's,
  same lengths; only the microsecond timestamps differ (the turbo R reaches each case ~0.3 s earlier) -- the bulk of
  the 7243 bytes. Rec +4 (C after) $D0 on all three MSX2s | $29 (cases 0-3, 18): a ROM-internal leftover, C is not an
  output. Rec +19+14 / +35+14 (PSG R14 = port A input) BF/BF/FF | 7F: bit 7 (cassette input) reads 0 on the turbo R.
  Rec +62 / +63 unwritten (power-on). Header (block 2 registers at INIT) as the HB-F900 / A1WSX. GT = ST except
  timestamps.
- **xsubbltd** -- CONFIG + timing. Rec +12 (IX low after, disk BLT cases 0, 1, 9, 13, 16, 17, ...): 97/96/85 | 80/85 --
  ROM-internal, differs between every machine incl. GT vs ST. Rec +31 / +194 S#2 (timing). Case 16's window +48..+79
  unwritten (power-on 00/FF). No change in A, F, the block, the files.
- **xsubset** -- CONFIG + timing. Rec +208 (row 0) and +424 (the "MSX" log hit): the banner SETSCR prints, "MSX BASIC
  version 2.1" (eu) / "3.0" (wsx) / **"4.1" (A1GT) / "4.0" (A1ST)**. Rec +124 (R#36 in @vdpfull, case 0-1): 88/60/70 |
  80/80 (the boot's last VDP command). Case 7's work-area diff entries $FC9E / $FCA2 (JIFFY / INTCNT): timing. S#2.
- **xsubpadg** -- CONFIG. Only rec 3 (fn $16, GTPAD path): R15 after 8F | CF (which port is left selected). GT = ST.

### TIMING / CLOCK

- **xclk** -- CLOCK. REDCLK records for block 0 registers 0-5 (seconds, minutes, hours) and the R2 / W2 copies: A and
  F (F follows A), and the registers read by port -- the time of day when the run happened (openMSX's clock chip; the
  baseline ran at another time). MODE before / after, every block 1-3 settings register, WRTCLK: identical. GT vs ST:
  the seconds only.
- **xva16** -- TIMING. Rec +14 / +15 (the calibration, loop iterations per frame): 10/3D/29 | **2A**/29 -- the A1GT
  counts one more iteration per frame than the A1ST and the A1WSX; with it every step's interrupt lands one NOP
  elsewhere, which moves the mark (+2), the logged writes (+3), and, for the steps where the interrupt lands between
  two port writes, R#14 / the pointer (+5..+7) and the SP-depth / port-$98 bytes from +$2404 / +$2644. The SP depths
  seen are the same values (1C-26) as on the MSX2s. No new outcome kind.
- **xsubblt / xsubknj / xsubscr** -- TIMING. Rec +19 (xsubblt, xsubknj) and the S#2 cell of xsubscr: S#2 read at a
  random moment (bits 7 TR, 6 VR, 5 HR, 1 EO vary; 0C/0E/2C/2E/4C/4E/8C/8E/AC/AE); varies among the MSX2s and gt vs
  st as well. xsubscr also rec +124 (R#36, case 0): 88/60/70 | 80/80 (boot state).
- **xsubsc2** -- TIMING. S#2; R#36 (rec +124) 70 | 80; case 1's work-area diff entries for JIFFY / INTCNT one count
  apart.
- **xsubgc2** -- TIMING. STATE records (122 bytes from +5): +44 = R#36 70 | 80 (boot), +74 = S#2.
- **xsubbox / xsubbox2** -- TIMING. Rec +1 / +2 (A, F) in cases 3, 6 (xsubbox) and 7-9 (xsubbox2): A is an S#2 read
  (0E / 0C / 2E) and F follows it -- the A1WSX already returns that (eu/jp $00 / $54); the turbo R values are the
  same kind. GT vs ST differ in the same way.
- **xmode2** -- TIMING. S#2 cells (68 bytes), 35 power-on bytes, rec +174 (R#36 before, case 0) 70 | 80, case 27 +93 /
  +207 one count apart (79 | 7A/79). Every register, VRAM sum and work-area byte else identical.
- **xsubkyk / xsubkyk2 / xsubkyk3 / xsubkyk4** -- TIMING. Rec +32.. (changed work-area bytes): the JIFFY ($FC9E) /
  INTCNT ($FCA2) new values (counters); in case 0 the turbo R also changes STATFL ($F3E7: $89 -> $9F, an interrupt
  read S#0) -- +18 (count) 04 | 05 and the list shifted by one entry; rec +12 (IY low after, case 1) 23/33/33 | 37
  (ROM-internal); rec +256.. (PSG log timestamps). KANAST / CAPST / port $AA / PSG writes identical. GT vs ST: the
  timestamps only.
- **xsubpvr / xsubpvr2 / xsubpvr3** -- TIMING. Rec +182..+191 (the VRAM-sum / counter pairs that move with JIFFY) one
  count apart; rec +340 / +454 (R#36 in the two @vdpfull blocks) 88/60/70 | 80/80; S#2 (24 / 16 / 24 bytes); case 8
  +371 / +373 one count. GT vs ST: S#2 only.

### POWER-ON RAM only

- **xchknew, xextrom** (+4FF), **xeol** (+147F), **xextrom0, xextromnx** (+3F), **xsubdln** (+19FF), **xsubdln4** (+28FF),
  **xsubpch** (+FFF), **xsubpch2, xsubpch3** (+3FF) -- the capture's last byte, which the probe's clear loop stops one
  short of (xextrom0: `ld bc, $003E`): 00 on the MSX2s and the A1ST, FF on the A1GT. Not a reading.
- **xsubdln2** (20 cases, records end +1902), **xsubdln3** (12 cases, end +F02), **xsubctx** (16 cases, end +1802):
  the alternating 00/FF pattern past the last record -- each machine's power-on RAM fill, which differs between gt and
  st too.
- **xsubpmt** -- the unused slots of the H.CHPU log (rec +25..+72) in all 20 records: power-on 00/FF.
- **xva3** -- case 0 only: rec +10 (a port-$99 slot NSETRD did not use) 00/FF/00 | 00/FF and +19 (the first port-$98
  write, none in that call) FF/FF/00 | FF/FF.
- **xva, xva2, xva14** -- SAME against the A1WSX; gt vs st differ only in case 0's rec +10 (the same unused slot).

### APPARATUS

- **xva13** -- not comparable. The probe must run on machines CONFIGURED with 64 KB of VRAM (scratchpad/xva13_run.py
  writes those configs); trall_run.py ran it on the stock turbo Rs (128 KB). The differences (rec +0, A after
  NRDVRM, in cases 12 / 17 / 22 / 82 / 87 / 97 ...: FF on every MSX2 | 00 / C7 / 44) are what a 128 KB VRAM reads
  back, not a BIOS difference; cmp also flags the probe newer than its baseline. Needs an xva13_run.py-style turbo R
  run (a 64 KB-VRAM turbo R config) if the question matters.
