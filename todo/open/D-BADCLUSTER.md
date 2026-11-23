- [ ] 🔴 **A FILE WHOSE CLUSTER CHAIN POINTS PAST THE VOLUME LOADS AS AN EMPTY
      PROGRAM HERE, SILENTLY; THE CF-3300 SAYS `Disk offline` — AND `DSKI$` PAST THE
      LAST SECTOR DIVERGES THE OTHER WAY (D-BADCLUSTER, found 2026-09-29).**
      🎚️ TIER 6 — corrupt media: neither shape arises on an intact disk.
      🤖 **AUTONOMOUS** — the reference settles both.
      📏 A crafted copy of `disk/test720.dsk` with one extra root entry, `BAD.BAS`,
      first cluster $7F0 (past a 720 KB volume), size 1000
      ([`errkeep3_probe.py`](../../scratchpad/errkeep3_probe.py) →
      [`errkeep3_run.out`](../../scratchpad/errkeep3_run.out),
      [`errkeep3_run2.out`](../../scratchpad/errkeep3_run2.out)):
      • `LOAD "BAD.BAS"` — CF-3300 `Disk offline` (70), with or without a file open;
        zerobas NOTHING (ERR 0, `LIST` empty): the FAT walk treats an out-of-volume
        cluster as the end of the chain and loads zero bytes without complaint.
      • `A$=DSKI$(0,4000)` — CF-3300 no error (ERR 0); zerobas `Disk I/O error` (69).
      The open channel survived the failed LOAD on the CF-3300 (a later `PRINT #1`
      raised nothing), so LOAD does NOT close files there — worth knowing for
      D-ERRKEEP2 whenever a witness turns up.
