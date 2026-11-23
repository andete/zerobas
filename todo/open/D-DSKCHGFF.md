- [ ] **D-DSKCHGFF — DSKCHG NEVER ANSWERS B $FF ("CHANGED"); THE REFERENCE DOES WHEN THE DISK'S MEDIA BYTE IS NOT C**
      🎚️ TIER 6 — every edge (filed 2026-11-22).
      🤖 **AUTONOMOUS** — docs/disk/DSKCHG.md R-DC-READ (scratchpad/XDENT3_run1.out XE3 0): DSKCHG ($4013) with C $F8
      on the $F9 disk, at a call that reads: the VG-8020 + NMS 1200 answers B $FF (A $F9, the $F9 DPB, F $38);
      zerobas B 0. A DOS that trusts B 0 keeps its old FAT for a disk of another format. Fix in disk/ with
      D-DSKCHGREGS (compare the disk's media byte with C).
