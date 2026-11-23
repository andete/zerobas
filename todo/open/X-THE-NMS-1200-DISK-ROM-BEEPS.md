- [ ] **The NMS 1200 disk ROM beeps at boot (R0 = $55 at a cartridge's INIT); zerobas's
      disk ROM does not**
      🎚️ TIER 6 — a boot-state register only a cartridge's INIT
      🤖 **AUTONOMOUS** — lifted from D-ENTRYTIERS; picked up by tier.
      can read before anything else writes the PSG; pinned in biosl_run.py's ALLOW.
      (Lifted out of D-ENTRYTIERS on 2026-11-23 when that umbrella closed.)
