- [ ] 📌 **ANY BATTERY OR KNIFE SCORE TAKEN 2026-08-30 EVENING .. 2026-08-31
      04:30 IS SUSPECT — THE HOST WAS ASLEEP UNDER IT.** Found 2026-08-31 by
      D-NOSLEEP2, [`docs/spec-nosleep2.md`](../../docs/spec-nosleep2.md).
      `caffeinate -i` asserts `PreventUserIdleSystemSleep` and does NOT block
      macOS's scheduled **'Maintenance Sleep'**, which fired on AC power at 100%
      charge: 15 minutes asleep, 45 seconds awake, repeatedly. A battery walled
      at **3861 s against 471 s** for the same ROM hashes, and
      `graphics-acceptance` reported a **977 s** stall against a **979 s** sleep.
      ✅ **FIXED**: `caffeinate -i -s -w <pid>`, at the `omsx_repl` chokepoint, so
      every probe and knife runner holds it.
      🔴 **AND THE OLD ARM PASSED ALL NIGHT** — `S1` asked whether *an* assertion
      was held and one always was, the idle one. New `S6` names
      `PreventSystemSleep`; re-planting the old flags makes S6 red while S1 stays
      green.
      ✅ **RE-VERIFIED 2026-08-31 ON AN AWAKE MACHINE**: the D-NGRAM14 arms
      re-run identically (S1 green, K-N14A moves exactly `r.atn r.round2 x.m100
      x.p100`), and D-CLOSALIAS's red/green plant was taken after the fix. The
      D-NGRAM12/13, D-TRUNCLOAD and D-DEADBODY batteries all walled at 449-476 s,
      which is the AWAKE wall -- a slept-through run walls at 3861 s, so the wall
      itself dates them outside the window.
      ➡️ **STILL OWED:** re-run anything ELSE scored in that window before
      building on it. **The wall time is the cheap discriminator.**
      🎚️ APPARATUS — battery-score validity window
      🤖 AUTONOMOUS — a re-run settles each one.
