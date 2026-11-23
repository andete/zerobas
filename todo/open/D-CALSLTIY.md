- [ ] **D-CALSLTIY — IY IN A CALLF TARGET (AND IN A TARGET IN AN EXPANDED SLOT) DIFFERS FROM THE REFERENCES'**
      🎚️ TIER 6 — every edge (a target reading IY on entry after CALLF, or after CALSLT into an expanded slot;
      filed 2026-11-18).
      🤖 **AUTONOMOUS** — docs/bios/CALLF.md R-CF-IY, docs/bios/CALSLT.md R-CS-IY ([`XCALSLT_run4.out`](scratchpad/XCALSLT_run4.out),
      [`XCALSLT_run4c.out`](scratchpad/XCALSLT_run4c.out)): in a CALLF target the references' IY holds the slot ID
      over the entry F (IY was $8765); zerobas's the slot ID over $55 (a slot that is not expanded) or $8388 (its
      expanded RAM). For a call into the expanded RAM 3-0 the CF-3300's IY in the target is $0314, whatever the
      caller's IY and the page; zerobas's CALSLT passes the caller's. After the call both return the target's IY.
      CALLF publishes IY as destroyed; the values are not published. Priced when picked up.      💰 **PRICED 2026-11-20: left unmatched.** Same core as D-CALSLTSTACK; CALLF publishes IY as destroyed.
