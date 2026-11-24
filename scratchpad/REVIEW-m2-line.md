# Goldfish review (test-writer role), 2026-11-23: DELLNO / INSLNO / PUTCHR / PUTVRM / KYKLOK

Fresh reviewer; read the pages and the probes / decoders / run files they cite (one grep of xsubpvr.asm). Spot-checked
NMS 8250 and HB-F900 rows; did NOT decode the FS-A1WSX rows ("interrupts OFF on the FS-A1WSX" unchecked).

## 1. Rules not pinned
1. DELLNO / INSLNO: LINLEN vs LINL40 / LINL32, NAMBAS vs TXTNAM / T32NAM, and how W is chosen are never separated
   (xsubdln2: LINL40 = LINL32 = LINLEN; CHGMOD sets the base). Fix: PUTVRM's PV2 method -- after CHGMOD set LINLEN,
   LINL40, LINL32, NAMBAS, TXTNAM to five different values; add SCREEN 0 width 40 with LINLEN > 40 for W.
2. KYKLOK: BC / DE / HL the same in every case ($B1C1 / $D1E1 / $4171); "In: none" and "C, DE kept" rest on one value.
   Repeat one toggle case with different BC, DE, HL.
3. PUTCHR: F has no rule beyond Z; the values fit exactly the flags of `CP` with A = low(GETPNT), operand =
   low(new PUTPNT) ($B3, $92, $23, $62, $9A, $93 all check) -- state it. BC / DE ($B1C2 / $4E5F) never varied.
4. DELLNO / INSLNO: BC / DE never varied ($B1C1 / $D1E1); early-return "BC, DE kept" rests on one value.
5. PUTVRM: F has no rule ($00/$04/$08/$0C/$2C) -- say whether the test leaves F out.
6. PUTVRM PV2 4-7: the base not measured -- "landed at $0800 + offset" is TXTNAM $0800 left from case 3, copied into
   NAMBAS by CHGMOD; NAMBAS not recorded. Record NAMBAS there, or reset TXTNAM first.
7. DELLNO / INSLNO: no L above 26 measured; L 0 is NOT early, so the test is not a plain unsigned L - 1 > last.
   Measure L 128, L 255.

## 2. Rival rules
1. PUTCHR "full = new PUTPNT equals GETPNT" 16-bit vs low byte only: case 9's F $9A = flags of an 8-bit `cp $19` with
   A $F0. Separate: PUTPNT $FC18 with GETPNT $FB19. Same for the wrap test "= $FC18" vs "low byte = $18": PUTPNT $FB17.
2. DELLNO / INSLNO "last = CRTCNT - 2 when CNSDFG != 0" vs "last = CRTCNT - 1 + CNSDFG (8-bit)": agree on $00 / $FF
   only. CNSDFG $01 separates.
3. INSLNO "LINTTB[last] := $FB constant" vs depends on old LINTTB[last - 1] (every old value was >= $C0). Separate:
   LINTTB[last - 1] = 0.
4. DELLNO, same for "LINTTB[last] := $AF": separate with LINTTB[last] = 0; DELLNO's open list lacks the item.
5. KYKLOK toggle "KANAST = $FF" vs "(KANAST AND m) = m" for masks with bit 0 plus another bit (e.g. $81): measured $01,
   $40, $80, $FE, 0, $FF exclude only masks without bit 0 or bit 0 alone. Pin with $7F, $BF, $DF, $EF, $F7, $FB, $FD.
6. PUTVRM how W is chosen (SCRMOD / VDP mode vs LINLEN > 40) -- already named on the page.

## 3. Citations that do not match
1. KYKLOK open list counts "$5A" as a measured toggle input; it occurs only in KY3 1 (MODE bit 0 set, KANAST not
   tested).
2. DELLNO "entries after last are kept [M xsubdln 0, 5, 6, 8, 15]": in 0, 5, 6 last = 23 (no entries after last); only
   8 and 15 show it.
3. PUTVRM "M = 0 with LINLEN = W [M PV1 0-11]": LINLEN not recorded; in the SCREEN 5 cases it is inferred, carried
   over.
Everything else checked matches (registers, DE offsets, early-return A / H, LINTTB moves, INSLNO L 0 $27D8, $FBCA 30 in
xsubdln2 7-9, PUTCHR pointers / A / CHGET, KYKLOK F-from-OR).

## 4. Gaps in the open lists
1. DELLNO / INSLNO: 1.1; BC / DE as inputs; L 27-255; LINTTB[last - 1] / LINTTB[last] = 0; DELLNO "is $AF constant".
2. PUTCHR: 2.1; the F rule; BC / DE as inputs.
3. PUTVRM: the edge-case margin ([A] in the body, not in the open list); LINLEN > W (negative margin); NAMBAS not
   recorded in PV2 4-7.
4. KYKLOK: BC / DE / HL as inputs; the KANAST masks (2.5), $5A removed from "tried".
