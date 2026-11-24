# Goldfish review (test-writer role), 2026-11-23: docs/msx2/concepts/screen-modes.md, docs/msx2/sub/CHGMOD.md, docs/msx2/sub/CHGMDP.md, docs/msx2/sub/SETPAG.md

**Records decoded (by hand, from `scratchpad/AE_xmode_msx2.out`, 96-byte records per `probes/bios/spec/xmode.asm`'s
header, CAP dump starting at C001):** NMS 8250 reference records 0, 1, 2, 3, 4, 5, 7, 9, 10, 11, 12, 19, 20, 21, 22;
HB-F900 reference records 0, 19 and the $FFE7-$FFFC block; FS-A1WSX reference records 0, 22 and the $FFE7-$FFFC
block; C-BIOS ("ours") records 0, 3, 5, 19, 22 (EU / JP). **Not decoded:** records 6, 8, 13-18, 23-25 field by field
(read only for A / F / IFF / SCRMOD); `scratchpad/xmode_decode.py` (named by the pages but not linked; not read). The
run file's DIFF lists are truncated (NMS after C255, JP after C1C3, WSX after C22D), so no C-BIOS difference beyond
case 5 can be cited from them.

## 1. Rules not pinned by any measured case

1. **CHGMOD / CHGMDP: VRAM is not captured at all** — screen clear, sprite parking (Y 217), the palette table save
   (CP-SAVE) and "changes nothing" for A 9 / $FF / 10-12 are all unmeasured; the only trace is R#17 = $2C and
   R#14 = $01 / $03 after A 5-8 (a command / CPU write happened). Pin with the 128 KB block sums the open table
   already lists.
2. **CHGMOD / CHGMDP: palette entries are not captured** — "does not touch the palette" (CHGMOD) and "the palette is
   written" (CHGMDP) both rest on R#16 alone. Pin with CM-PAL / CP-PAL (read all 16 entries).
3. **All three calls: BC, DE, HL, IX, IY and the alternates on return are not recorded** by the probe (it saves A / F
   only), so SETPAG's "registers: AF" and CHGMOD's EXTROM claims are unpinned. Pin with SP-REG / CM-IX.
4. **Interrupts on an EI entry** — every case was entered with DI, so CHGMOD's "as entered" is unpinned for EI. Pin
   with the IE rows.
5. **CHGMOD: OLDSCR's rule** — measured OLDSCR = 1 after A 1 and 0 after every other A, but every case began with a
   main CHGMOD 0, so "last text mode", "OLDSCR := SCRMOD if ≤ 1" and "untouched by A 2-8" all fit. Pin with CM-PREV
   (enter A 2 / 5 after SCREEN 1).
6. **CHGMOD: R#10 / R#11 / R#14 for A 0-4 after a mode 7 / 8** — case 0 ran first (R#11 already 0); the direct
   INITXT case 11, run after A 8, left R#11 = $01. Whether CHGMOD 0-4 resets R#10 / R#11 is unmeasured. Pin: CHGMOD 0
   entered from SCREEN 8.
7. **SETPAG: page 2, SCREEN 6 / 7 / 8, and ACPAGE's effect on R#32-R#46** — only DPPAGE 0, 1, 3 in SCREEN 5 ran, and
   the probe records R#0-R#27 only, so "ACPAGE writes no VDP register" is unpinned for R#36-R#45. Pin with SP-5 /
   SP-7 / SP-AC plus a read of R#32-R#46.
8. **CHGMDP: only A = 5 ran.** Every other A, and the palette values, are unpinned (CP-EQ / CP-PAL).

## 2. Rules the measured cases could also explain with a different rule

1. **CHGMOD table, R#0 and R#1 contain the probe's $A5 garbage.** R#0 bit 5 ($20 in every row) and R#1 bits 0 and 2
   ($65 / $75: MAG set) match RG0SAV / RG1SAV = $A5; RG0SAV after A 0 is $A1 (= $A5 with the mode bits cleared). Rule
   A "R#0 := RG0SAV & ~mode | mode bits" and rule B "R#0 := $20 | mode bits" both fit; a clean copy (RG0SAV / RG1SAV
   = $00, and walking bits) separates them. The table presents garbage-derived values as the call's.
2. **CHGMOD R#4 = $25 for A 5-8 is $A5 masked to six bits** (RG4SAV stays $A5): "R#4 rewritten from RG4SAV" vs
   "R#4 := $25". Same for R#3 "(kept)" = $A5. Separated by a second garbage value in RG3SAV / RG4SAV.
3. **"(kept)" conflates two rules**: "the VDP register left as found" vs "rewritten from its copy". The VDP showing
   $A5 (a value the probe wrote only to RAM) indicates rewriting, but the probe does not record the VDP before the
   call, so the case cannot exclude a leftover. Separate with VDP R#3-R#6 ≠ copies, both recorded before and after.
4. **CHGMOD CGPBAS = $0800 for A 5-8** equals SCREEN 0's value that every case started from: "set to $0800" vs
   "kept". Separate by entering from SCREEN 1 (CGPBAS $0000).
5. **CHGMOD LINLEN 37 / 39 for A 2-8** equals SCREEN 0's: "set" vs "kept". Separate by entering A 2 / 5 from SCREEN 1
   (LINLEN 29).
6. **CHGMOD interrupts "as entered (off)"** vs "forced off" — only DI entries. Separated by IE.
7. **CHGMOD R#7 "machine values (JP $07, EU $04)"** vs "from BDRCLR / BAKCLR" (and $F4 in SCREEN 0 from FORCLR /
   BAKCLR). Separate by setting FORCLR / BAKCLR / BDRCLR to non-default values.
8. **SETPAG "Out: A = SCRMOD"** vs "A = 5" (or any value that happens to be 5 in SCREEN 5): only SCREEN 5 ran.
   Separate with SP-7 (SCREEN 7 / 8).
9. **SETPAG R#2 / R#6 / R#11 from DPPAGE alone** vs "DPPAGE masked to 2 bits" vs "written raw": DPPAGE 0, 1, 3 do not
   separate them (SP-OOR does). And R#0's mode bits ($A7 in RG0SAV, $26 in the VDP) fit both "from SCRMOD" and "from
   the VDP's current mode" — separate with SCRMOD ≠ the VDP's mode.
10. **CHGMDP "the palette is written"** vs "R#16 := 0 only": R#16 = $00 after CHGMDP vs $0F after CHGMOD fits both.
    Separate by reading the 16 entries.
11. **"A 9 / $FF / 10-12 change nothing"** vs "change only VRAM / palette" — only registers and work-area cells were
    captured (see 1.1). Also R#9 bit 7 := 1 for A 5-8 fits both "from RG9SAV" and "constant" (RG9SAV not garbaged);
    CM-LN separates.

## 3. Citations that do not match the tables

1. **CHGMOD.md, Measured: "LINLEN 37 / 39 (EU / JP)" for A 0-8 is false for A 1** — record 1 has LINLEN $1D (29) on
   all three machines, and OLDSCR := 1 (unreported).
2. **CHGMDP.md, Differences: "their R#16 ... differ"** — record 22 has R#16 = $00 in both the reference and C-BIOS.
   What differs is R#17 ($2C vs $18) and F ($10 vs $A8); A is $07 in both.
3. **SETPAG.md, Measured, omits R#11 := DPPAGE** ($00 / $01 / $03 in records 20 / 19 / 21) — the sprite attribute
   table's high bits also follow the page. It also omits that the call rewrites R#0 with the mode bits (RG0SAV $A5 →
   $A7, VDP $26), rewrites R#5 / RG5SAV := $EF and R#4 from its copy ($25), and updates RG2SAV / RG6SAV; "rewrites
   R#1, R#3 and R#7 from their copies" is incomplete. Its Differences omit C-BIOS's R#4 ($00 vs $25) and RG6SAV
   (left $A5).
4. **CHGMOD.md, "Machine values, not the call's: R#7 (JP $07, EU $04), R#9 (PAL $02, NTSC $00)"** — R#7 is $F4 after
   A 0 on all three, and R#9 is $82 / $80 after A 5-8, so bit 7 is the call's. The table stops at R#6 though R#9,
   R#11 ($01 for A 7 / 8), R#14 ($01 / $03) and R#17 ($2C) change with A; "the same on all three" does not hold for
   R#17 ($1C on the FS-A1WSX vs $18 for A 0-4).
5. **CHGMOD.md, Differences: "set the same registers and cells"** — the run shows C-BIOS LINLEN 37 where the HB-F900
   and FS-A1WSX have 39 (C043 / C103 / C163 / C1C3), R#14 and R#17 differ for A 5 (C1F5, C1F8), RG3SAV differs for
   A 3 (C146), and $F92A differs (C04D ...).
6. **CHGMOD.md, Interface / Behaviour still say [A]** for "interrupts on return", "A outside 0-8" and "10-12 on an
   MSX2+", contradicting its own Measured paragraph; CHGMDP's "Interrupts on return: [A]" and SETPAG's "RG2SAV
   updated [A]" / R#2 low bits "[A]" likewise (the run shows RG2SAV = $3F, low bits forced to $1F despite RG2SAV $A5).
7. **screen-modes.md says "DRAFT 0, nothing measured yet"** and keeps "$7800 in R#6 is [A]", "SCREEN 4 tables
   constants or GRP\* [A]" and "A = 9 ... [A]"; the xmode run measured R#6 $0F / PATBAS $7800 (SCREEN 5 / 6), $F000
   (7 / 8), $1E00 (SCREEN 4, though GRP\* were not moved, so the GRP\* question stays open) and A 9 as a no-op. The
   concept page cites none of it.
8. **The decoder `scratchpad/xmode_decode.py` is named on all three call pages but not linked**, so a reader cannot
   reach it under the stated rules.

## 4. Gaps in the open lists

1. **CHGMOD's "every output is recorded" names R#0-R#27 only** — R#32-R#46 and S#0-S#9 (the concept page's own
   apparatus) are missing, yet R#17 = $2C shows a VDP command ran; CM-CLR / CM-BUSY and SETPAG's SP-AC need them.
2. **No row records the VDP before the call**, which every "(kept)" claim needs (item 2.3); CM-R01 covers only
   R#0 / R#1 and only A 4-8 — R#0 / R#1 garbage leaks into A 0-3 too, and R#3-R#7 need the same walk.
3. **CHGMOD: no row for** LINLEN / OLDSCR on A 1 (LINL32 vs LINLEN), LINLEN and CGPBAS kept vs set in 2-8, R#7 vs
   FORCLR / BAKCLR / BDRCLR, and R#10 / R#11 / R#14 for A 0-4 after a mode 7 / 8.
4. **SETPAG: no row for** R#11 / R#5 / R#0 (now known to be written), for RG1SAV with bit 6 clear (the reference
   blanks the screen: R#1 = $25 in records 19-21), or for SCRMOD ≠ the VDP's mode.
5. **CHGMDP: CP-EQ should note it is already falsified on one output** — record 22 returns interrupts ON where
   CHGMOD 5 returns them off, and A / F differ; the "= CHGMOD + INIPLT" rule needs to say which.
6. **CM-0..3 is shown as all `?`** although records 11-14 (direct INITXT..INIMLT in the base state) already give the
   comparison in one state (equal except R#11, left at $01 by INITXT); the row should say what remains.
7. **screen-modes.md's R#25-R#27 locating row** ignores that the probe already captures $FFFA-$FFFC (FS-A1WSX 00 00 00,
   HB-F900 FF FF FF, NMS 8250 FF 00 FF, unchanged by CHGMOD 10-12); the row could start there.
