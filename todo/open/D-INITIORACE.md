- [ ] **D-INITIORACE — A FRAME INTERRUPT PENDING AT INITIO'S ENTRY PLAYS A STALE QUEUED NOTE ON THE REFERENCES; ZEROBAS'S GICINI-FIRST DOES NOT**
      🎚️ TIER 6 — every edge (filed 2026-11-22, from a C-BIOS 0.32 port measurement).
      🤖 **AUTONOMOUS** — reported, not yet measured here: with interrupts off, a frame interrupt pending (a ~30 ms DI
      loop before JP $003B), MUSICF $01, voice A's word 1 and a note packet (vol $8F, tone $0123) in queue A, the
      VG-8020 and the NMS 8250 end INITIO with PSG R0 / R1 = $23 / $01 -- the frame lands inside INITIO (WRTPSG enables
      interrupts) and the player sounds the stale note before GICINI clears MUSICF; GICINI resets volumes, MUSICF,
      words and queues but not the tone registers, which is where it shows. With no interrupt pending they leave R0 /
      R1 0. zerobas's INITIO calls GICINI FIRST (cbios-repack/initio-gicini.patch, for R-IO-PLAY), so it never plays it.
      FIRST: a row on docs/bios/INITIO.md measuring exactly this (a pending IRQ at entry + a stale packet), then
      decide: undo GICINI-first (R-IO-PLAY's case must then still hold) or keep it as a listed difference.
