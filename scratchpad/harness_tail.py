#!/usr/bin/env python3
"""MINIMAL REPRODUCER for the harness's wall-time TAIL, with the phases split.

graphics-acceptance: 20 of 463 openMSX invocations = 48% of all wall, each ~5.8 s
whether its schedule is 20.5 or 73 emulated seconds. Constant cost independent of
emulated time means the stall is OUTSIDE the emulation -- so neither a shorter
budget nor a sentinel can reach it. This runs ONE trivial case many times and
times the three phases separately, so the answer is a phase, not a guess:

    preflight  -- omsx_preflight.guarded(cmd), which runs per launch
    spawn      -- Popen returning
    run        -- the poll loop until openMSX exits
    parse      -- reading the capture file back

⚠️ Deliberately NOT a probe: if the tail reproduces on a fixed 3-line case, it is
the harness, and nothing about any test's content matters.
"""
from __future__ import annotations
import os, statistics, subprocess, sys, time

ROOT = "/Users/joost/projects/zerobas"
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, omsx_preflight                                   # noqa: E402

N = int(os.environ.get("N", "60"))
MACHINE = os.environ.get("M", "C-BIOS_MSX1_EU_REPACK_DISK")
PH: list[dict] = []

_pre, _pop = omsx_preflight.guarded, subprocess.Popen


def pre_spy(cmd):
    t = time.monotonic()
    r = _pre(cmd)
    PH[-1]["preflight"] = time.monotonic() - t
    return r


def pop_spy(*a, **kw):
    t = time.monotonic()
    p = _pop(*a, **kw)
    PH[-1]["spawn"] = time.monotonic() - t
    PH[-1]["_t_after_spawn"] = time.monotonic()
    PH[-1]["pid"] = p.pid
    import threading

    def watch(pid, rec):
        # sample only if this invocation is already abnormal
        time.sleep(1.0)
        if rec.get("wall") is not None:
            return
        for _ in range(6):
            try:
                o = subprocess.run(["ps", "-o", "%cpu=,state=,wq=", "-p", str(pid)],
                                   capture_output=True, text=True, timeout=2).stdout.strip()
            except Exception:
                o = "?"
            if not o:
                return
            rec.setdefault("samples", []).append(o)
            # what else is hot right now
            try:
                top = subprocess.run(["ps", "-Ao", "%cpu=,comm=", "-r"],
                                     capture_output=True, text=True, timeout=3).stdout
                rec.setdefault("hot", []).append(
                    [l.strip() for l in top.splitlines()[:4]])
            except Exception:
                pass
            time.sleep(0.7)

    threading.Thread(target=watch, args=(p.pid, PH[-1]), daemon=True).start()
    return p


omsx_preflight.guarded = pre_spy
subprocess.Popen = pop_spy
omsx_repl.omsx_preflight.guarded = pre_spy
omsx_repl.subprocess.Popen = pop_spy

NC = int(os.environ.get("NC", "1"))
CASE = [("stored", ['PRINT"HI"'])] * NC


def main():
    print(f"{N} identical invocations, {NC} case(s) each, on {MACHINE}\n")
    for i in range(N):
        PH.append(dict(n=i, preflight=0.0, spawn=0.0))
        t0 = time.monotonic()
        omsx_repl.run_batch(MACHINE, CASE, reset=(), boot=8.0, step=2.5,
                            cap_gap=2.5, timeout=120.0, verify_delivery=False)
        PH[-1]["wall"] = time.monotonic() - t0
        PH[-1]["after_spawn"] = time.monotonic() - PH[-1].pop("_t_after_spawn", time.monotonic())
    w = sorted(p["wall"] for p in PH)
    tot = sum(w)
    print(f"wall: median {statistics.median(w):.3f}s  mean {tot/N:.3f}s  "
          f"min {w[0]:.3f}s  max {w[-1]:.3f}s")
    k = max(1, N // 10)
    print(f"slowest {k} = {100*sum(w[-k:])/tot:.0f}% of total\n")
    thr = 3 * statistics.median(w)
    pos = [p["n"] for p in PH if p["wall"] > thr]
    print(f"  stalls (>3x median): {len(pos)} at {pos[:14]}")
    if len(pos) > 1:
        d = [b - a for a, b in zip(pos, pos[1:])]
        print(f"  deltas in COUNT: {d[:12]}  median {statistics.median(d):.1f}")
        print(f"  => one stall per {statistics.median(d)*statistics.median(w):.1f}s "
              f"of non-stall wall")
    slow = sorted(PH, key=lambda p: -p["wall"])[:5]
    fast = sorted(PH, key=lambda p: p["wall"])[:5]
    for name, grp in (("SLOWEST 5", slow), ("FASTEST 5", fast)):
        print(f"  {name}")
        for p in grp:
            print(f"    #{p['n']:<3} wall {p['wall']:6.3f}s = preflight "
                  f"{p['preflight']:.3f} + spawn {p['spawn']:.3f} + "
                  f"after-spawn {p['after_spawn']:.3f}")
    print("\n  WHAT THE EMULATOR WAS DOING DURING A STALL (%cpu, state):")
    for p in sorted(PH, key=lambda p: -p["wall"])[:3]:
        if p.get("samples"):
            print(f"    #{p['n']} wall {p['wall']:.2f}s  omsx: {p['samples']}")
            for h in (p.get("hot") or [])[:2]:
                print(f"       hottest: {h}")
    print(f"\n  median preflight {statistics.median(p['preflight'] for p in PH):.3f}s"
          f"  median spawn {statistics.median(p['spawn'] for p in PH):.3f}s"
          f"  median after-spawn {statistics.median(p['after_spawn'] for p in PH):.3f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
