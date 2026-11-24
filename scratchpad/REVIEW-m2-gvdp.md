# Goldfish review (test-writer role), 2026-11-23: concepts/vdp-and-palette.md, sub/WRTVDP.md, sub/VDPSTA.md, sub/INIPLT.md, sub/RSTPLT.md, sub/GETPLT.md, sub/SETPLT.md, sub/CHGCLR.md, sub/CLS.md

**Records decoded by hand** (layouts from the probe headers):
- `AE_xwv_msx2.out`: the reference rows only. NMS 8250: the WRTVDP records C 0, 1, 8, 9, 14, 15, 16, 24, 46 field by field, and the rest spot-checked (A / F / B / C, the port $9B count). FS-A1WSX: C 0, 24, 25, 26, 27. HB-F900: C 0, 7, 9. All 30 VDPSTA records (10 per machine).
- `AE_xplt_msx2.out`: the NMS 8250 reference, the 6-byte register header of all 17 steps, plus the palette and table of steps 0-9, 11, 13, 15 and 16. HB-F900 / FS-A1WSX: register headers checked equal, and the SCREEN 0 / 1 tables differ only by font data.
- `AE_xsubcls_msx2.out`: all 21 NMS 8250 reference records. The HB-F900 and FS-A1WSX reference strings were compared with it and are identical.

**Not decoded:** the C-BIOS ("ours") rows beyond what the DIFF lines show. The `*_decode.py` scripts are named on the pages but not linked, so they were not read.

## 1. Rules not pinned by any measured case

1. **CLS** (SCREEN 2, 3): the windows were the first 16 bytes of the name, pattern and colour tables (`xsubcls.asm` cases 9-12). Nothing pins the fill's extent: all 6144 pattern and colour bytes, all three thirds, or where SCREEN 3's pattern fill ends. To pin it, read the last 16 bytes of $0000-$17FF and $2000-$37FF (SCREEN 3: $0000-$05FF), and the 16 bytes just past each.
2. **WRTVDP**: "C 24 and 28-46 have no copy" and the copy rule for C 0-23 come from only two RAM windows ($F3DF-$F3E6 and $FFE7-$FFFF). RG0SAV + C for C ≥ 8 ($F3E7-$F40D, including STATFL) was never read. A whole-RAM diff per C, as the concept page's recording rule asks, would pin it.
3. **RSTPLT / GETPLT**: "from the mode's VRAM table" is measured in SCREEN 5 only (`xplt.asm` steps 3-7). SETPLT's table write is measured in SCREEN 5 and 8 only. To pin it, repeat the pattern step, RSTPLT and GETPLT in SCREEN 0 (40 / 80), 1 and 8.
4. **GETPLT**: "unmasked" is pinned only for C. B came from table byte 10 = $35, whose bits 3 and 7 are clear. A table byte of $88 or $FF at entry 5 would pin B.
5. **CHGCLR**: "in SCREEN 1 the colour table is filled with $A5" rests on its first 16 bytes only ($2000-$200F). Reading $2010-$201F and $2020 would pin the 32-byte extent.
6. **INIPLT**: R#16 after the call is not recorded, and neither is anything in VRAM outside the one 48-byte table per step. The `xplt.asm` record has no R#16 field. A snapshot read after the call would pin R#16.

## 2. Rules the measured cases could also explain with a different rule

1. **CLS** SCREEN 6: both BAKCLR $06 and $C5 fill $FF. "(BAKCLR rot 4 OR BAKCLR) OR the same rot 2" and "constant $FF" explain both equally. CL-BK's planned $0F and $FF also give $FF under the page's rule, so they cannot separate the two. BAKCLR $01 does: the rule gives $55, the constant gives $FF. $00 and $02 also separate.
2. **WRTVDP** C 0 → R#9 := $12 / $10: three rules fit.
   - (a) A constant per machine.
   - (b) R#9's copy OR $10. The copy was $02 on the NMS 8250 and $00 on the others, as the other records' $FFE8 shows.
   - (c) A function of B. Only B = $0F was ever written.

   To separate them, run C 0 with the R#9 copy preset to $80, and C 0 with B $00 vs $0E. The log also shows R#9 is written before R#0 (`12 89 0F 80`), which the page does not state.
3. **VDPSTA** A 0: F is $44 for A 0 and $9B for A 1-9 on all three machines, which suggests a separate A-0 path. Three readings fit A 0 → $1F:
   - S#0 selected through R#15;
   - port $99 read with no selection;
   - STATFL.

   S#0's bit 7 was 0, STATFL was not recorded and there was no port log. To separate them, preset STATFL distinct, make S#0's F flag pending, and log port $99.
4. **CHGCLR**: SCRMOD vs the register copies' mode bits as the mode source. CHGMOD always set both consistently. CC-AS's third clause separates them.
5. **RSTPLT**: A after is $9E, which is table byte 31 (3 + 31 × 5). "A = the last byte read, so exactly 32 bytes are read" and "A is incidental" both fit. If bytes 32-47 were read, A would be $EE. The page omits A. Bytes 32-47 set distinct, with A recorded, decide RP-03.
6. **GETPLT** "E $00", and **RSTPLT** "D $00, E $00": D and E entered as 0 (the `steps` table), so "set to 0" and "kept" cannot be told apart. Preset D and E to garbage.
7. **INIPLT** / **SETPLT**: "writes the mode's table" is equally explained by "writes the mode's table and other places". Each step read only the expected 48 bytes; for example, SCREEN 0 width 40 might also write $0F00. Preset all six places distinct, then read all six after one call.
8. **CHGCLR**: FORCLR / BAKCLR are masked in SCREEN 0, 1, 2 and 5 and not in 8. Three rules fit: "unless SCRMOD 8", "SCRMOD ≤ 5" and "palette modes only". SCREEN 6 and 7 (and 3 / 4) separate them.
9. **CHGCLR / CLS** interrupts: every case entered with DI (`xsubcls.asm` line 68). So "ON on return" is forced-on vs toggled, and CLS SCREEN 0 / 1 "kept (off)" is kept vs forced off. An EI entry separates both.
10. **WRTVDP** C 8-23: "the copy at $FFE7 + C − 8" vs "that and RG0SAV + C". $F3E7-$F3F6 was never recorded.

## 3. Citations that do not match the tables

1. **GETPLT** "Out: ... D kept": every GETPLT record on all three references reads D = $05 (`04 34 73 04 05 00`, `3a 34 35 3a 05 00`). The `steps` table entered D = 0, so D := A (the palette number), not kept.
2. **WRTVDP**: "C 24 and 28-46 have no copy" and "every write is DIRECT ... for every C up to 46" include C 28-31. `wcases` jumps from $1B to $20, so C 28-31 never ran.
3. **CHGCLR**: the measured paragraph, and case CC-0..8 ("A = SCRMOD = 0..8"), imply A followed the mode. The probe entered A = 0 in every case (`xsubcls.asm` line 91, `xor a`), yet R#7 and the masking changed with SCREEN. So the run already shows the mode is not taken from A. The page and CC-AS still list A vs SCRMOD as open.
4. **vdp-and-palette.md**: line 8 says "DRAFT 0 ... nothing measured yet" beside the [M] paragraph at line 128. The "How every case is recorded" rules (garbage presets in two sets, whole-RAM diff, port log with IFF1) were not used by the runs the pages cite.
   - `xplt.asm`: no RAM read, no port log, BC = $5AA5, D / E = 0.
   - `xsubcls.asm`: no port log, no RAM beyond the colour cells.
   - `xwv.asm`: two RAM windows only.

   So the [M] claims rest on weaker apparatus than the page says every case uses.
5. **vdp-and-palette.md** line 129: "the calls use the FIRST 32 bytes" also claims RSTPLT and GETPLT read only 32 bytes. No case read with bytes 32-47 distinct from 0-31 and checked the result; the only hint is RSTPLT's A = $9E (item 2.5).
6. **CLS**: the measured header says each mode's windows were "the start, last 16 bytes, and the 16 just past". For SCREEN 2 they were the starts of the name, pattern and colour tables. For SCREEN 3 they were the name start, pattern start and name end. Neither got a last-16 or past-end window for the cleared area.
7. **INIPLT** line 28: "the initial values are Table 2.5's" is still [A] beside the measured 32 bytes. The page does not say whether `0000 0000 1106 ... 7707` equals Table 2.5.

## 4. Gaps in the open lists

1. Rows the cited runs already decided are still listed as open:
   - INIPLT: IP-02 (step 9: VRAM got the power-on palette while the VDP held the pattern palette), IP-05, IP-07, IP-11.
   - SETPLT: SP-03 and SP-06; GETPLT: GL-02 (steps 2-5).
   - WRTVDP: WV-01 and WV-02 (direct writes and the copy addresses).
   - CHGCLR: the A half of CC-AS.
   - CLS: CL-BK for $06 / $C5.

   None says which part remains open.
2. **CLS** CL-BK: the planned BAKCLR values ($06, $C5, $0F, $FF) cannot separate the SCREEN 6 rule from a constant $FF. Add BAKCLR $00-$03 (see 2.1).
3. **WRTVDP**: no row covers the C 0 → R#9 side effect. Add one that varies B and the R#9 copy. Also add a scan of every C for writes to a register other than C: the run kept only the first six port writes and a count.
4. **GETPLT** GL-07 and **RSTPLT** RP-08: neither presets or records D and E. Add D / E garbage and record D (GETPLT's D := A), plus RSTPLT's A (2.5).
5. **CHGCLR / CLS**: the IE rows do not note that DI-entry results already exist (2.9). Only the EI-entry half is still missing.
