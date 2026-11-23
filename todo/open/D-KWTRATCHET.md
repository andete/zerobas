- [ ] 🔴 **A kwtime ROW THAT REGRESSES FROM OK TO SLOW OR HANG FAILS NO GATE
      (D-KWTRATCHET, found 2026-09-28 while fixing D-DSKFSLOW).**
      🎚️ APPARATUS — the T2 rung (reasonable time) has no regression guard per ROW.
      🤖 **AUTONOMOUS** — design is the whole item.
      📏 `make kwtime` exits 0 on SLOW/HANG by design ("findings, reported, not gate
      failures"), and its pin is `build/kwtime.json` — an untracked build artifact, so
      a fresh clone has nothing to compare against. The tracked record,
      `docs/tier-status.md`, is PER KEYWORD: DSKF kept its T2 through D-DSKFSLOW
      because each form had another OK row, so reverting that fix would change no
      tracked byte and redden nothing. A ratchet wants a TRACKED per-row baseline
      (the OK set) and a failure when a baseline-OK row reads SLOW/HANG.
      ⚖️ **FLAKE RISK MEASURED LOW:** of 825 OK rows only 2 sit above 6× — `sqr`
      8.25×, `resumekw_b` 6.76× (build/kwtime.json, 2026-09-28) — so a 10× ratchet
      would rarely trip on noise; D-RUNT5NOISE's flip was a T5 ratio, not T2.
