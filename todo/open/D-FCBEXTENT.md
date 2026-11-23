- [ ] **D-FCBEXTENT — SEQUENTIAL WRITES IGNORE THE FCB'S EXTENT AND CURRENT RECORD (THEY WRITE AT ZEROBAS'S OWN POSITION); FOPEN OPENS ANY EXTENT**
      🎚️ TIER 6 — every edge (filed 2026-11-22).
      🤖 **AUTONOMOUS** — docs/bdos/FILES.md R-BF-EXTENT (XB2 4-9): with +12 = $FF (left by FMAKE over a pre-filled
      FCB) the references' WRSEQ answers A 1 and writes nothing, FOPEN answers A $FF (no extent 255); zerobas's write
      and open succeed, so FSIZE reads 1 record against 0. disk/ (wrseq_body, bdos_open: the extent).
      Round 3 (XBFILE3, R-BF-SEQ3 / R-BF-OPEN3) WIDENED it: the references' WRSEQ writes at the FCB's current record
      (+32 AND $7F) -- CR $85 writes record 5 (a 768-byte file), CR $FF record 127 (16384 bytes, then extent 1, CR 0)
      -- and FOPEN refuses an extent the file lacks (+12 1 on a 0-record file); zerobas writes record 0 every time and
      opens any extent. A program that positions by CR (or by extent) writes at the wrong place on zerobas: tier 6
      as filed, but read it again when a corpus program writes files.
