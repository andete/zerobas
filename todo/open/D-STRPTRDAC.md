- [ ] **D-STRPTRDAC — THE REFERENCE KEEPS THE CURRENT STRING RESULT AT DAC+2; ZEROBAS KEEPS STRPTR APART**
      🎚️ TIER 4 — RAM usage (VG-8020) (filed 2026-11-20, from D-PAINTRAMCLASH's measurement).
      🤖 **AUTONOMOUS** — scratchpad/STRPTR_run1.out: after `A$="AB"+"CDE"` (and LEFT$, a literal, CHR$+...) both references
      hold DAC+2 ($F7F8) -> TEMPST $F67A, the result's descriptor; TEMPPT ($F678) -> $F67A. zerobas: STRPTR (now SLTWRK
      $FD0E) points at DSCTMP ($F698) for a literal and at nothing matching otherwise. Adopting DAC+2 puts the pointer
      inside zerobas's FAC (FAC = DAC, $F7F6), so first AUDIT every STRPTR use (181 in basic/ and sub/) for one held
      across a numeric evaluation. Price it against TIER 4's other RAM items before starting.
