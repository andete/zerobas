- [ ] **DISK BASIC: THE CF-3300 OPENS DISK FILES ONLY AS #1-#6 ("Bad file number" for #7+, EVEN WITH MAXFILES=15); ZEROBAS OPENS
      ALL 15 (D-DISKFNUM6).**
      🎚️ TIER 6 — every error (a program that opens a disk file as #7 or higher errors on the reference and runs here).
      🤖 **AUTONOMOUS** — black box, the CF-3300 the reference; screen only.
      MEASURED 2026-11-28 (D-COPYSLOW U1, [bfiles_probe.py](../../scratchpad/bfiles_probe.py), [AE_bfiles_u1.out](../../scratchpad/AE_bfiles_u1.out)): MAXFILES=15 (Ok on both), then
      OPEN of a disk file AS #7 or AS #15 with nothing else open: CF-3300 "Bad file number" (and PRINT #15 "File not
      OPEN"), zerobas opens it. #1-#6 open on both; "CRT:" AS #7 opens on both, so the limit is the disk's: the CF keeps
      a disk channel as one of SIX 37-byte MSX-DOS FCBs at $DEB5-$DF92. Not yet measured: the VG-8020 + NMS 1200's limit
      (a second reference, may differ); whether the CF refuses at OPEN only or at MAXFILES time in some other path.
      Fix belongs to D-COPYSLOW's staged redesign, step 1 (the channel table into the CF's six FCB slots) -- not alone.
