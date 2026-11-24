# Goldfish review (test-writer role), 2026-11-23: docs/msx2/concepts/clock-and-misc.md docs/msx2/sub/REDCLK.md docs/msx2/sub/WRTCLK.md docs/msx2/sub/DSPFNK.md docs/msx2/sub/BLTVV.md docs/msx2/sub/BLTVM.md docs/msx2/sub/BLTMV.md docs/msx2/sub/NRDVRM.md docs/msx2/sub/NWRVRM.md

**Decoded by hand:**
- `scratchpad/AE_xclk_msx2.out`: all 64 REDCLK records and 4 WRTCLK records, on all three references and the subject.
- `scratchpad/AE_xsubfnk_msx2.out`: all 4 cases, references and subject.
- `scratchpad/AE_xsubblt_msx2.out`: all 6 cases, references and subject.
- `scratchpad/AE_xva2_msx2.out`: cases 0, 2–8, 15–24 × calls 0–3. Cases 9–14 were only skimmed (they look the same as case 8).

**Not read:**
- The decoders (`xclk_decode.py`, `xsubblt_decode.py`, `xva_decode.py`): the pages name them, but they are not links.
- The main-ROM VRAM address matrix ([main/README.md](../docs/msx2/main/README.md)): it is not an evidence file, so I could not check the "17-bit rule" claims against it.

## 1. Rules not pinned by any measured case

1. **WRTCLK — "the call selects the block itself" and "MODE left at the block written" are unmeasured.**
   - Before each WRTCLK call, `xclk.asm`'s `port_rd` (used to read the "before" value) sets MODE's bank to the case's own block. So every write ran with MODE already on the right block.
   - To pin it: preset MODE to another block, call WRTCLK, then read the target register and the same address in the preselected block through the ports.
2. **REDCLK / WRTCLK — "MODE's bits 3–2 kept" was tested with one TE/AE pair only.**
   - MODE entered every case as TE = 1, AE = 0 (before-values $08–$0B).
   - So "bits 3–2 kept" and "MODE := $08 OR MM" give the same results.
   - To pin it: RC-6 / WC-6 with AE = 1 and with TE = 0.
3. **REDCLK — "for every block 0–3 and register 0–15 the call selects the block" holds only where the two blocks differ.**
   - A read only separates the named block from the preselected one when their registers hold different values. Several do not:
     - block 3 is all 0 on all three references;
     - block 2 registers 1, 2, 3, 11 (and 10, 12 on the HB-F900 / FS-A1WSX) are 0, the same as preselected block 3;
     - block 1 registers 1, 2, 3 and 10 equal block 2's.
   - So an implementation that returns 0 for block 3 passes.
   - To pin it: preset blocks 2 and 3 to non-zero values that differ by address (the concept page's fixture), then rerun.
4. **WRTCLK — A's bits 7–4 and the F rule are unmeasured.**
   - All four written values (5, $A, 3, 9) are ≤ $0F, so masking and "A kept" versus "A := the masked value" are not tested.
   - All four have even parity, so the P/V bit in F $14 / $1C never varies.
   - To pin it: write A = $F5 and A = $07.
5. **DSPFNK — "nothing is drawn on the bitmap" in SCREEN 5 is only lightly checked.**
   - The probe read only the first 96 bytes (192 dots) of line 204.
   - Lines 205–211, dots 192–255, and the other pages were never read, and nothing was recorded before the call.
   - SCREEN 2–4 and 6–8 are unmeasured.
   - To pin it: diff the whole of lines 196–211 on every page before and after the call.
6. **BLTVV / BLTVM / BLTMV — the measured dots do not show whether the call waits for the VDP command.**
   - `xsubblt.asm` runs its own `cewait` after the call returns, so the dots were read only after the probe's wait. A call that returns while the command is still running would pass.
   - Likewise, "interrupts ON" was seen only on entry with DI, through EXTROM. That does not separate the call enabling them from the path enabling them.
   - To pin it: read S#2 CE immediately on return, and run the same case through SUBROM.
7. **BLTVV — two partial claims.**
   - "LOGOP is applied" was measured only in SCREEN 8: one op (3) over one preset ($FF).
   - The SCREEN 5 case used an odd SX only, with even DX and even NX ((9, 8) → (40, 8), NX 4). Dot-exact placement at an odd DX or with an odd NX is unpinned.
   - To pin it: BV-02a with DX 41, NX 5, and a destination preset that is not 0.
8. **BLTMV — "nothing written past it" and an untouched VRAM.**
   - Only 8 bytes past the array ($D224–$D22B) were checked; the open list asks for 32.
   - VRAM is not read when the destination is RAM.
   - To pin it: preset $EE over 32 bytes and diff the source window.
9. **NRDVRM / NWRVRM — the data path is unmeasured.**
   - The probe reads the VDP pointer, never the data: VRAM was not marked.
   - Neither "A = the byte at the address" (A varies across machines: $00 / $44 / $55) nor "the byte A lands at the address" is checked.
   - BC = $5AA5 and DE = $A55A were preset but never read back, so "only AF changes" is also unmeasured.
   - To pin it: mark VRAM by address, and record BC, DE, HL and the alternate set.
10. **NRDVRM / NWRVRM — the measured page rule leaves several cases out.**
    - Not measured:
      - SCREEN 3 with ACPAGE ≠ 0, even though the page's "SCREEN 0–4" covers it;
      - SCREEN 0 at width 80 with ACPAGE ≠ 0;
      - SCREEN 0 with ACPAGE 2 or 3;
      - SCREEN 6;
      - SCREEN 7 / 8 with ACPAGE ≥ 2;
      - SCREEN 5 with ACPAGE 1, which is NR-03 / NW-03 itself.
    - To pin it: add each of these to the xva2 case table.
11. **DSPFNK — the row and the CNSDFG rule.**
    - "Row 23" was measured only with CRTCNT 24.
    - Only row 23 was read: no other row and no sum, so "drawn only there" is unpinned.
    - CNSDFG was preset to 0 only.
    - To pin it: DF-ROW, plus a whole-name-table sum.

## 2. Measured cases that another rule could also explain

1. **NRDVRM / NWRVRM, SCREEN 0 page — "HL + ACPAGE × $1000" versus "HL OR $1000".**
   - The only measured case is $C123 → $0D123, and bit 12 of $C123 is 0, so the two rules agree.
   - Wrapping AND $FFFF in SCREEN 0 is also untested.
   - Separating case: HL $D123 and HL $F123 with ACPAGE 1 in SCREEN 0 at width 40.
2. **DSPFNK, width 80 — "slot = width / 5 − 1" versus "the whole FNKSTR string (≤ 15 characters)".**
   - The 15-character slot equals the 15-character test strings, so both rules give the same row.
   - At every measured width, LINL40 = LINL32 = the width, so a rule keyed on LINLEN cannot be told from one keyed on LINL40 / LINL32.
   - Separating cases: 3-character strings at widths 40 and 80; LINL32 = 29 in SCREEN 1; width 37.
3. **WRTCLK — "MODE left at the block written" versus "MODE not touched".**
   - MODE already held that block on entry (see 1.1).
   - Separating case: MODE preset to another block.
4. **REDCLK / WRTCLK — "TE/AE kept" versus "MODE forced to $08 | MM".**
   - Separating case: entry with MODE = $04 | another bank.
5. **WRTCLK F — "flags of the value (bit 3 → $08, P from parity)" versus "P/V always set".**
   - $14 for 5 and 3, $1C for $A and 9: every value has even parity.
   - Separating case: write 1 or 7 (odd parity).
6. **BLTVV DIX — "both source and destination run leftwards" versus "[SX−NX+1..SX] copied to [DX−NX+1..DX] in normal order".**
   - Both give the same final VRAM when the rectangles do not overlap, and the measured case does not overlap.
   - Separating case: overlapping rectangles (BV-05).
7. **BLTVV — "LMMM always" versus "HMMM when aligned with LOGOP 0, LMMM otherwise".**
   - Both fit every measured dot.
   - Separating case: only the time on an aligned SCREEN 5 copy (BV-02b).
8. **BLTVM — "NX / NY from the header, written to the block" versus "the header used only because the block's NX / NY were 0".**
   - The block entered with NX = NY = 0.
   - Separating case: BM-01 with a garbage NX / NY in the block.

## 3. Citations that do not match the tables

1. **NRDVRM / NWRVRM compare against a different main-ROM call than they name.**
   - The pages say the address is "the main ROM's", and their preambles say every case runs through the main ROM's NRDVRM $0174 / NWRVRM $0177.
   - `xva2.asm`'s in-run baseline was NSETRD $016E / NSETWR $0171 (calls 0 and 1). $0174 and $0177 were never run.
   - The "ACPAGE × $100 + E" description is NSETRD's ($0015A with E = $5A).
2. **NRDVRM / NWRVRM Differences understate what the subject does.**
   - In cases 15, 23 and 24 (SCREEN 1 / 2 / 4, ACPAGE 1, HL $C123), the subject's NWRVRM address equals the reference's $00123. The agreement comes from the subject's AND $3FFF, not from the right rule.
   - In every SCREEN 0–4, ACPAGE ≠ 0 row, the subject makes **5** port $99 writes, not 4. The sub-ROM NRDVRM's address byte carries $41, the write bit.
   - The Differences section mentions neither.
3. **NRDVRM's pointer after a read is HL + 2, not HL + 1.**
   - NR-06 assumes the counter is left at HL + 1.
   - The measured debugger snapshot after NRDVRM is HL + 2 (e.g. $1234 → $1236; NWRVRM leaves $1235), on all references.
   - The page records neither.
4. **REDCLK Differences — "25 of the 64 reads differ" is right as a count, but some of the 39 matches are coincidences.**
   - On the subject, blocks 2 and 3 both read $F everywhere.
   - The subject's MODE ends at block 3 for block-2 reads (MODE after $0B).
   - So the block-2 rows agree by coincidence. The subject reads the wrong block there too.
5. **The concept page is stale against the xclk dump.**
   - It still says "nothing measured yet" and "$01F5 is taken as the entry [A]; RC-0 settles it". REDCLK's interface also still says "[A] until RC-0".
   - The dump has block 2 register 0 = **$A** and block 3 register 0 = **0** on all three references. That contradicts the ID table (0 / 1 / 2) and "register 0 of block 3 repeats it" [P 5§6.7]; neither page notes this.
6. **REDCLK — the measured rows did not use the concept page's fixtures.**
   - The concept page says block-0 cases run with TE = 0 and a distinct-value register frame.
   - The probe ran with the clock running (TE = 1), with entry A = C, and with registers as found.
7. **DSPFNK — "line 204 unchanged" is inferred, not measured.**
   - The probe recorded the line only after the call.
   - Its value, $44 everywhere, is the cleared background, and the subject (which draws nothing) shows the same.

## 4. Gaps in the open lists

1. **REDCLK — measured facts missing from the page, and stale open rows.**
   - The page does not record F's measured rule: flags of the value AND $0F, giving $10 / $14 / $18 / $1C / $54.
   - It does not record that registers 14 and 15 read $F, or that register 13 reads $08 | MM.
   - RC-0 and the "A bits 7–4 = 0" part of RC-1 are effectively settled but still listed as open.
   - No row presets blocks 2 and 3 to non-zero values, so 1.3's unseparated reads stay open.
2. **NRDVRM / NWRVRM — missing rows.**
   - No rows for the extents of the measured page rule listed in 1.10 and 2.1.
   - No row checks the data byte against marked VRAM.
   - NR-03 / NW-03's expected values ($9234 etc.) should be restated now that the SCREEN 5 rule is measured.
3. **DSPFNK — missing rows.**
   - DF-STR does not ask for strings shorter than the slot.
   - DF-1 does not vary LINL32.
   - No row separates LINLEN from LINL40 / LINL32.
   - DF-BM should require a before/after diff of lines 196–211 on all pages.
4. **BLTVV / BLTMV — rows measured but still listed as open, with no note.**
   - BLTVV: BV-01 (in SCREEN 8) and BV-02a (odd SX only).
   - BLTMV: MV-08 (SCREEN 8).
5. **WRTCLK — no row with A's high nibble set.**
   - No row writes a value with A's high nibble set while also reading A back.
   - WC-1's $F0 / $A5 rows also need A recorded, not only the register.
