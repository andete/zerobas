- [ ] **D-BDOSCARRY — SNEXT / SFIRST ANSWER "NOT FOUND" (A $FF) WITH THE CARRY CLEAR; BOTH REFERENCES SET IT**
      🎚️ TIER 6 — every error (filed 2026-11-22).
      🤖 **AUTONOMOUS** — docs/bdos/FILES.md R-BF-CARRY (scratchpad/XBFILE1_run1.out, run2.out, cases 4 and 10): through
      $F37D every A $FF answer carries the carry SET on the VG-8020 + NMS 1200 and the CF-3300 (F $45); zerobas's
      FOPEN does too, its SNEXT and SFIRST do not (F $44). A caller testing `jr c` after a search misses the end on
      zerobas. disk/ (snext_body / sfirst_body's exit).
      Round 3 (XBFILE3 XB3 13): FDEL of a missing file -- A $FF, carry SET on both references -- carry clear on
      zerobas too; FREN / FSIZE of a missing file agree.
