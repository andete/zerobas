- [ ] 🐛 **BDOS $00 (TERMINATE) THROUGH $F37D RETURNS ON ZEROBAS; ON THE CF-3300 IT ENDS THE BASIC PROGRAM (D-F37DTERM,
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
