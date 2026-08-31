# D-NOSLEEP2 — `caffeinate -i` does not stop macOS Maintenance Sleep

*2026-08-31. `probes/lib/probe_awake.py`, `tools/run_gates.py`. No ROM change.*

## 1. What it cost before it was found

Four hours of batteries, all of them read and none of them worth reading:

| run | wall | verdict |
|---|---|---|
| clean, evening | **471 s** | 48/48 green |
| same ROM hashes, night | **3861 s** | 46/48, `graphics-acceptance` `REAL (still red)` |
| `graphics-acceptance` alone | — | `25 of 25 captures MISSING`, stalled **109 s** |
| `graphics-acceptance` alone, again | — | different phase, different machine, stalled **977 s** |
| `lineerr-acceptance` alone | — | stalled **1053 s**, then **561 s** |

The stall moved between phases and between machines on each run, including onto
the **VG-8020** — a stock reference machine no zerobas change can touch.

## 2. `pmset -g log` names it exactly

```
03:51:15  Entering Sleep state due to 'Maintenance Sleep' ...  939 secs
04:06:54  DarkWake from Deep Idle ...                           45 secs
04:07:39  Entering Sleep state due to 'Sleep Service Back to Sleep' ...  979 secs
04:23:58  DarkWake from Deep Idle ...                           44 secs
```

Fifteen minutes asleep, forty-five seconds awake, on **AC power at 100%
charge**. `graphics-acceptance` reported a **977 s** stall against that **979 s**
sleep — the same window, near enough to the second.

A suspended process burns wall clock without progress, which is precisely what
the stall watchdog reports, and its own message says so: *"a host-clock deadline
CANNOT separate a frozen emulator from one starved of CPU"*.

## 3. 🔴 The assertion was held the whole time — the wrong one

`probe_awake` spawned `caffeinate -i -w <pid>`. That asserts
`PreventUserIdleSystemSleep`: it blocks the sleep that follows *inactivity*. It
does **not** block macOS's scheduled Maintenance Sleep / Sleep Service cycle.

`-s` (prevent **system** sleep) is the assertion that covers it. macOS ignores
`-s` on battery, so it needs no power-source test.

## 4. 🔴 And the arm certified the exposure

`S1` asked *"is the assertion ACTUALLY held, per pmset?"* — and it passed, every
time, all night. One assertion **was** held. It was the wrong one, and the arm
never named which it wanted.

**An arm that checks the wrong assertion is worse than no arm: it converts an
exposure into a certification.** `S6` names it:

| flags | S1 | S6 |
|---|---|---|
| `caffeinate -i -w` (before) | 🟢 PASS | 🔴 **FAIL** |
| `caffeinate -i -s -w` (now) | 🟢 PASS | 🟢 PASS |

That is a real red arm with a green control on the same apparatus — the old
behaviour is re-plantable in one `sed`, and it fails on the named assertion
while still passing the vague one.

🟢 Verified live as well as in the selftest: polling `pmset` through an actual
uncached probe run, `PreventSystemSleep` is held for the run's duration and
released when it exits.

## 5. 🔴 A measurement mistake of my own, on the way

I first sampled `pmset` **25 seconds after launching a probe** and found no
assertion and no `caffeinate`, and wrote down *"confirmed: nothing holds the
machine awake"*. The probe had already finished — the harness batches all rows
into one emulator run, and with a warm refcache it exits in seconds.

**A sample taken after the subject exits measures the absence of the subject.**
Continuous polling for the run's lifetime is what actually answers it; the
corrected reading found `caffeinate` in 10 of 65 samples and the idle assertion
in 22 of 65, which is what sent me looking at *which* assertion rather than
whether there was one.

## 6. What is now protected

`probe_awake` is imported by `probes/lib/omsx_repl.py` — the chokepoint every
probe in the tree reaches the emulator through — so every probe, knife runner and
ad-hoc run holds `-i -s` for exactly as long as its own process lives.
`tools/run_gates.py`'s own leak arm was re-pinned to the new flag string.

⚠️ **Any battery, knife score or "REAL vs FLAKE" verdict taken between 2026-08-30
evening and this fix should be re-run before it is believed.**
