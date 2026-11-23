- [ ] 🧰 **D-KWTIMESYMRACE — `kwtime` CAN DIE IN 0 s ON `KeyError: 'tokenise'` WHEN ANOTHER BATTERY
      UNIT REWRITES main's .sym (found twice: 2026-10-04 during B-3, 2026-10-05 during B-11; MEASURED)**
      🎚️ TIER 6 — apparatus: the runner's serial retry turns it green both
      times, but a flake that hides behind a retry is one a real red can hide
      behind too.
      🔬 `basic_probe_kwtime.py` imports `basic_probe_kwsweep`, whose MODULE
      LEVEL builds `TAPE_PROGRAM` through `bas_tokenise.make_multiline_program`,
      which loads the main ROM's .sym and calls `tokenise` on the host core. If
      a concurrent unit is mid-rewrite of that .sym, the lookup misses and the
      import dies (the battery's own kwtime log showed this traceback both times).
      ➡️ Build `TAPE_PROGRAM` lazily (on first use, not at import), or have
      kwtime read a snapshot of the .sym taken at the warm-up. Then put kwtime
      back in the pool without the retry hiding it.
      🔁 **A THIRD TIME, 2026-10-10, AND IN `kwsweep` ITSELF** (D-HOOKDI's FULL
      battery; that run's kwsweep log, overwritten since): its own
      module-level `TAPE_PROGRAM2` died at import the same way, and the serial
      retry turned it green. Not only kwtime's import of it — any unit that
      builds a program at import time can lose this race.
      🤖 **AUTONOMOUS** — apparatus.
