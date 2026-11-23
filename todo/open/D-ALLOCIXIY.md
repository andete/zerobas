- [ ] **D-ALLOCIXIY — ALLOC THROUGH $F37D LEAVES IX / IY; THE REFERENCES RETURN THE DPB AND FAT-BUFFER ADDRESSES**
      🎚️ TIER 6 — every edge (filed 2026-11-22).
      🤖 **AUTONOMOUS** — docs/bdos/SYSTEM.md R-BS-ALLOC: ALLOC ($1B, E 0) returns IX / IY = $F197 / $E597 (VG-8020 +
      NMS 1200) and $F195 / $E595 (CF-3300), the DPB and the FAT buffer in the disk work area; zerobas leaves IX /
      IY as entered. A, BC, DE, HL agree. A program that reads the DPB through IX gets garbage on zerobas.
