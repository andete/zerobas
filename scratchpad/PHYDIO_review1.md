# PHYDIO.md DRAFT 1 -- review pass 1 (test writer, 2026-11-20), NOT YET ANSWERED

A fresh reviewer read only the page, XDSK1_run2.out, XDSK2_run1.out, xdsk1.asm and xdsk2.asm. It confirmed every
row-D reference record against its rule and the tables' counts. Findings to answer BY MEASURING (round 3), then fix the page:

1. Unpinned:
   - media $F8 / $FF read only at sector 0 (try DE 9 and DE 720 with C $F8: the geometry and bound);
   - a write straddling the end (DE 1439, B 2): partial or refused;
   - interrupts entered ON for the media refusal and the past write;
   - E = entry F on the error rules (every error case had F $00 / $01): use F $5A / $A4 / $FF;
   - R-PD-FFFF "512 zeros" rests on a sum (record a CRC, or narrow the rule);
   - R-PD-NODISK "A as entered" (A was always 0: try A 1 on row N, safe there);
   - "B 0 = 256" vs "unbounded" (a WRITE with B 0 from DE 1184 separates them).
2. Rival rules:
   - $FFFF is not refused vs a 16-bit wrap in the bound check (DE $FFFE B 1, DE $F000 B 1; marker writes to find
     the sector read);
   - write-past: transfer-then-stop vs refuse up front (F $11 hints at refuse);
   - the media rule is circular (C $80, $F0, $F7, $FA separate the candidates);
   - D = entry A asserted although the Open list says it is unmeasured (word the rule as measured).
3. Citations: the Summary's "transfers the same bytes" is false for case 04 (D-PHYDIOB0); the Open list's
   "three sectors of case 15" is wrong (2 sectors, 1 KB); R-PD-WRITE should cite 07 / 10 as the proof the write
   happened.
4. Open-list gaps: error precedence (bad media + past sector; bad media on a write), writes of more than one sector
   and with F other than $01, memory past HL + 1 KB on a past read.
