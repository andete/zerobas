- [ ] **D-WRZEREXT — WRZER PAST 16 KB LEAVES +12 0 AND RR'S LOW BYTE IN +32; THE REFERENCES SPLIT RR INTO EXTENT AND RECORD**
      ➕ 2026-11-22: WRRND too (docs/bdos/BLOCKS.md R-BK-PAST255FCB, scratchpad/XRRND1_run1.out XRR 3 / 4): after
      WRRND 300 the references hold +12 2, zerobas 0; after WRRND 44 they point +28 / +30 at its cluster, zerobas not.
      🎚️ TIER 6 — every edge (filed 2026-11-22).
      🤖 **AUTONOMOUS** — docs/bdos/BLOCKS.md R-BK-ROUND7 (scratchpad/XBBLK7_run1.out, run2.out XK7 2 / 7): WRZER
      ($28) through $F37D at RR 156 and RR 300: the VG-8020 + NMS 1200 and the CF-3300 leave +12 1 / 2 (RR / 128)
      and +32 28 / 44 (RR mod 128); zerobas leaves +12 0 and +32 156 / 44 (RR AND $FF). Size, clusters and +33 ..
      agree. Round 8 (R-BK-ROUND8, scratchpad/XBBLK8_run1.out, run2.out XK8 4 .. 9): the same on L.TXT, and WRZER
      below the end points +28 / +30 at the cluster holding RR on the references (round 9, XK9 3: $1B / $19 at RR
      200; zerobas keeps the last). Round 10 (R-BK-ROUND10, scratchpad/XBBLK10_run1.out, run2.out XKA 15): after a
      growing WRZER with a gap the references point +28 / +30 at the cluster the zero fill ended in (before RR's);
      zerobas at RR's own; round 11 (XKB 7, scratchpad/XBBLK11_run1.out) the same, and round 9 (XK9 10, growing to
      RR 600: $72 / $4A on the references, $73 / $4B on zerobas -- D-WRZER64K's remainder). WRBLK and
      RDBLK ignore +12 / +32 on all three. A program mixing random and sequential access past 16 KB (RDSEQ after WRZER) reads from another
      place. Check WRRND / RDRND / SETRND past 16 KB too (RECORDS.md measured only below it). disk/ (WRZER's
      FCB update: the extent / record split).
