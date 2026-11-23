- [ ] **D-PLAYLONGTIME — A RING-FILLING PLAY RETURNS 14-15 JIFFIES EARLIER THAN ON THE VG-8020**
      🎚️ TIER 5 — on-par speed (filed 2026-11-20).
      🤖 **AUTONOMOUS** — `PLAY "T255L64CDEFGAB..."` (40 notes, the ring fills) returns after 86 jiffies here and
      100-101 on the VG-8020, the same on 3e302ee5 (before D-TRGFLGISR / D-PLAYVOICEORDER):
      scratchpad/PLAYLONG_run1.out, probe scratchpad/playlong_probe.py (program and direct forms). D-PLAYRATE's floor
      (closed) and playqueue-acceptance's tolerance cover shorter cases. Measure first: the total play time
      (PLAY(0) = 0) against the reference, and whether it is the start or the wait that differs.
