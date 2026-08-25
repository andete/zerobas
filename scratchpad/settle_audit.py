#!/usr/bin/env python3
"""CORRECTNESS AUDIT: is any gate case captured while it is STILL CHANGING?

Correctness first, speed second. The emulated-time budgets are guesses at the
completion time (docs/spec-probe-budget.md), and a guess that is too SHORT does
not raise -- it captures a half-finished machine, and a partial result reads as
SEMANTICS. So before any budget is cut or any sentinel replaces one, ask the
opposite question: **does any case ALREADY get captured mid-work today?**

This wraps `omsx_repl._run_batch` so every case a real probe runs is sampled by
the settle instrument -- no probe edits, no case list to maintain, and therefore
no denominator of my own invention: the corpus is whatever the probe drives.

A case is RED when its capture region still differs between the last two samples
(`still_moving`) -- the region was in motion when the capture fired.
A case is AMBER when it settles in the last 10% of its window: no margin left.

⚠️ Sampling is log-spaced, so the last two samples are the FINEST-grained pair in
the window -- the most sensitive place to ask "was it still moving?".

Usage:  python3 scratchpad/settle_audit.py <probe-module> [probe args...]
   e.g. python3 scratchpad/settle_audit.py basic_probe_graphics
        python3 scratchpad/settle_audit.py circmiss_probe
"""
from __future__ import annotations

import importlib
import os
import sys

ROOT = "/Users/joost/projects/zerobas"
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
sys.path.insert(0, os.path.join(ROOT, "scratchpad"))
import omsx_repl                                                   # noqa: E402

N = 24                       # samples per window; log-spaced
FINDINGS: list[dict] = []
_orig = omsx_repl._run_batch
_seq = [0]


def _wrapped(machine, cases, **kw):
    """Force the settle instrument on for every case the probe runs."""
    if kw.get("settle_n"):                       # already instrumented; leave it
        return _orig(machine, cases, **kw)
    so: dict = {}
    kw["settle_n"] = N
    kw["settle_out"] = so
    res = _orig(machine, cases, **kw)
    for idx, samples in sorted(so.get("samples", {}).items()):
        span = so.get("span", {}).get(idx)
        if not span or len(samples) < 2:
            continue
        t_run, t_cap = span
        window = t_cap - t_run
        moving = samples[-1][1] != samples[-2][1]
        last_change = None
        for i in range(1, len(samples)):
            if samples[i][1] != samples[i - 1][1]:
                last_change = samples[i][0]
        settled = last_change if last_change is not None else samples[0][0]
        used = settled - t_run
        _seq[0] += 1
        rec = dict(n=_seq[0], machine=machine, window=window, used=used,
                   moving=moving, frac=used / window if window else 0.0,
                   body=cases[idx][1] if idx < len(cases) else None)
        FINDINGS.append(rec)
        if moving:
            print(f"🔴 STILL MOVING AT CAPTURE  {machine}  window={window:.2f}s "
                  f"used>={used:.2f}s  body={rec['body']}", flush=True)
    return res


omsx_repl._run_batch = _wrapped


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    mod_name = sys.argv[1]
    sys.argv = [mod_name] + sys.argv[2:]
    mod = importlib.import_module(mod_name)
    rc = 0
    try:
        if hasattr(mod, "main"):
            rc = mod.main() or 0
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else 0
    red = [f for f in FINDINGS if f["moving"]]
    amber = [f for f in FINDINGS if not f["moving"] and f["frac"] > 0.90]
    print(f"\n=== SETTLE AUDIT: {len(FINDINGS)} cases sampled ===")
    print(f"  🔴 still moving at capture : {len(red)}")
    print(f"  🟠 settled in the last 10% : {len(amber)}")
    if red:
        print("\n  A case captured mid-work produces a PARTIAL result, which "
              "reads as semantics.\n  These are correctness findings, not "
              "performance ones:")
        for f in red[:20]:
            print(f"    {f['machine']:<28} window={f['window']:7.2f}s  "
                  f"body={f['body']}")
    for f in amber[:10]:
        print(f"  🟠 {f['machine']:<28} used {f['used']:.2f}/{f['window']:.2f}s "
              f"({100*f['frac']:.0f}%)  body={f['body']}")
    if FINDINGS:
        worst = max(FINDINGS, key=lambda f: f["frac"])
        print(f"\n  tightest margin seen: {100*worst['frac']:.1f}% of its window "
              f"({worst['used']:.2f}/{worst['window']:.2f}s) on {worst['machine']}")
    print(f"  probe's own exit code: {rc}")
    return 1 if red else 0


if __name__ == "__main__":
    raise SystemExit(main())
