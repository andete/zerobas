- [ ] 🎯 **D-DISKROMHOST — ZEROBAS'S OWN DISK ROM AS A CONTRACT-FOLLOWING CARTRIDGE: ITS MSX-DOS HALF STANDS ON ITS OWN
      (Joost 2026-11-24: "this is exactly what I had in mind").**
      🎚️ TIER 1 — preparing disk support for C-BIOS (a host without BASIC): the DOS half must need nothing from zerobas
      BASIC, and must follow the host contract (docs/concepts/disk-rom-host.md) as a stock disk ROM does.
      🤖 **AUTONOMOUS** — step 1 done; step 2 (it changes the disk ROM's structure and RAM map) approved by Joost
      2026-11-24.
      STEP 1 (2026-11-24, zerobas's own source; scripts inline in the session): of disk/basic-resident-abi.inc's 104
      imports, 10 are unused; of the rest, 32 are BASIC CODE (interp / expr / float-arith / vars / strvar / field /
      files / str-engine / traps / pdfcb-body) and 62 are RAM CELLS (sysvars.inc). EVERY code import is called from a
      Disk BASIC statement handler -- in disk/kernel.asm hk_dsk (DSKI$ / DSKO$), hkc_body (COPY), hk_mkfloat (MKS$ /
      MKD$), hk_lrset (LSET / RSET), hk_system (CALL SYSTEM), hk_cv (CVI / CVS / CVD), hk_name (NAME), the RANDOM
      record helpers; in disk/fat.asm / driver.asm / runtime.asm / pageenv.asm only the BASIC file paths (OPEN,
      INPUT#, GET / PUT / FIELD, FILES, LOAD) import cells. The MSX-DOS path -- the DSKIO / DSKCHG / GETDPB / DSKFMT
      driver, the BDOS / FCB layer, the page-0 environment, INIT and the DOS boot bridge -- calls NO BASIC code; its
      only ties are four layout constants in disk/disk.asm: the sector buffers FSECTOR_BUF / FWBUF, FLD_END and
      TXTMAX_NODISK -- fixed addresses from zerobas's RAM map, not RAM the disk ROM claims.
      STEP 2 (⛔ Joost): the disk ROM claims its RAM by lowering HIMEM in INIT and keeps ALL its state inside the claim
      (the sector buffers, the DOS-path bridge block -- today $DDAE..$DF92, straddling DISK_HIMEM $DE77 --, the disk-only
      cells of scratchpad/ram_inventory_f380.md class C); patches H.RUNC and does its phase-2 set-up and the DOS boot
      from there, as a stock disk ROM does. ACCEPTANCE: zerobas's disk ROM, inserted as a cartridge into a VG-8020
      (real MS-BASIC host) in openMSX, boots MSX-DOS -- host-independent, so a C-BIOS host can take it.
      STEP 3: memory parity on the DISK build vs the CF-3300 (plain boot: FRE, the layout cells), after D-BOOTCELLS.
      ✅ STEP 2 APPROVED (Joost 2026-11-24: "excellent news. Go ahead"). SEQUENCED after D-BOOTCELLS's swap (both touch
      basic/interp.asm init's HIMEM / layout path), as an isolated-instance unit with its own FULL gate.
      STEP 2a DONE (2026-11-24, isolated instance): INIT is phase 1 only (slot byte, the HIMEM claim, the hooks -- HPHYD
      and H.RUNC are rows of install_basic_hooks' table now); the first H.RUNC call runs `init_p2` (the rest of the
      set-up) and the DOS boot, and the handler leaves the hook five RETs, as the CF-3300 and the VG-8020 + HBD-F1 do.
      ACCEPTANCE MET: zerobas's disk ROM as a cartridge in the VG-8020 boots MSX-DOS 1.03 from inside the cold start's
      H.RUNC (before: from INIT) -- scratchpad/AE_diskhost_vg8020.out; the DISK machine's HIMEM / FRE(0) / FRE("") /
      MEMSIZ / STKTOP / FILTAB still equal the CF-3300's (scratchpad/AE_diskhost_fre.out). Bytes: hrunc_h took
      fat_bufinit's (inline in init_p2 now) and rh_init's (moved to the $4EDE pad).
      STEP 2b ⛔ (a ruling): the RAM. Every BASIC-phase cell the disk ROM keeps is already inside [$DE77, $F380); what
      lies below DISK_HIMEM is the DOS-phase block -- GETWRK_AREA $DD0E (128 B, the $4030 work area MSXDOS.SYS places
      its kernel under) and the slot bridges INT_H_HIRAM $DDAE..$DF92 -- written only at DOS entry (install_dos_env),
      when BASIC is gone, and at the CF-3300's own addresses ($DD0E is its DRVTBL+3 value, $DDAE its $0038 target;
      its own H.RUNC claim stops at $DF93, above both). Options: (a) keep them (reference-faithful); (b) move both into
      the claim (e.g. over the engine-table rows, dead under DOS) -- changes the DOS kernel's placement, the TPA top
      at $0006 and $0039 against the CF-3300. Also open: the reference's TWO-STEP claim ($F195 in INIT, $DF93 in
      H.RUNC, with the layout rebuilt under each -- docs/concepts/disk-rom-host.md, Open) against zerobas's one-step
      $DE77 with no rebuild, which leaves an MS-BASIC host's layout inside the claim when no DOS disk boots.

