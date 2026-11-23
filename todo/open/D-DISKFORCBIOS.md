- [ ] **D-DISKFORCBIOS — WHAT A C-BIOS DISK-DRIVER PORT NEEDS FROM ZEROBAS: DSKIO / CHOICE / MTOFF PAGES, AN NMS 8250 ROW, A DRIVER-RAM NOTE**
      ➕ 2026-11-22: (a) DONE -- docs/disk/DSKIO.md and docs/disk/CHOICE.md (with MTOFF) FINAL. (c) and (d) DONE --
      docs/concepts/disk.md "The driver alone needs far less" (the driver's own cells, read from its code and the
      work-area map) and "The DOS 1 driver interface's own routines are not entries". LEFT: (b) the NMS 8250 row,
      (e) blocked on 2-Tier2-a.
      ✅ (b) DONE 2026-11-22: a reference-only NMS 8250 row (`biosl_run.py --row nms8250`; spec_rules' c.ref_only,
      spec_live does not re-run it) on PHYDIO, DSKIO, DSKCHG, GETDPB and CHOICE / MTOFF -- every rule there now
      holds on all three interfaces, the interface's own values per row (scratchpad/AE_speclive_nms8250.out). Found:
      interrupts ON after every call on the NMS 8250 (off on the other two); it refuses media $FF in PHYDIO and
      $FC .. $FF in GETDPB (R-GD-REFUSE); MTOFF A 3 with F / BC / HL kept; DSKCHG's 48 / 96 model the same case for
      case; its first call after start-up, a track-1 read, got track 0 (R-PD-FIRSTE, measured twice). DSKFMT not
      run: its choices are each interface's own. Summary for the port: docs/concepts/disk.md "What every interface
      keeps". ⏸️ ONLY (e) LEFT, BLOCKED on 2-Tier2-a.
      🎚️ TIER 1 — entry points (the disk-ROM entries are the BDOS / disk-BIOS focus's own subject; filed 2026-11-22).
      🤖 **AUTONOMOUS** — C-BIOS is weighing folding the disk BIOS calls in (0.32 / 0.33) and ports by spec page. Wanted:
      (a) spec pages for the driver entries without one: DSKIO ($4010, called DIRECTLY -- docs/bios/PHYDIO.md
      measures it only through $0144 / H.PHYD), CHOICE ($4019: HL and the registers only -- its string is ROM bytes,
      not readable in the clean room) and MTOFF ($401F: how to observe the motor without reading the FDC's
      memory-mapped registers is the design question); (b) an NMS 8250 row (built-in drive, the Philips-style FDC)
      for the disk pages -- do the black-box rules hold on a third interface, or do some depend on it (DSKCHG's
      count, the motor timing)?; (c) a note in docs/concepts/disk.md of the RAM the DRIVER itself needs, apart
      from the FAT / BDOS layer and zerobas BASIC's layout (TXTMAX_NODISK, the shared buffers); (d) the DOS1 driver
      interface's internal entries (INIHRD, DRIVES, INIENV, DEFDPB, MYSIZE / SECLEN, OEMSTA, DSKSTP) are not
      published entries a program calls -- say so in disk.md, measure only what a black box can see; (e) the
      MSX-DOS 1 boot test is 2-Tier2-a (blocked): C-BIOS would like the same disk image when it lands.
