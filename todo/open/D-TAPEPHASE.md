- [ ] **D-TAPEPHASE — OUR TAPE CYCLES START HIGH; THE VG-8020'S START LOW (THE SIGNAL IS INVERTED)**
      🎚️ TIER 6 — every edge (filed 2026-11-21).
      🤖 **AUTONOMOUS** — Found by scratchpad/castrace_lead.py run 4 (scratchpad/CASTRACE_LEAD_run4.out, a CSAVE on
      each machine, a watchpoint on the PPI's cassette-out bit): the VG-8020's start bit is LO 1487-1568 T then HI
      1492, its leader ends on a HI half; zerobas's start bit is HI 1504 then LO 1493-1498, its leader ends on a LO half
      -- every cycle the other way up. The VG-8020 reads our recordings anyway (cassave-acceptance's reference-load leg)
      and our reader takes real tapes (the corpus), so no read fails that is known. Open: whether a reader that keys on
      one edge (a turbo loader, a later MSX) cares; the CF-3300's phase. A fix swaps CASW_1 / CASW_0 in cas_cycle /
      cas_cycle_last and moves the compensations (CAS_DUTY, CAS_BITCOMP*, CAS_LEADCOMP, CAS_STARTCOMP) to the other half:
      re-solve them from a new trace, not by hand.
