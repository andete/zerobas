- [ ] **D-F37DREGS — THE $F37D BDOS RETURNS OTHER WORKING REGISTERS THAN BOTH REFERENCES**
      🎚️ TIER 6 — every edge (filed 2026-11-22).
      🤖 **AUTONOMOUS** — docs/bdos/SYSTEM.md R-BS-WORK / R-BS-SLOT: the two references agree on F and the open
      parts of BC / DE / HL / IX for every case, and leave IY = the inter-slot call's value ($0110 / $0314); zerobas
      differs (F, HL / BC working values, IX / IY as entered). Working values; fix only if a caller is found.
