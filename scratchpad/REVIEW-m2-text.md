# Goldfish review (test-writer role), 2026-11-23: SDFSCR / SETSCR / PROMPT / CLRTXT

Fresh reviewer; read the pages, the probe sources, and the raw `CAP ref` dumps of the four scratchpad/AE_xsub*_msx2.out
files, sliced by the probes' record layouts (not the decoders).

## 1. Rules not pinned
1. SDFSCR printer / cassette bits: only 0 -> 1 measured (case 13 NTMSXP $00 -> $FF; case 14 $F406-$F40A). Whether a 0
   bit restores NTMSXP $00 and the 53 5C 26 2D 0F timings or leaves them: not measured (case 18 is a snapshot, never
   diffed). Pin: a diffed case clearing bits 2 / 3 after set 6.
2. SDFSCR "the VDP reprogrammed": never says which registers. RG5SAV / RG6SAV keep the previous mode's $EF / $0F after
   SCREEN 0 results (cases 1, 5-9) but $36 / $07 after SCREEN 1 results (2, 10, 18) -- state and test the split.
3. PROMPT "the clock chip is left as it was" covers block 3 regs 0-12 only; MODE (reg 13) not recorded -- record it as
   xsubscr does at +69.
4. CLRTXT "the same before and after": RG0SAV-RG7SAV recorded only after; the RG7SAV / copies claim rests on expected
   CHGMOD values, not a before/after pair.

## 2. Rival rules
1. SDFSCR / SETSCR "the screen cleared": neither probe fills VRAM before the call; the probe's CHGMOD already blanked
   it. Blank rows 0 / 23 also fit "no clear"; only the cases entered from SCREEN 5 separate (SDFSCR 1, 5; SETSCR 2,
   half). Pin: fill the name table with non-spaces in the same mode before the call.
2. SETSCR order of banner and key line: the page says banner then key line; the port-$98 log of case 0 shows key-label
   bytes just BEFORE "MSX BASIC" on all three (NMS 8250 `45 45 45 45 45 20 20 20` then "MSX"; HB-F900 / FS-A1WSX
   `44 44 20 45 45 45 45 45` then "MSX") -- key line first, or drawn twice; the full port log's label positions decide.
   SDFSCR "no key line is drawn" is final-state only (no xsubscr case sets the log flag b4).
3. SDFSCR work-area claims ("nothing else changes", cases 12-17; the SETSCR vs SDFSCR diff, 6/7) compare two runs: a
   cell written to the same value each time is invisible. Pin: before-vs-after of one call over a junk-filled area.
4. SDFSCR interrupts on in TEXT 2: every TEXT 2 case (6-10) enters from TEXT 1 / SCREEN 1 / 5 -- "result is TEXT 2" vs
   "VDP was switched into TEXT 2". Separate: enter already in 80-column TEXT 2 with DI.
5. CLRTXT row length 32 in graphic modes: cases 10, 11 have LINL32 = 32 -- "always 32" vs "LINL32"; only SCREEN 1
   (case 8, LINL32 29) separates. Pin: SCREEN 2 or 5 with LINL32 != 32.
6. PROMPT which IDs give the stored prompt: only 0-3 measured -- "ID = 2" vs "(ID AND 3) = 2"; ID 6, $A, $F separate ($F
   is also C-BIOS's fresh value).
7. SDFSCR A / flags not inputs: A $FF only with EI (case 9), A / carry / Z only on the width-80 path; the SCREEN 1 /
   40-column path (interrupts kept) not tested.

## 3. Citations that do not match
1. CLRTXT interrupts with the key line on (MOST IMPORTANT): the records show IFF 01 on both reads on the HB-F900 in
   cases 4, 7, 9, like the NMS 8250; only the FS-A1WSX gives 00. The interface bullet ("off on the HB-F900 and
   FS-A1WSX") and the Open table's IE row are wrong for the HB-F900.
2. CLRTXT row numbering: rows 24-26 "still hold the probe's garbage" (from 0) and the key line on / blank on "row 24"
   (from 1) -- read literally row 24 is both.
3. SETSCR cursor "CSRY = 2, CSRX = 1" cites cases 0-4 and 7-13; case 5 (width 100) also records it.
4. CLRTXT interrupts with the key line off: the citation omits case 3.
5. PROMPT key-line scroll "rows 1-23 up one" rests on 4 rows of an all-'#' table; the supporting port-$98 count (926 /
   922 bytes in cases 14 / 15 = 23 x 40 + the prompt) is not cited.

## 4. Gaps in the open lists
1. SDFSCR: SCREEN 1 with width 33-40 and > 40 (TEXT 2?), width 0; clearing printer / cassette bits (1.1); entering in
   TEXT 2 (2.4).
2. PROMPT: IDs 4-15 incl. $F; a prompt wrapping at the right edge; MODE after the call.
3. CLRTXT: key line on in SCREEN 2 / 5; CNSDFG other than $00 / $FF; key line on entered with EI.
4. SETSCR: a banner longer than the window (SCREEN 1 width < 21, e.g. 18); the full port-log order (2.2).
