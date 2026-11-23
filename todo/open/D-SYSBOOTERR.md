- [ ] 🔴 **`CALL SYSTEM` WITH MSXDOS.SYS DELETED: THE CF-3300 LOOPS ON `Boot error` /
      `Press any key for retry`; ZEROBAS RESTARTS DISK BASIC WITH ITS BANNER
      (D-SYSBOOTERR, found 2026-10-09 by D-CALLSYSTEM's `doskillsys` row).**
      🎚️ TIER 6 — `CALL SYSTEM` after the system file is deleted
      🤖 **AUTONOMOUS** — the reference settles it.
      [`callsystem_after.out`](scratchpad/callsystem_after.out) `doskillsys`.
      Both hand the same boot sector the same step-7 call; what the CF-3300
      does when its loader finds no MSXDOS.SYS (the retry prompt) is not ours.
      Measure first which documented entry the retry goes through (PC at the
      disk ROM's published entries only — no stepping into the ROM).
