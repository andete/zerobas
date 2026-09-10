#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-STALLRATE falsification — force a REAL stall kill, on an IDLE host.

TODO.md carried this arm as recorded-but-NOT-EXERCISED:

    "forcing a real kill with ZEROBAS_OMSX_STALL=2 did not kill, so nothing
     proves the READ happens at a real kill site -- only that the parse and the
     message are right. An arm that passes because it never fired is not an arm."

and the entry was ⛔ BLOCKED "needs an idle host".

\U0001f3af IT NEEDS A SIGNAL, NOT A BUSY HOST. `SIGSTOP` on the emulator stops
its event loop dead while leaving the process alive -- which is precisely the
state the watchdog exists to detect, and it is reproducible on a quiet machine
in seconds. Shortening `ZEROBAS_OMSX_STALL` alone never fired because a healthy
emulator keeps beating; nothing was ever stopped.

TWO ARMS, and they test different things on purpose:

  A1 INTEGRATION -- run a real case, SIGSTOP openMSX once beats are flowing, and
     read the kill message the watchdog actually produces. This is the arm that
     was missing: it proves the read happens AT A REAL KILL SITE.
     \U0001f534 And it makes a FALSIFIABLE prediction: the emulator was healthy
     right up to the signal, so the final beat interval must read HEALTHY. If a
     SIGSTOPped emulator reported "already crawling", the rate would be measuring
     the wrong window.

  A2 UNIT -- call `_why_missing` directly with a crawling rate and with no rate
     at all. This tests the RENDERING only, and says so: it cannot prove the
     measurement, which is exactly the gap A1 fills.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))

# \U0001f534 BEFORE THE IMPORTS, AND THAT IS THE WHOLE POINT. `probe_refcache`
# reads `ZEROBAS_REFCACHE` at MODULE level, so setting it inside the arm -- which
# is what attempt 3 did -- is too late: the cache stayed on, served the case from
# the store, and NO EMULATOR WAS EVER SPAWNED. The arm then reported "no stable
# openMSX process appeared", which reads exactly like the failure it is meant to
# detect. `omsx_repl` documents this hazard at the hit path (D-CACHEPRE: "a served
# hit returns before that", having silently disabled the preflight guard) -- the
# same trap, one arm along [[apparatus-is-part-of-the-measurement]].
os.environ["ZEROBAS_REFCACHE"] = "0"
os.environ["ZEROBAS_OMSX_STALL"] = "12"
os.environ["ZEROBAS_OMSX_ABSCAP"] = "1800"    # the run is long ON PURPOSE

import omsx_repl                                                  # noqa: E402
import probe_sides                                                # noqa: E402


def newest_emulator_pid() -> int | None:
    try:
        out = subprocess.run(["pgrep", "-n", "-f", "openmsx"],
                             capture_output=True, text=True).stdout.strip()
        return int(out.splitlines()[0]) if out else None
    except (ValueError, IndexError, OSError):
        return None


def a1_real_kill() -> bool:
    cfg = probe_sides.sides("zb")["zb"]
    result: dict[str, object] = {}

    def run():
        try:
            result["caps"] = omsx_repl.run_cases(
                cfg["machine"], [("direct", list(cfg["reset"]) + ['PRINT "X"'])],
                batch=False, reset=(), boot=cfg["boot"], step=4.0,
                # \U0001f534 `run_gap=20000` IS THE WHOLE TRICK, AND IT IS WHY
                # THE ORIGINAL ARM NEVER FIRED. openMSX here runs UNTHROTTLED at
                # roughly 400x, so an ordinary case lives **0.9 wall seconds** --
                # measured, along with 900 emulated seconds costing 2.1s and
                # 20000 costing 45.2s. There was never a process to stall, which
                # is why `ZEROBAS_OMSX_STALL=2` "did not kill": not a bug in the
                # watchdog, an emulator that had already exited. Wall life is
                # bought with EMULATED work, and 20000 emulated seconds buys the
                # ~45s this arm needs to hold ~15 beats plus the signal.
                run_gap=20000.0, cap_gap=4.0, timeout=900.0)
        except BaseException as exc:                     # noqa: BLE001
            result["exc"] = exc

    t = threading.Thread(target=run, daemon=True)
    t.start()
    # Let it boot and beat a few times: the rate we are about to assert on is
    # measured from the LAST TWO beats, so there have to be two.
    # \U0001f534 WAIT FOR A **STABLE** PID. The first attempt grabbed a pid,
    # slept 8s and then signalled -- and got `No such process`, because
    # `omsx_preflight` launches its own short-lived openMSX to validate the
    # machine before the real run. Signalling the newest match blind hits that
    # one. So: require the SAME pid to still be alive after the beats have had
    # time to flow, and start over if it is not.
    stopped = None
    deadline = time.time() + 120.0
    while time.time() < deadline and stopped is None:
        pid = newest_emulator_pid()
        if not pid:
            time.sleep(0.2)
            continue
        alive = True
        for _ in range(10):                  # ~10s: HB_WALL is 3s, so 3-4 beats
            time.sleep(1.0)
            try:
                os.kill(pid, 0)
            except OSError:
                alive = False
                break
        if not alive:
            continue                         # that was the preflight probe
        try:
            os.kill(pid, signal.SIGSTOP)
            stopped = pid
        except OSError as exc:
            print(f"  A1: pid {pid} went away before the signal ({exc}); retrying")
    if stopped is None:
        print(f"\U0001f534 A1: no STABLE openMSX process appeared inside the "
              f"window -- nothing was stopped, so this arm did NOT fire (the "
              f"failure the entry names). run finished={not t.is_alive()}")
        return False
    print(f"  A1: SIGSTOPped pid {stopped}; waiting for the stall watchdog...")
    t.join(timeout=180.0)
    try:
        os.kill(stopped, signal.SIGCONT)     # in case the kill did not land
    except OSError:
        pass
    if t.is_alive():
        print("\U0001f534 A1: the run never returned -- the watchdog did not fire")
        return False
    caps = result.get("caps")
    exc = result.get("exc")
    text = f"{exc}" if exc is not None else ""
    if caps is not None:
        text += " ".join(str(c) for c in caps if c)
    ok = True
    if "stall" not in text and "watchdog" not in text:
        print(f"\U0001f534 A1: no stall kill was reported. Got: {text[:300]!r}")
        ok = False
    if "final beat interval" not in text:
        print(f"\U0001f534 A1: the message carries NO rate field, so the read did "
              f"not happen at the kill site. Got: {text[:300]!r}")
        ok = False
    elif "HEALTHY and then stopped" not in text:
        print(f"\U0001f534 A1: a SIGSTOPped emulator was healthy until the signal, "
              f"so the final interval must read HEALTHY. Got: {text[:300]!r}")
        ok = False
    if ok:
        print("  A1 PASS: a real stall kill, and its message carries the final "
              "beat interval reading HEALTHY — the read fires at a real kill site.")
    return ok


def a2_rendering() -> bool:
    ok = True
    crawl = omsx_repl._why_missing("M", 0, 1, "stall", -9, 947.0, 88, "/nonexistent",
                                   hb_emu=12.4, hb_rate=0.013)
    if "ALREADY CRAWLING" not in crawl:
        print(f"\U0001f534 A2: a 0.013x final interval did not render STARVED: "
              f"{crawl[:200]!r}")
        ok = False
    boot = omsx_repl._why_missing("M", 0, 1, "stall", -9, 5.0, 0, "/nonexistent",
                                  hb_emu=None, hb_rate=None)
    if "killed during boot" not in boot:
        print(f"\U0001f534 A2: no rate at all did not render the boot case: "
              f"{boot[:200]!r}")
        ok = False
    if ok:
        print("  A2 PASS: 0.013x renders STARVED and no-rate renders the boot "
              "case (RENDERING only — A1 is what proves the measurement).")
    return ok


def main() -> int:
    print("D-STALLRATE falsification")
    a2 = a2_rendering()
    a1 = a1_real_kill()
    print(f"\n{'GREEN' if (a1 and a2) else '🔴 RED'}: A1 "
          f"{'PASS' if a1 else 'FAIL'}, A2 {'PASS' if a2 else 'FAIL'}")
    return 0 if (a1 and a2) else 1


if __name__ == "__main__":
    raise SystemExit(main())
