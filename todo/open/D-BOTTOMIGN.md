- [ ] 🐛 **ZEROBAS BASIC IGNORES BOTTOM: A CARTRIDGE'S CONVENTIONAL WORK AREA SITS INSIDE THE PROGRAM TEXT (D-BOTTOMIGN, found
      2026-11-26 by D-DISKROMHOST (d)'s CF-3300 check).**
      🎚️ TIER 1 — happy path: the PUBLISHED way for a cartridge to get more than 2 bytes of RAM (MSX2 Technical Handbook
      ch.5 §7: store BOTTOM, $FC48, in its SLTWRK entry and raise BOTTOM by what it needs) is lost on zerobas -- the first
      program line typed overwrites that work area.
      MEASURED (scratchpad/claimconv_probe.py, [AE_claimconv.out](../../scratchpad/AE_claimconv.out), the BOTTOM rows): a test cartridge raises BOTTOM by
      64 from $8000. The CF-3300 starts BASIC's text above it -- TXTTAB $8041 for BOTTOM $8040; zerobas leaves TXTTAB at
      $8001 with BOTTOM $8040. (Slot 1 and slot 2 alike; the signature in the area is still intact at the prompt only
      because nothing was typed yet.)
      FIX DIRECTION: the BASIC start-up takes TXTTAB from BOTTOM + 1 (BOTTOM's own published meaning) instead of a fixed
      $8001 -- find where zerobas's boot sets TXTTAB / BOTTOM (basic/interp.asm's boot, near the HIMEM handling D-CARTCLAIM
      names) and check every other writer of TXTTAB (NEW, CLEAR, LOAD) keeps it. Measure the VG-8020 too (expected as the
      CF-3300). A gate row: BOTTOM raised, a program typed, the signature intact and TXTTAB = BOTTOM + 1 on both.
      🤖 **AUTONOMOUS** — but a BASIC item: by Joost's focus it waits behind the disk ROM's readiness for C-BIOS, beside
      [D-CARTCLAIM](D-CARTCLAIM.md).
