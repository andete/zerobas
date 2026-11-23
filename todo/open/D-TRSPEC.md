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
      2026-11-23 (tr2): PCMPLY / PCMREC DRAFT 1 (xpcm*.asm: one OUT $A4 per sample, rates 63.6 / 127.4 / 191.1 / 254.8
      us; an undocumented `$00 n` run code; VRAM source E:HL, length D:BC; from the Z80 it switches to R800 ROM and
      back; PCMREC's successive approximation, rate 0 refused outside DRAM mode; compression / threshold without a key
      never return); R800 DRAM mode: the top 64 KB of the mapper refuse writes ONLY in DRAM mode (A1GT 512 KB, A1ST
      256 KB). A clean-room INCIDENT (page-1 source) was self-caught and contained: docs/clean-room-audit.md.
      Open: PCMREC with a real input needs a harness directive to feed openMSX's wavinput a file.
      2026-11-23 (tr3): EVERY existing BIOS probe (206) re-run on both turbo Rs (scratchpad/trall_run.py / trall_cmp.py,
      AE_trall/, docs/turbor/remeasured.md): 53 SAME, 74 as the FS-A1WSX, 18 NEW on the turbo R -- RDRES / WRRES the
      other way round from the A1WSX, CHKSLZ never returns on the A1GT, NEWPAD / GTPAD 0-11 and GTPDL do nothing, the
      cassette calls are stubs (carry set), DSKRST after SELDSK 1 returns DI on the A1GT only, INIT32 width 255 / 0.
      Not run: xtap1 / xtap5 / b7tape (`@tape` kills the run on a machine with no cassette port -- biosl_run needs to
      skip it). NEXT: carry each NEW finding onto its page (docs/turbor/remeasured.md lists them), the @tape skip, a
      goldfish pass over docs/turbor/.
      DONE the same evening: `@tape` records "no cassette port" (tr4); the tape probes ran (every cassette call returns
      carry set, nothing read / written); all 21 NEW findings re-checked and carried onto their MSX1 / BDOS / MSX2 pages
      as "On the turbo R" bullets; goldfish pass 1 over docs/turbor/ (32 findings) acted on (fxtr: CHGCPU's accept rule
      pinned against rivals, $FFFD = SP - $18 at three SPs, I carried across CPUs, PCMPLY's $00 code in every mode,
      STOP from every mode).
      Late 11-23 (tr5, tr6): a turbo R line on 171 more call pages (every remeasured verdict is now on its page);
      biosl_run `@iffsnap` / `@dumpstate` / `@wavin`; port $F4 bit 7 decides whether JP $0000 comes back (1: re-boots
      into the cartridge, VRAM kept; 0: never returns within 60 s); PCMREC with a known WAV input: offset binary
      (128 + input / 256, $00 stored as $01), threshold = wait for |sample - $80| >= 8t, compression `$00 n` for runs of
      exactly $80; the A1GT-only DSKRST DI is a timing coincidence of xbsys2's run (2400-step phase sweep: 0 DI),
      cause not found (candidate: disk rotation phase).
      OPEN (all small): the DSKRST cause; PCMREC's comparator bits / the unstored conversion / rounding / VRAM
      compression; a second goldfish pass over docs/turbor/ when the pages next change.
