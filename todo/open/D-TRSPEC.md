- [ ] **D-TRSPEC — ELEPHANT / GOLDFISH SPEC PAGES FOR THE MSX TURBO R BIOS CALLS**
      🎚️ TIER 1 — Joost 2026-11-23: "if we're finished with the msx2 and msx2+ specs we could also spec the turbor
      bios calls" -- AFTER D-MSX2SPEC / D-MSX1ON2, before D-KWSPEC unless Joost reorders.
      🤖 **AUTONOMOUS** — turbo R additions (CHGCPU / GETCPU, PCM PCMPLY / PCMREC, the R800 and its own slot / timing
      behaviour), plus the MSX1 / MSX2 / MSX2+ calls re-measured on it (D-MSX1ON2's rule). Reference machine: openMSX's
      generic `turbor` links to the Panasonic FS-A1GT (checked 2026-11-23; Joost installed its ROMs the same day; it BOOTS
      -- HIMEM $E7B5, EXBRSA $87, read from RAM only) -- the same rule Joost set for MSX2.
      C-BIOS has no turbo R build: the subject is TBD (pages first, as the MSX2 ones were).
      2026-11-23 (isolated agent tr1): biosl_run `--row turbor` = FS-A1GT vs FS-A1ST (a DIFF is the two references
      disagreeing), `@cpusnap`; docs/turbor/index.md (MAP: no new sub-ROM call; $FFFD the CHGCPU stack cell; $FCB1 found
      by measurement); CHGCPU / GETCPU DRAFT 1 (xchgcpu / xgetcpu / xtrboot.asm): A AND $7F in 0-2 accepted, anything
      else ignored without trace; S1990 R#6 is the truth GETCPU reads, not $FCB1; CHGCPU returns with interrupts ON
      even entered DI; both models agree except boot timing. PCMPLY / PCMREC DRAFT 0. NEXT: PCMPLY / PCMREC (and the
      DRAM-mode memory side), then the MSX1 / MSX2 / MSX2+ calls re-measured on turbo R, then a goldfish pass.
