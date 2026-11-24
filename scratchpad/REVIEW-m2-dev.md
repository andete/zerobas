# Goldfish review (test-writer role), 2026-11-23: BEEP.md, NEWPAD.md, KNJPRT.md

Fresh reviewer; read only the pages and their cited evidence. Decoded the NMS 8250 records for BEEP / NEWPAD (all four
runs) and the NMS 8250 + HB-F900 records for KNJPRT; NOT the HB-F900 / FS-A1WSX records for BEEP / NEWPAD.

## 1. Rules not pinned by any measured case
1. BEEP — final R7 := $B8 may be a restore, not a constant: the probe's preset R7 (psgset) is $B8. Pin: preset R7 to
   e.g. $BF or $78 and check the final write; R7 bits 7-6 (port directions) never varied.
2. KNJPRT — placement rests on one position (GRPACX = GRPACY = 16): (GRPACX, GRPACY) vs snapped to an 8/16 grid. Pin:
   unaligned 13 / 21.
3. KNJPRT — the advance rests on one start value: 16 -> 32 fits +16, x2, := 32. Pin: the same unaligned start.
4. KNJPRT — "GXPOS / GYPOS not used" half measured: they are 40/40 but the window ends at 35. Pin: capture (40,40) or
   set GXPOS inside the window.
5. BEEP — "PPI port C left as found [M XB 0-17]" has no before-value (read after only, $5A, same as C-BIOS). Pin:
   record port C before and preset bit 7 (BP-6).
6. KNJPRT — whether the call waits for the VDP command engine: the probe waits after the call. Pin: S#2 bit 0 right
   after the return.
7. NEWPAD — out-of-range classes pinned only by flags: PADX runs before any fetch, so every read returns 0; "3, 7, 31,
   $FF -> 0" vs "0, 1, 4, 5, 24, $80 -> X" rest on F alone. Pin: repeat PADX after a fetch of an empty port ($01).

## 2. Rules the cases could also explain with a different rule
1. NEWPAD — X/Y read split: A) 00/01 -> X, 10 -> Y; B) same cell, only F differs. Every fetch gave X = Y. Separating
   case: a fetch with X != Y; NP-3 does not name this split.
2. BEEP — FS-A1WSX interrupts: A) as on entry; B) off unless MODE / TE changed. Case 17 changes EI entry, MODE $07 and
   V = 6 at once. Separating case: EI entry with MODE left at $0B.
3. BEEP — what paces the sound: CPU loop vs VDP frame flag. Separating case: FS-A1WSX in turbo mode.
4. KNJPRT — mode 3 / 4: A) bit 1 -> odd rows; B) mode AND 2 -> mode 2; C) any mode >= 2 -> mode 2. A = 4 separates C;
   KJ-9b lists it but not the rules.
5. KNJPRT — refused codes: BC $0000 fits B = 0, C = 0, BC = 0, code < $2121. Separating: $0021, $2100 (KJ-7b lacks
   them).

## 3. Citations that do not match
1. NEWPAD "[M PADB 11-12, 16]" for "9/10 return the last mouse/track-ball fetch's X/Y": PADB 11-12 follow call 8, a
   fetch of the EMPTY port 1 ($01); only PADB 16 follows a mouse fetch. Rule holds; wording and citation do not.
2. NEWPAD "[M PAD 5-6, 16-17]" for "a read repeats without fetching": PAD call 8 (function 16) is a fetch between them.
   The no-fetch pair is PAD 9-10 vs 18-19.
3. NEWPAD "0" class "separated by value [M PAD 7, 11, 15]" holds for 15/19/23 only, not 3, 7, 31, $FF (see 1.7).
4. BEEP sound-00 durations: summary "36-733 ms" vs body "~44 ms"; NMS 8250 case 0 gives 46.1 ms entry -> final R7
   (R8 held 43.2 ms). 36 ms matches nothing.
5. BEEP "PPI port C left as found [M XB 0-17]": no before-value (1.5).

## 4. Gaps in the open lists
1. BEEP: no open row for an R7 preset other than $B8 / the direction bits.
2. KNJPRT: no row for unaligned GRPACX/Y, GXPOS/GYPOS outside the window, the command engine on return.
3. NEWPAD NP-1b: inputs 32-127, 129-254 leave out 25-30; "12 of 233" is wrong (240 out-of-range numbers, 228
   unmeasured).
4. NEWPAD: no rows for out-of-range reads after a fetch; GTPAD with A = 20-23 or out of range; a fetch (12/16) with a
   plain joystick plugged.
5. BEEP: no row for EI entry with MODE unchanged; timing at another CPU speed.
6. KNJPRT: KJ-7b lacks $0021 / $2100.
7. KNJPRT: no row for other BAKCLR / $F3F2 colour values (upper-bit masking in SCREEN 5).

## Checked and consistent
NMS 8250 BEEP register values, the four sequences, write order, ~365 ms decay (same at levels 4 and 15); NEWPAD's NMS
8250 registers, flags, fetch values, port sharing; GTPAD 9 after GTPAD 8 returns $01 [PAD 27] (pinned, uncited: 8 does
not clear the stored values); KNJPRT HB-F900 mode 1/2 rows, XOR colours 6/7, 82 dots for $3021, GRPACX values.
