- [ ] 🔴 **A KNIFE HARNESS SCORES THE ROWS A CRASHED PROBE NEVER PRINTED AS UNMOVED
      (D-KNIFEROWS, found 2026-10-09 by D-CALLSYSTEM's K-CS4).**
      🎚️ APPARATUS — knife harness completeness
      🤖 **AUTONOMOUS** — mechanical.
      The `*_knives.py` harnesses in `scratchpad/` share one template
      (`readflt_knives.py` onward): they compare only the rows a cut run
      printed with the baseline, so a probe that dies part-way reports its
      missing rows as unmoved. K-CS4 said "moved nothing" that way and a
      load-bearing store was removed on the strength of it
      ([`callsystem_knives_r1.out`](../../scratchpad/callsystem_knives_r1.out)).
      [`callsystem_knives.py`](../../scratchpad/callsystem_knives.py) now refuses an
      incomplete run; give the other harnesses the same check (a FAIL can only
      hide an over-move there, never fake a PASS, but that is still blindness).

      - [ ] **B3 (a) / (b): SEQREAD after a random move on an FMAKE'd file, and a repositioned
            record past 255** -- 🎚️ TIER 6 — no measured program does either (above): (a) a
            SEQREAD whose FCB record equals the counter reads on from the iterator; (b) records
            past 255 sync the counter without being re-positioned.
