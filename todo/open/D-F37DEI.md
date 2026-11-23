- [ ] **D-F37DEI — THE $F37D BDOS LEAVES INTERRUPTS ON; BOTH REFERENCES LEAVE THEM OFF**
      🎚️ TIER 6 — every edge (filed 2026-11-22).
      🤖 **AUTONOMOUS** — docs/bdos/SYSTEM.md R-BS-DI: after each of the 15 calls (entered with interrupts off) the
      references' interrupts are off, zerobas's on. Where it enables them is disk/ (the $F37D path's exit).
