- [ ] **D-F37DDTA — THE DTA CELL STARTS AT $0080 AND DSKRST DOES NOT RESET IT; THE REFERENCES: $0000, AND DSKRST -> $0080**
      🎚️ TIER 6 — every edge (filed 2026-11-22).
      🤖 **AUTONOMOUS** — docs/bdos/SYSTEM.md R-BS-DTA: before any SETDTA the references' DTA cell ($F23D) reads
      $0000 (zerobas $0080, dta_init, disk/driver.asm); after SETDTA $A800 both read $A800; DSKRST then resets it
      to $0080 on the references, zerobas keeps $A800.
