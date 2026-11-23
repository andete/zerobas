- [ ] 🔧 **D-PINSTALE — gates-fast SHOULD RE-MEASURE THE KEYWORD SWEEPS WHEN THE ROM HAS MOVED SINCE THEIR PINS
      (filed 2026-10-08 by D-STATICEMU's first ROM commit)**
      🎚️ APPARATUS — a manual loop step stands in for a check the tool can make.
      📏 D-STATICEMU took kwsweep / kwtime / kwram out of STATIC and keeps the last
      pins across the build wipe. For a docs commit that is right; for a ROM
      commit the pins describe the OLD ROM, `make tiers-md` renders stale evidence
      and FULL's post-check goes red (D-PUTDIR: 169/170, two T4/T5 cells).
      ➡️ Record the ROM hashes a pin was measured against (beside the pin, or in
      it), and have `run_gates.py --static` run the three sweeps itself when the
      built ROM's hashes differ -- docs commits stay at ~2 min, ROM commits pay
      the sweeps once, as before. A selftest arm for both branches.
      🤖 **AUTONOMOUS** — a tool change; the gate's own selftest settles it.
      ✅ **FIXED 2026-10-09.** `tools/run_gates.py` writes `build/sweeps-rom.txt` --
      the ROM hashes -- after a pool in which all three sweeps passed, keeps it
      across the build wipe with the pins, and a run that would skip the sweeps
      RUNS them when the built ROM differs or no stamp is on record
      (`sweeps_needed`, four selftest arms incl. a NEGATIVE). 📏 Measured end to
      end ([`pinstale_fast1.out`](../../scratchpad/pinstale_fast1.out),
      [`pinstale_fast2.out`](../../scratchpad/pinstale_fast2.out)): the first gates-fast
      found no stamp and ran the sweeps (1833 s, 48/48 green) and wrote it; the
      second, same ROM, skipped them (129 s, 45/45). 🔮 Predicted both: HIT.
