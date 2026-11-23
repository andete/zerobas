- [ ] **D-GRPPRTSETC — GRPPRT DRAWS EACH SET GLYPH BIT AS ONE SETC; docs/bios/GRPPRT.md R-GP-VRAM SAYS OTHERWISE**
      🎚️ TIER 6 — every edge (filed 2026-11-21).
      🤖 **AUTONOMOUS** — From the C-BIOS 0.32 port's measurements (Joost, 2026-11-21; headless openMSX, BIOS calls made directly, VG-8020 = NMS 8250 unless noted). Check zerobas against them first.
      With a RAM font (CGPNT -> RAM, glyph $41 = FF 81 00 C3 3C 00 01 80): each set bit is one SETC, left to right, RIGHTC
      between, TDOWNC after each line -- so SETC's 'all 8 bits set' step DOES happen: pixel $20 over $FF / $14, FORCLR $0A
      -> $DF / $1A; glyph line $81 over $FF / $1A with FORCLR $1A -> $7F / $AA. R-GP-VRAM ('no whole-byte or last-clear-bit
      step') holds only for a full glyph line over an empty byte. Also: CR in SCREEN 0, 1 and 3 steps 32, not 8; GRPACY's
      low byte wraps to 0 past 191 with the high byte kept ($01BA -> $0100; $00FA -> $0002). Re-measure, then fix the page.
