- [ ] 🔴 **A TYPE MISMATCH IS RAISED AT A DIFFERENT POINT OF THE EXPRESSION THAN ON
      THE VG-8020, IN BOTH DIRECTIONS (D-TMORDER, found 2026-10-24 by D-DEFERRSTUDY).**
      🎚️ TIER 6 — which side effects happen before a type mismatch
      🤖 **AUTONOMOUS** — the reference settles it; ten cases are already measured.
      📏 [`tmorder_run.out`](../../scratchpad/tmorder_run.out) ([`spec-basic-deferr-study.md`](../../docs/spec-basic-deferr-study.md) §2b),
      a USR call counter after the mismatch: the VG-8020 runs it in `1+"X"+USR(0)`,
      `1-"X"+USR(0)`, `1+"X"+USR(0)+1` (count 1) where zerobas raises first (0), and
      raises at once in `"X"+1+USR(0)` (0) where zerobas runs on (1). The other six
      variations agree (0). The error itself is the same everywhere; only what runs
      before it differs, so it is latent until an operand has a side effect.
