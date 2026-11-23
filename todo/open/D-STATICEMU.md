- [ ] 🔧 **D-STATICEMU — THE "STATIC" GATE TIER BOOTS EMULATORS: `kwsweep`, `kwtime` AND `kwram` SIT IN
      `tools/run_gates.py`'s STATIC LIST AND COST ~26 OF ITS ~27 MINUTES (found 2026-10-07)**
      🎚️ APPARATUS — a gate tier whose cost contradicts its own definition.
      📏 The STATIC list's own header says a STATIC unit "reads tracked FILES; an
      EMULATOR unit boots a machine", yet the list carries the three keyword
      sweeps, which boot the references and ours for every row (kwsweep 482 s,
      kwtime 1087 s in a run the same day). A LICENSE + README commit (32d38e6d)
      sat 25 minutes in it before Joost asked why; its 44 file-reading units ran
      in 168 s.
      ➡️ Find WHY they were put there (most likely: `tiers-md-check`, the
      post-check, needs a CURRENT kwsweep pin, and a STATIC-only run would
      otherwise compare against a stale or missing one -- 32d38e6d met exactly
      that: no pin in build/). Then move them to the EMULATOR tier and give the
      STATIC tier a pin rule that does not need an emulator: skip
      `tiers-md-check` with a stated reason when neither TODO.md nor
      tier-status.md changed, or refuse loudly when the pin is absent. A
      selftest arm: a docs-only plan must not schedule an emulator unit.
      🤖 **AUTONOMOUS** — a tool change, the gate's own selftest settles it.
      ✅ **FIXED 2026-10-08 -- gates-fast 127 s, was ~55 min.** The cause was as
      guessed: 2183bed9 put the sweeps in STATIC so the post-check
      `tiers-md-check` always had a FRESH pin, because `run_gates.py`'s `main()`
      wipes `build/`. Now:
      - `kwsweep` / `kwtime` / `kwram` are EMULATOR units (`SWEEPS`);
      - a run that leaves them out keeps the PREVIOUS run's pins across the wipe
        (`SWEEP_PINS`, read into memory first) and SAYS so; with no pin on record
        it does not run `tiers-md-check` and says that;
      - `tools/pick_gates.py` puts the three in `CANARY`, so every ROM-changing
        SCOPED plan still runs the keyword net (FULL runs everything anyway).
      Selftest arms: no sweep in STATIC (+ a non-vacuity NEGATIVE), a
      handler-local ROM change schedules all three, a docs-only plan schedules no
      emulator unit, a probe-only change does not drag them in. 📏 `make
      gates-fast`: **127 s wall, 45/45 green**, the pin note printed
      ([`staticemu_fast.out`](scratchpad/staticemu_fast.out)); the day's runs before
      it took 3300-3600 s. 🔮 Predicted 3-5 min: HIT.
      ⚠️ The loop's `make tiers-md` after gates-fast now renders from the LAST
      FULL's pin, not a fresh one; the next FULL re-checks the sheet against a
      fresh pin, and a keyword verdict a ROM change moved shows up there.
      🔴 **AND IT DID, ON THE VERY NEXT ROM COMMIT (D-PUTDIR, 2026-10-08):** FULL
      went 169/170, `tiers-md-check` red on two evidence cells the new ROM moved
      (DSKI$ T5 0.14 -> 0.13, RSET T4 0.26 -> 0.45). Before this change gates-fast
      measured the NEW ROM, so `make tiers-md` and FULL always agreed. ➡️ **LOOP
      RULE until D-PINSTALE lands: a ROM-changing commit runs `make kwsweep kwtime
      kwram` (with the knife pin) BEFORE `make tiers-md`;** a docs / probe commit
      does not need to. (~~LOOP RULE~~ RETIRED 2026-10-09: D-PINSTALE makes
      gates-fast run them itself when the ROM moved.) That commit's sheet was re-rendered from FULL's fresh pins
      (same ROM) and `tiers-md-check` re-run green alone.
