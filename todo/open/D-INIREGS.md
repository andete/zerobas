- [ ] **D-INIREGS — INIGRP / INIMLT RETURN OTHER DE AND HL ON ZEROBAS**
      🎚️ TIER 6 — every edge (unpublished return registers; filed 2026-11-18).
      🤖 **AUTONOMOUS** — docs/bios/INIGRP.md R-IG-REGS, INIMLT.md R-IM-REGS ([`XINIG_run3.out`](../../scratchpad/XINIG_run3.out)):
      the VG-8020 returns DE $7F03 / $0000 and HL $F3D1 / $F3DB; zerobas DE $88D1 and HL $F3E7 in every case.
      A, F and BC agree. Priced when picked up.      💰 **PRICED 2026-11-20: left unmatched.** The VG-8020's INIGRP / INIMLT return SETGRP's / SETMLT's own DE / HL
      ($7F03 / $F3D1, 0 / $F3DB -- since D-SETREGS exactly what zerobas's SET calls return), so its mode calls END on
      the SET call. C-BIOS's end on chgmod_finish, which re-sends R0-R7 through HL / DE and enables the display;
      restructuring that shared finish for two unpublished registers is risk with no measured program behind it.
