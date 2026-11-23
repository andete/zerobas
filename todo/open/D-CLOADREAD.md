- [ ] 🔍 **D-CLOADREAD — AFTER CLOAD zerobas CALLS H.READ; THE VG-8020 PRINTS `Ok` AND
      CALLS H.MAIN ALONE (measured 2026-10-11, from D-AUTORUN)**
      🎚️ TIER 6 — invisible to openMSX's autorun (D-AUTORUN's 9/9) and to
      BASIC; only a program that hooks H.READ itself can tell.
      🤖 **AUTONOMOUS** — but priced against the binding wall: main page 1
      has 4 B (2026-10-11), and the fix is a path flag CLOAD sets and
      `repl` tests before `call H_READ`.
      📏 [`autorun_seq_probe.out`](scratchpad/autorun_seq_probe.out): the
      VG-8020's log ends `2RMM` -- the prompt after the marker line, then
      CLOAD's lone M. Unmeasured: LOAD (no `,R`), MERGE and BLOAD's returns.
