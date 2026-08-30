#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Hold off macOS idle sleep for the life of THIS process.

🔴 WHY THIS EXISTS, AND WHY IT IS AT A CHOKEPOINT RATHER THAN A CALL SITE.
On 2026-08-30 an overnight run was read as a busy host: `math-acceptance`
refusing in 4 s, `intarg-acceptance` in 0 s, emulators "stalling". It was
macOS idle sleep -- `pmset -g log` showed `Using BATT`, `DarkWake to FullWake
from Deep Idle` and 610 sleep/wakes since boot, with `PreventUserIdleSystemSleep`
held only by powerd *while the display is on*. A suspended process burns WALL
CLOCK without progress, which is exactly the signature the stall watchdog
reports -- and its own message says a host-clock deadline "CANNOT separate a
frozen emulator from one starved of CPU". Cost: two thrown-away batteries and
one CORRECT change withdrawn unshipped.
⚠️ THE TELL: refusals in 0-4 SECONDS are not contention. Contention makes work
SLOW; a 0-second refusal means it was never scheduled at all.

D-NOSLEEP put the assertion in `tools/run_gates.py`, which covered `make gates`
and NOTHING ELSE. Every ad-hoc probe and every knife runner -- which is most of
what an unattended session actually runs, and all of what it runs BEFORE the
battery -- stayed exposed. This module is that fix: it is imported by
`probes/lib/omsx_repl.py`, the one function every probe in the tree reaches the
emulator through, and it asserts AS A SIDE EFFECT OF IMPORT. Same reasoning as
`probe_tmp` establishing the temp root: one chokepoint beats 200 call sites that
each have to remember. [[apparatus-is-part-of-the-measurement]]

`caffeinate -i -w <pid>` asserts for exactly as long as that pid lives, so it is
released when this process exits HOWEVER it exits -- no atexit, no leak if we are
killed, and no way for it to outlive the run. Nothing to install: caffeinate
ships with macOS. Concurrent probes each hold their own; they are cheap and each
dies with its owner.

🟢 SILENT ON SUCCESS, LOUD ON FAILURE. Probe stdout is PARSED by knife runners,
several of which merge stderr into the same file, so a chatty success line is a
new way to break a reading. A failure prints once, because an exposed run that
says nothing is exactly the night this module exists to prevent.
"""
from __future__ import annotations

import os
import subprocess
import sys

HELD: bool | None = None      # None = not attempted yet
WHY: str = "not attempted"


def hold_awake():
    """-> (held, why). Spawns a caffeinate that dies with this process."""
    if sys.platform != "darwin":
        return False, "not macOS -- no idle-sleep hazard to hold off"
    try:
        subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as e:
        # Not fatal: a run without the assertion still RUNS, it is just exposed.
        # Say so rather than failing, and never say "held" when it is not.
        return False, f"🔴 caffeinate unavailable ({type(e).__name__}) -- "
    return True, "caffeinate -i held for this run"


def hold_once():
    """Idempotent per process. Safe to call from anywhere; never raises."""
    global HELD, WHY
    if HELD is not None:
        return HELD, WHY
    try:
        HELD, WHY = hold_awake()
    except Exception as e:                      # never break a probe over this
        HELD, WHY = False, f"🔴 hold_awake raised {type(e).__name__}"
    if not HELD and sys.platform == "darwin":
        print(f"⚠️  NOT holding off idle sleep: {WHY}\n"
              f"    A long run may be SUSPENDED, which reads as a stalled "
              f"emulator or a 0-second preflight refusal, not as sleep.",
              file=sys.stderr, flush=True)
    return HELD, WHY


def _selftest() -> int:
    """Collected by `make selftest-check` (tools/check_selftests.py scans
    probes/lib for scripts advertising "--selftest")."""
    ok = True

    def arm(name, cond):
        nonlocal ok
        print(f"{'PASS' if cond else '🔴 FAIL'}  {name}")
        ok = ok and bool(cond)

    held, why = hold_once()
    arm("S3 hold_once never claims 'held' without saying why", bool(why))
    if sys.platform == "darwin":
        a = subprocess.run(["pmset", "-g", "assertions"],
                           capture_output=True, text=True).stdout
        arm("S1 the assertion is ACTUALLY held, per pmset",
            held and "caffeinate" in a)
        # 🔴 It must die with US, not leak: a caffeinate bound to a dead pid
        # must not still be asserting.
        mine = subprocess.run(["pgrep", "-f", "caffeinate -i -w"],
                              capture_output=True, text=True).stdout.split()
        arm("S2 the assertion is bound to THIS pid, so it cannot outlive the run",
            any(str(os.getpid()) in
                subprocess.run(["ps", "-o", "args=", "-p", q],
                               capture_output=True, text=True).stdout
                for q in mine))
    else:
        arm("S1 off macOS this is a no-op and says so",
            not held and "macOS" in why)

    # 🎯 THE ARM THAT MATTERS, AND THE ONE A PRIVATE COPY COULD NOT HAVE HAD.
    # Holding the assertion is worthless if the CHOKEPOINT does not reach it, and
    # nothing else in the tree can see that wiring. Both halves are checked
    # because either alone is satisfiable without the other: an import with no
    # call holds nothing, and a call with no import cannot run.
    # [[a-knife-can-be-inert-because-the-build-did-not-happen]]
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "omsx_repl.py"), errors="replace").read()
    imports = "import probe_awake" in src
    calls = "probe_awake.hold_once()" in src
    arm("S4 omsx_repl -- the chokepoint every probe reaches -- IMPORTS this "
        "module", imports)
    arm("S5 ...and CALLS hold_once(); an import alone holds nothing", calls)

    print("selftest:", "GREEN" if ok else "🔴 RED")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    h, w = hold_once()
    print(f"held={h}  why={w}")
