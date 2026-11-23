- [ ] **D-SETREGSCBIOS — SETTXT / SETT32 / SETGRP / SETMLT RETURN C-BIOS'S LEFTOVER REGISTERS SINCE THE REBASE**
      🎚️ TIER 6 — every edge (filed 2026-11-22).
      🤖 **AUTONOMOUS** — d23d87b's bodies return DE / HL the other way round and another F (R-TX-REGS / R-T3-REGS /
      R-GR-REGS / R-MT-REGS); C-BIOS declined the fix (Joost: "skip"; documented "Registers: All", no program reads
      them) and zerobas no longer carries setregs-order.patch. Listed on the four pages. Re-carry only if a program
      is found that reads them (~5 B).
