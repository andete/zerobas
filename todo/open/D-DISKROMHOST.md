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

