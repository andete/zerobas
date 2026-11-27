- [ ] 🧭 **THE DISK ROM PAIRED WITH A FOREIGN BASIC -- a goal, at LOWER priority (Joost 2026-11-26: "this is a goal,
      but definitely lower priority now") (D-FOREIGNBASIC).**
      🎚️ TIER 6 — every edge, by Joost's ranking: behind the disk ROM's filed fixes for the C-BIOS port.
      🤖 **AUTONOMOUS** — the first steps are measurements and a small guard; the large step needs a ruling.
      WHAT IS KNOWN (2026-11-26): every Disk BASIC handler in the disk ROM (hook_tab: DSKF, MKI$/MKS$/MKD$, CVI/CVS/CVD,
      NAME, KILL, FILES, LSET/RSET, FIELD, DSKO$/DSKI$, COPY, the error messages, CALL FORMAT) speaks zerobas BASIC's
      PRIVATE calling convention -- values crossing in work-area cells (STRSCR+1 ...), and hk_mkfloat / hk_cv CALLing
      six routines of zerobas's main ROM by address (disk/basic-resident-abi.inc). The hooks are the STANDARD cells, and
      install_basic_hooks claims them with no check of which BASIC is there. Microsoft's BASIC calls the same hooks
      with ITS convention, so on a VG-8020 these handlers would misbehave (by reading).
      MEASURED: a VG-8020 with zerobas's disk ROM in slot 1 (composed from openMSX's VG-8020 config + the zerobas-disk
      extension) never reaches a usable prompt -- it sits at "Enter date (M-D-Y):" and answers every line, a valid
      `1-1-84` included, "Invalid date" (by hand, 2026-11-26).
      STEPS: (1) why the date prompt never accepts on that host; (2) a guard -- INIT tells zerobas's BASIC from a
      foreign one and, on a foreign one, installs NO Disk BASIC hooks: MSX-DOS only (small; needs disk-ROM room);
      (3) Disk BASIC on BOTH BASICs -- 🧭 JOOST 2026-11-26: "The disk rom can still assume presence of _a_ basic." So
      not two handler sets: ONE set written against the interface both BASICs present, MICROSOFT'S -- each hook called
      with its convention, the published cells (DAC, VALTYP, FBUFFR ...; zerobas uses these already), and the published
      entry points. zerobas, faithful to MS-BASIC anyway, moves toward that interface where it differs: today it calls
      the hooks with a PRIVATE convention (STRSCR+1 ...) and does NOT serve the published Math-Pack entries at their
      standard addresses (checked 2026-11-26) -- which is why hk_mkfloat / hk_cv call zerobas-private routines.
      STEPS: (a) MEASURE each Disk BASIC hook's entry convention on the VG-8020 (registers / RAM at the hook, black box);
      (b) zerobas BASIC calls the hooks that way; (c) the few routines the handlers need (float conversion ...):
      served by zerobas at the published addresses (main-ROM room, also tight) or done inside the disk ROM. Size only
      after (a); plausibly hundreds of bytes over both ROMs, not kilobytes.
      🎯 THE GOAL (Joost 2026-11-26): "Given that a real disk rom manages to work this way, ideally we should be able to as
      well." -- zerobas's disk ROM should depend on exactly what a REAL disk ROM depends on: MS-BASIC's published
      interface PLUS the fixed internal addresses a real disk ROM relies on (MSX1 MS-BASIC is identical across machines;
      one met already: the routine at $7D2F the disk ROM calls from H.RUNC, docs/concepts/disk-rom-host.md item 4, which
      zerobas serves). The same interface makes the reverse work -- zerobas BASIC hosting a STOCK disk ROM (MSX-DOS
      sessions already do). ⚠️ CLEAN ROOM: those addresses are learned only at the boundary (registers, RAM, slot / port
      traffic, which hook fires in what state), never by tracing a reference ROM's code or recording its PC -- the way
      the host contract (D-DISKROMHOST) mapped $7D2F.
      🧭 JOOST 2026-11-27: "we'll only do disk basic with zerobas for now, which is fine. The more broad compatibility
      can be a later step." Disk BASIC = a zerobas BASIC host only, for now. The same day C-BIOS integration step 1
      added zerobas BASIC's host marker (ZB_HOST, $FD09 -- slot 0's own SLTWRK entry -- "ZB", written before the scan;
      Joost chose the marker cell): H_FORM's handler refuses without it (D-BIOSFORMAT). A first step here, when this
      item comes up: skip installing the Disk BASIC hooks when the marker is absent, so a foreign BASIC host gets
      plain MSX-DOS instead of the VG-8020's date-prompt hang.
