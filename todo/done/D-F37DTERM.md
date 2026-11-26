- [x] 🐛 **BDOS $00 (TERMINATE) THROUGH $F37D RETURNS ON ZEROBAS; ON THE CF-3300 IT ENDS THE BASIC PROGRAM (D-F37DTERM,
      found 2026-11-26 by D-DISKCONTRACT gap 6).**
      🎚️ TIER 6 — every edge: a program that calls function 0 through $F37D from BASIC.
      🤖 **AUTONOMOUS** — measured; the fix needs disk-ROM room and touches BASIC's program end.
      MEASURED (by hand, 2026-11-26; the stub `ld c,0 / call $F37D / ret` as a USR from `20 X=USR(0):PRINT "AFTER"`):
      the CF-3300 ends the program SILENTLY -- no `AFTER`, no error message, `Ok`, the CLEAR's FRE(0) kept (15503); a
      bdosf37d row for $00 never finishes there (the harness reads "NOTHING WAS MEASURED"). zerobas RETURNS (A = 0
      since D-F37DHIGH, $FF before) and prints `AFTER`. tests/test_bdosbasic.py pins zerobas's A = 0 for $00 with this
      item named.
      NOT MEASURED: $00 through $F37D with NO BASIC (a ROM program or a boot code on the BASIC-less C-BIOS host) -- what
      "terminate" means there is the port's question.
      FIX DIRECTION: a bdos_tab row for $00 that leaves to BASIC's program end as END does (the main ROM's -- so a
      BASIC-side seam, and a guard for the BASIC-less host). Disk-ROM room first (docs/disk/port-readiness.md row 5).
      ✅ **FIXED 2026-11-26 (the program end; the same line's rest filed as [D-F37DTERMLINE](../open/D-F37DTERMLINE.md)).** A bdos_tab
      row for $00 (disk/kernel.asm bb_term): under BASIC (DISKVE's high byte 0) it does what END does to the run --
      ONEFLG 0, ENDFLAG 1 (zerobas's cells, now exported to the disk ROM's resident ABI) -- and returns A = 0; under
      MSX-DOS nothing changes. New `make f37dterm-acceptance` (probes/disk/disk_probe_f37dterm.py): the next line no
      longer runs and FRE(0) is kept -- SAME; the rest of the CALLING line still runs (AFTER printed) -- pinned
      ([AE_f37dterm1.out](../../scratchpad/AE_f37dterm1.out), [AE_f37dterm2.out](../../scratchpad/AE_f37dterm2.out)).
