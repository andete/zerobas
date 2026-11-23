- [ ] **D-VCBLAYOUT — PLAY'S VOICE-BLOCK BYTES: ZEROBAS'S OWN LAYOUT, NOT THE REFERENCE'S**
      🎚️ TIER 6 — every edge (filed 2026-11-22).
      🤖 **AUTONOMOUS** — Measured on the VG-8020 (scratchpad/AE_d23_vcbcmd.out): offset 18 of a voice block holds the
      packet's vol byte ($80 | V, $90 | S, + $40 while an M is pending), offsets 19-20 the M period; zerobas's
      parser keeps volume 0..15 at 18, $80 | shape at 19 and M at 13 (sub/playparse.asm VCX_*). Only PEEK sees it;
      since the rebase C-BIOS's GICINI writes the reference's defaults, which the parser detects ($FF at 19) and
      re-seeds. Move the parser to the reference layout when sub page 1 has the room.
