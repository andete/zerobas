- [ ] 🔁 **D-BASICPUB — THE PUBLISHED BASIC-ROM ENTRY POINTS (MATH-PACK + INTERPRETER
      INTERNALS) ARE NOT AT THEIR ADDRESSES (found 2026-10-15 by D-BASICINT)**
      🎚️ TIER 1 — happy path: machine code that calls the published BASIC ROM
      (PROPOSED -- the same class Joost ruled in for the undocumented three;
      he confirms or re-tiers it in the question below).
      🔁 **STANDING** — Joost 2026-10-16, *"maybe later, as needed for now"*: no bulk
      layout project; an entry is built (D-BASICINT's method) when a measured
      title calls it. ~~🙋 NEEDS-JOOST~~.
      📏 2026-11-01: the titles that call these internals run on two other European MSX1s
      and reset on an MSX2 -- see D-TAPELOAD's (A1) block for the runs; Joost asked for that
      measurement before deciding (A1) and this item's scope.
      📚 MSX2 Technical Handbook (allowed source B): App. 2 publishes ~70
      math-pack entries with their contracts ($268C DECSUB ... $383F INTEXP; DAC
      $F7F6, ARG $F847), ch. 2 eight interpreter internals for CALL-statement
      extensions (CHRGTR $4666, FRMEVL $4C64, FRMQNT $542F, GETBYT $521C, FRESTR
      $67D0, PTRGET $5EA4, NEWSTT $4601, READYR $409B). zerobas implements the
      RST-vector contracts but none of these addresses. The cost is a LAYOUT
      project: ~80 pinned entries across $268C-$67D0, part inside the repacked
      C-BIOS region, some 1 B apart (FOUT $3425 / PUFOUT $3426), and the float
      core's format differs from DAC's BCD (D-ROMSIZE step 4 meets it).
      ✅ **RULED (Joost, 2026-10-16): "maybe later, as needed for now"** -- see the
      STANDING line at the top. ~~🙋 Joost: in scope, and at which tier?~~
      ~~📏 A concrete case, 2026-10-16: Loopy Laundry calls ~25 BASIC-ROM
      internals~~ -- WITHDRAWN the same day: those were the reference's own hook
      returns, not game calls (D-TAPELOAD's correction note). Demonia's $72E9 /
      $72D4 are real calls, but undocumented: D-BASICINT's class, not this item's.
