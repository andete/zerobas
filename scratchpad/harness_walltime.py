#!/usr/bin/env python3
"""WHERE DOES THE HARNESS'S WALL TIME ACTUALLY GO?

🔴 Written because the last two attempts to speed something up here were both
justified by a MODEL and both models were wrong: "the per-case boot dominates"
(refuted, the boot is ~0.7 s) and "PAINT is VDP-access-bound" (refuted, removing
85% of the accesses bought 12%). So this measures instead of modelling.

Every probe reaches openMSX through `omsx_repl._run_batch`: one process, one
boot, a scheduled EMULATED timeline, one exit. Wall time per invocation is then

    wall  =  fixed overhead (spawn + boot + teardown)  +  k x emulated seconds

and which term dominates decides whether the SENTINEL can help at all. The
sentinel collapses `run_gap` + `cap_gap` to the case's own completion, so it can
only ever attack the SECOND term.

This wraps _run_batch, times each invocation, and records the case shape that
produced it -- no probe edits, and the corpus is whatever the probe drives.

    python3 scratchpad/harness_walltime.py <probe-module> [args...]
"""
from __future__ import annotations
import importlib, os, re, statistics, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
sys.path.insert(0, os.path.join(ROOT, "scratchpad"))
import omsx_repl                                                   # noqa: E402

REC: list[dict] = []
_orig = omsx_repl._run_batch
_orig_tcl = omsx_repl._tcl
_last_sched = [0.0]


def _tcl_spy(*a, **kw):
    """🔴 THE SCHEDULE MUST COME FROM THE HARNESS, NOT FROM A FORMULA I WROTE.
    Draft 1 estimated the emulated timeline as `boot + lines*step +
    ncases*(gap+cap)` and concluded that invocations of IDENTICAL emulated
    length differed 36x in wall -- an alarming 'heavy tail'. But a case may
    contain `@WAIT` pseudo-lines and `holds`, and a wait ADVANCES the schedule by
    its own length (see _tcl's own `last_inj` comment), so the formula
    under-counted exactly those cases. The real end of the timeline is the
    emulated instant of the generated `exit`."""
    out = _orig_tcl(*a, **kw)
    ends = re.findall(r"after time ([\d.]+) \{ close \$__f; exit \}", out)
    _last_sched[0] = float(ends[-1]) if ends else 0.0
    return out


omsx_repl._tcl = _tcl_spy


def _wrapped(machine, cases, **kw):
    step = kw.get("step", 2.5)
    gap = kw.get("run_gap")
    gap = step if gap is None else gap
    cap = kw.get("cap_gap", 2.5)
    boot = kw.get("boot", 8.0)
    # the emulated timeline the harness SCHEDULES: boot, then per case the typed
    # lines at `step` apart, then the RUN->capture budget, then cap_gap.
    lines = sum(len(c[1]) for c in cases)
    emu = boot + lines * step + len(cases) * (gap + cap)
    _last_sched[0] = 0.0
    t0 = time.monotonic()
    try:
        return _orig(machine, cases, **kw)
    finally:
        REC.append(dict(n=len(REC), wall=time.monotonic() - t0, machine=machine,
                        ncases=len(cases), nlines=lines, step=step, gap=gap,
                        cap=cap, boot=boot, emu_formula=emu,
                        emu=_last_sched[0],          # the REAL scheduled end
                        diska=bool(kw.get("diska")), cart=bool(kw.get("cart"))))


omsx_repl._run_batch = _wrapped


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    mod_name = sys.argv[1]
    sys.argv = [mod_name] + sys.argv[2:]
    t0 = time.monotonic()
    try:
        mod = importlib.import_module(mod_name)
        rc = (mod.main() or 0) if hasattr(mod, "main") else 0
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else 0
    total = time.monotonic() - t0

    wall = sum(r["wall"] for r in REC)
    emu = sum(r["emu"] for r in REC)
    print(f"\n=== HARNESS WALL-TIME ATTRIBUTION: {len(REC)} openMSX invocations ===")
    print(f"  probe wall total      : {total:8.1f} s   (exit code {rc})")
    print(f"  inside _run_batch     : {wall:8.1f} s   ({100*wall/total:.0f}% of it)")
    print(f"  emulated s scheduled  : {emu:8.1f} s")
    if emu:
        print(f"  wall per emulated s   : {wall/emu:8.4f} s")

    import json
    with open(os.path.join(ROOT, "scratchpad", "hw_records.json"), "w") as fh:
        json.dump(REC, fh)
    print(f"  raw records -> scratchpad/hw_records.json ({len(REC)} rows)")

    # 🔴 A TWO-POINT MEDIAN FIT CANNOT SEE A HEAVY TAIL, and the first run of this
    # instrument printed one that its own top-10 list contradicted: invocations
    # with IDENTICAL emulated time (20.5 s) cost 0.16 s and 5.80 s. Report the
    # distribution, not a slope.
    ws = sorted(r["wall"] for r in REC)
    tot = sum(ws)
    print(f"  wall: median {statistics.median(ws):.3f}s  mean {tot/len(ws):.3f}s  "
          f"max {ws[-1]:.2f}s")
    for frac in (0.01, 0.05, 0.10, 0.25):
        k = max(1, int(len(ws) * frac))
        print(f"    slowest {100*frac:>4.0f}% ({k:>3} invocations) = "
              f"{100*sum(ws[-k:])/tot:5.1f}% of all _run_batch wall")

    # Split the invocations by how much EMULATED time they buy. If the fixed
    # overhead dominates, cheap and expensive invocations cost about the same
    # wall; if the budgets dominate, wall tracks `emu`.
    REC.sort(key=lambda r: r["emu"])
    n = len(REC)
    lo, hi = REC[:max(1, n // 4)], REC[-max(1, n // 4):]
    for name, grp in (("cheapest quartile", lo), ("dearest quartile", hi)):
        w = statistics.median(r["wall"] for r in grp)
        e = statistics.median(r["emu"] for r in grp)
        print(f"  {name:<20}: median emu {e:8.1f} s -> median wall {w:6.2f} s")
    # the fixed cost, read off the cheapest invocations rather than assumed
    base = statistics.median(r["wall"] for r in lo)
    basee = statistics.median(r["emu"] for r in lo)
    dw = statistics.median(r["wall"] for r in hi) - base
    de = statistics.median(r["emu"] for r in hi) - basee
    if de > 0:
        k = dw / de
        fixed = base - k * basee
        print(f"\n  FIT from those two points: wall ~= {fixed:.2f} s fixed "
              f"+ {k:.4f} s per emulated s")
        print(f"  => fixed overhead is {100*fixed*len(REC)/wall:.0f}% of all "
              f"_run_batch wall; emulated time is {100-100*fixed*len(REC)/wall:.0f}%")
        print(f"  🎯 A SENTINEL CAN ONLY ATTACK THE SECOND TERM.")
    print("\n  top 10 invocations by wall:")
    for r in sorted(REC, key=lambda r: -r["wall"])[:10]:
        print(f"    {r['wall']:6.2f}s  emu={r['emu']:7.1f}s  "
              f"cases={r['ncases']:<3} lines={r['nlines']:<3} "
              f"step={r['step']:<5} gap={r['gap']:<5} cap={r['cap']:<4} "
              f"{r['machine'][:22]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
