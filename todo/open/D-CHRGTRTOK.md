- [ ] **D-CHRGTRTOK — CHRGTR TREATS THE NUMERIC-CONSTANT TOKENS $0B-$1F AS PLAIN CHARACTERS; THE VG-8020'S DECODES THEM**
      🎚️ TIER 6 — every edge (machine code -- a USR routine or a CALL handler -- walking program text with CHRGTR across
      a constant; zerobas's own interpreter reads constants without it; filed 2026-11-18).
      🤖 **AUTONOMOUS** — docs/bios/CHRGTR.md R-C-NUM / R-C-CONST / R-C-10 / R-C-1E / R-C-CHAIN
      ([`XCHRGTR_run4.out`](../../scratchpad/XCHRGTR_run4.out), [`XCHRGTR2_run1.out`](../../scratchpad/XCHRGTR2_run1.out)): on a numeric token the VG-8020 writes CONTXT ($F666) := the
      text after the constant, CONSAV ($F668) := the token, CONTYP ($F669) := 2 / 4 / 8, CONLO ($F66A..) := the value,
      and returns A = the token, a logical result's F and HL = $46E6; the next call from there returns the text after
      the constant. $10 resumes at CONTXT; $1E returns A = CONSAV.
      zerobas returns each as a plain character and writes none of the cells. The program text is the same format on
      both machines (docs/concepts/program-text.md), so such code meets these tokens on zerobas too. Priced when
      picked up; not cheap (a decoder for 19 tokens).
