- [ ] 🔬 **D-BRIDGEIX — THE HOST SUBROM BRIDGE KEEPS IX (AND A, F) THE WAY THE MACHINE DOES NOT
      (found 2026-10-22 by D-PLAYIY)**
      🎚️ TIER 6 — apparatus: a caller that keeps IX across a tenant call is green on the host
      and wrong on the machine, exactly as IY was.
      🤖 **AUTONOMOUS** — make tests/msxtest.py's bridge set IX to a poison value after the
      call (sr_slot's contract: HL/DE pass through, IY survives, the rest is clobbered); every
      test that goes red names a caller to check against the real machine before the test is
      blamed.
