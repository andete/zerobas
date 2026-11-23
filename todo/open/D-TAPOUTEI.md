- [ ] **D-TAPOUTEI — TAPOUT LEAVES INTERRUPTS OFF; THE REFERENCES KEEP THE ENTRY STATE**
      🎚️ TIER 6 — every edge (filed 2026-11-21).
      🤖 **AUTONOMOUS** — From the C-BIOS 0.32 port's measurements (Joost, 2026-11-21; headless openMSX, BIOS calls made directly, VG-8020 = NMS 8250 unless noted). Check zerobas against them first.
      The VG-8020's and NMS 8250's TAPOUT: DI in -> DI out, EI in -> EI out. zerobas's leaves interrupts off. A spec page
      rule for TAPOUT may already pin the DI-in half only: check docs/concepts/cassette.md first.
