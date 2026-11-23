- [ ] **D-CNVCHRCP20 — CNVCHR'S UNDOCUMENTED F: `cp $20` MATCHES THE VG-8020 EXACTLY**
      🎚️ TIER 6 — every edge (filed 2026-11-21).
      🤖 **AUTONOMOUS** — From the C-BIOS 0.32 port's measurements (Joost, 2026-11-21; headless openMSX, BIOS calls made directly, VG-8020 = NMS 8250 unless noted). Check zerobas against them first.
      With `cp $20` the undocumented F bits match the VG-8020 ($A3 for a converted code); zerobas's cnvchr-flags.patch
      (`cp $FF`) does not. docs/bios/CNVCHR.md's F rule decides; re-check its cases.
