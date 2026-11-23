- [ ] **D-DSKCHGREGS — DSKCHG'S "UNKNOWN" ANSWER RETURNS WORKING VALUES WHERE THE REFERENCE RETURNS THE MEDIA BYTE**
      🎚️ TIER 6 — every edge (filed 2026-11-22).
      🤖 **AUTONOMOUS** — docs/disk/DSKCHG.md R-DC-UNKNOWN / R-DC-F (scratchpad/XDENT2_run1.out): when DSKCHG ($4013)
      answers B 0 (after 3 s idle, or first), the VG-8020 + NMS 1200 returns A = the disk's media byte, C as entered,
      DE = HL + 19, F $50; zerobas A $03, C 0, DE $0007, F $04, HL $A412. Its clock (B 1 within ~1 s, B 0 after
      ~3 s) and its DPB are the reference's. Fix with D-GETDPBMEDIA (the same disk/ code).
