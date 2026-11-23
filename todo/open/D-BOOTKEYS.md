- [ ] 🔴 **SHIFT OR CTRL HELD AT BOOT — THE DISK ROM'S OWN BOOT OPTIONS FOR MORE FREE
      RAM (D-BOOTKEYS, raised by Joost 2026-10-09).**
      🎚️ TIER 6 — the `$F347` cell after a SHIFT boot (below); the TIER 4 face (SHIFT, CTRL's drive and RAM halves) shipped 2026-10-10 / 2026-10-27
      🤖 **AUTONOMOUS** — the CF-3300 settles it; measure before building.
      Joost: *"I also remember booting with shift key or ctrl key pressed disabled
      some parts of the disk stuff for more RAM available."* The MSX convention,
      to be CONFIRMED on the CF-3300 rather than taken from memory: SHIFT held
      at power-on skips the disk ROM's initialisation (no Disk BASIC, the disk
      work area not reserved, so `FRE(0)` and HIMEM are those of a diskless
      machine); CTRL held turns off the phantom second drive (drive B: and its
      per-drive work area), which matters once D-DSKIB builds that drive.
      Measure on the CF-3300 and on zerobas DISK: `FRE(0)`, HIMEM (`$FC4A`),
      whether `FILES` / `DSKF(0)` exist, `DSKF(2)`'s answer — for a plain boot,
      SHIFT held, and CTRL held (openMSX can hold a key from power-on). No
      reference ROM byte is read: the keys and the screen / work area only.
      📏 **MEASURED 2026-10-10** ([`bootkeys_probe.py`](scratchpad/bootkeys_probe.py)
      → [`bootkeys_run.out`](scratchpad/bootkeys_run.out); the key held in the Tcl
      prologue from power-on, released at 6 s; DSKF(2) left out — it prompts and
      waits):
      | boot | CF-3300 FRE(0) · HIMEM · drives ($F347) · DSKF(0) | zerobas |
      |---|---|---|
      | plain | 23320 · $DE77 · 2 · 706 | 23244 · $DD12 · 2 · 706 |
      | SHIFT | **28705 · $F380 · 255 (untouched) · ERR 5** | as plain |
      | CTRL | **24878 · $E48D · 1** · 706 | as plain |
      All predicted. SHIFT skips the disk ROM entirely (HIMEM is the diskless
      $F380, +5385 B, DSKF refused with 5); CTRL keeps Disk BASIC with ONE drive
      and +1558 B. zerobas ignores both keys. (Plain: zerobas is 76 B short of the
      CF-3300's FRE(0) — the TIER 4 RAM gap, not this item.)
      ➡️ Next: SHIFT is the bigger, simpler face — the disk ROM's INIT returns
      before reserving anything; check first how main discovers the disk ROM
      (DISKSLOT / the banner call / the hooks), or main still believes in it.
      CTRL depends on D-DSKIB's drive-B model.
      ✅ **SHIFT SHIPPED 2026-10-10.** The disk ROM header's INIT word now points
      at `init_gate` (disk/kernel.asm, the fill above `ds $5FE5`): SNSMAT row 6
      bit 0 held -> install nothing and leave $FF in main's DISKSLOT_OK; main's
      scan (`basic/islands.asm`) now `inc`s that cell instead of storing 1 (−1 B),
      so it wraps to 0 and BASIC is diskless — no `zerobas Disk BASIC` line,
      `DSKF(0)` ERR 5 as on the CF-3300; HIMEM is zerobas's own diskless `$E000`
      (its workspace, the TIER 4 RAM layout — not compared). Gate
      `bootkeys-acceptance` ([`disk_probe_bootkeys.py`](probes/disk/disk_probe_bootkeys.py),
      [`bootkeys_gate.out`](scratchpad/bootkeys_gate.out)): plain / shift / ctrl
      3/3 on the DSKF face; 🔪 [`bootkeys_knives.out`](scratchpad/bootkeys_knives.out):
      K-BK1 (init_gate always inits) -> shift, exactly. **CTRL stays open**: one
      drive and +1558 B on the CF-3300, after D-DSKIB.
      📏 **RE-MEASURED 2026-10-19** ([`bootkeys_1019.out`](scratchpad/bootkeys_1019.out),
      bootkeys_probe.py): **plain** now IDENTICAL (FRE 23320, HIMEM $DE77, 2 drives,
      DSKF 706 -- D-DISKHIMEM); **SHIFT** FRE 28705 and HIMEM $F380 IDENTICAL (since
      D-WSZERO's $F380 ceiling), DSKF ERR 5 on both. 🔮 "plain and SHIFT match, CTRL
      differs": HIT. ➡️ **2026-10-27: D-DSKIB is built**, so CTRL (one drive, B: gone,
      +1558 B) is unblocked. ✅ **CTRL'S DRIVE HALF SHIPPED 2026-10-27**
      ([`bootctrl_probe.py`](scratchpad/bootctrl_probe.py) -> [`bootctrl_run.out`](scratchpad/bootctrl_run.out): on the CF-3300 a CTRL boot answers
      DSKF(2) and FILES"B:" with 62 and $F347 reads 1). INIT reads SNSMAT row 6 bit 1
      into DRVCNT (1 with CTRL held, else 2); drv_select's B: arm calls dsl_bcheck
      (disk/fat.asm, the $46BA fill): DRVCNT below 2 -> 62 through calbak -- one check
      for every path, since every B: access passes drv_select. After: identical
      ([`bootctrl_after.out`](scratchpad/bootctrl_after.out)). Gate: bootkeys-acceptance row `ctrlb` ([`bootctrl_gate.out`](scratchpad/bootctrl_gate.out),
      4/4); 🔪 K-BC1 ([`bootctrl_knife.py`](scratchpad/bootctrl_knife.py)): `ctrlb` alone diverges (the B: prompt
      back), rc=2, all five restored ([`bootctrl_knife.out`](scratchpad/bootctrl_knife.out)). Docs: concepts/disk.md.
      🏗️ **RULED BY JOOST 2026-10-27: *"Ctrl boot should behave same as ref"*** (it was
      🙋, below). **The RAM half needed him (asked 2026-10-27):** the CF-3300 also frees 1558 B
      (HIMEM $DE77 -> $E48D). zerobas's own disk buffers (FAT_DBUF/FSECTOR_BUF $E46A,
      FAT_MBUF $E66A..$E869) sit inside that range, so matching it means moving them --
      a RAM-layout adjustment, which D-TIER5RAM says comes back to him. Residual (priority 3/4, an address): after a SHIFT boot the
      drive-count cell $F347 reads 255 (untouched) on the CF-3300 and 201 ($C9) here
      -- who writes $C9 there is unmeasured. CTRL still open (D-DSKIB).
      📏 **$F347 SETTLED 2026-10-20 -- C-BIOS's own fill, kept; the residual is TIER 6.**
      C-BIOS's `init_ram` fills $F300..$F37F ("Disk work") with $C9 on every boot (its own
      source, `src/main.asm`, the repack's base). The references leave that range alone:
      the VG-8020's reads as the emulator's power-on pattern -- [C9 FF 00 other] =
      [0 60 61 7] against zerobas NODISK's [128 0 0 0]
      ([`diskwork_fill_run.out`](scratchpad/diskwork_fill_run.out),
      [`diskwork_fill_probe.py`](scratchpad/diskwork_fill_probe.py)); the CF-3300's 255 is
      the same untouched RAM. On real hardware that is UNDEFINED power-on content, so no
      program can depend on it. Matching = dropping the fill (a cbios-repack patch), and
      the price is not bytes: disk/init.asm's RAMAD `$FF` gate KEYS ON this $C9 (C-BIOS
      hosts skip re-deriving RAMAD because RAMAD0 reads $C9), so it would flip the
      MSX-DOS boot path on every C-BIOS host -- a tier2 DOS-boot battery, for a value no
      program can observe. 🎚️ The `$F347` residual is TIER 6; CTRL (above) stays the
      item's TIER 4 face.
      ✅ **CTRL'S RAM HALF SHIPPED 2026-10-27** (Joost's ruling above). The block from the
      disk engine table to FAT_DEFER (DSK_ENGTAB, FSECTOR_BUF/SECTOR_BUF, FWBUF/WBUF and
      every disk.rom cell, $E04A..$E976) moved up $443 as one piece: TXTMAX $E36A -> $E7AD,
      so DSK_ENGTAB = $E48D and the cells end at FAT_DEFER $EDB9, under BASIC_WS_CEIL.
      install_basic_hooks (disk/kernel.asm) reads SNSMAT row 6 itself -- set_ramad seeds
      DRVCNT after it runs, and set_ramad's region had no room for the store (pasmo wrote
      an EMPTY disk.rom) -- and stores CTRL_HIMEM $E48D instead of DISK_HIMEM; asserted
      under the engine table rows. 🔮 plain 23320/$DE77, CTRL 24878/$E48D/1 drive on both:
      HIT ([`ctrlram_bootkeys.out`](scratchpad/ctrlram_bootkeys.out)). 🔮 MAXFILES=3, an
      OPEN write/read, CLEAR 300,&HD000, MAXFILES=0: every row equal, CTRL 1558 B above
      plain until the CLEAR: HIT ([`ctrlram_probe.py`](scratchpad/ctrlram_probe.py) ->
      [`ctrlram_run.out`](scratchpad/ctrlram_run.out)). Gate: bootkeys-acceptance row
      `ctrlram` ([`ctrlram_gate.out`](scratchpad/ctrlram_gate.out)); 🔪 K-CR1
      ([`ctrlram_knife.py`](scratchpad/ctrlram_knife.py)): the four files back to HEAD ->
      `ctrlram` alone DIVERGES (ZB 23313 / $DE77), rc=2, all five images restored
      ([`ctrlram_knife.out`](scratchpad/ctrlram_knife.out)). probes/disk/omsx_session.py's
      DRV_TRAMP range follows the move. Docs: concepts/disk.md, memory-map.md, rom-layout.md.
