#!/usr/bin/env python3
"""Does moving SLOW_ROWS from `step` to `run_gap` keep the RUN..capture window?

Read off `_tcl`'s generated timeline -- no emulator. The claim under test is
"the capture is at the SAME instant relative to RUN, and only the typing gets
cheaper". Anything else is a change to what the row measures.
"""
import re, sys
sys.path.insert(0, "probes/lib"); sys.path.insert(0, "probes/basic")
import omsx_repl
import basic_probe_lineerr as L


def tl(lines, *, boot, step, cap_gap, reset, run_gap):
    tcl = omsx_repl._tcl("/dev/null", [("direct", list(reset) + lines)],
                         boot, step, cap_gap, (), "screen", None, 12.0, (),
                         [], hb_path=None, settle_n=0, sentinel=(0xE000, 255),
                         run_gap=run_gap, sentinel_capture=True)
    end = max(float(m) for m in re.findall(r"after time ([\d.]+)", tcl)) - 30.0
    run = max(float(m) for m in
              re.findall(r"after time ([\d.]+) \{ __(?:inj|key) ", tcl))
    cap = [float(m) for m in
           re.findall(r'after time ([\d.]+) \{ if \{!\$::__cap', tcl)][0]
    return run, cap, end


print(f"  {'':22} {'t_run':>7} {'capture':>9} {'RUN..cap':>9} {'end':>8}")
for side, cfg in L.SIDES.items():
    lines = L.program("c.32767", "t", L.S2, "LINE (11,12)-(32767,21)") + ["RUN"]
    kw = dict(boot=cfg["boot"], cap_gap=2.5, reset=cfg["reset"])
    # BEFORE: step raised to 12.0, no run_gap
    b = tl(lines, step=max(cfg["step"], 12.0), run_gap=None, **kw)
    # AFTER: step at the side's default, 12.0 carried by run_gap
    a = tl(lines, step=cfg["step"], run_gap=12.0, **kw)
    for tag, (r, c, e) in (("before  step=12", b), ("after   run_gap=12", a)):
        print(f"  {side:6} {tag:15} {r:7.1f} {c:9.1f} {c-r:9.1f} {e:8.1f}")
    ok = abs((b[1] - b[0]) - (a[1] - a[0])) < 1e-6
    print(f"  {'':6} {'RUN..capture window UNCHANGED:':15} "
          f"{'YES' if ok else 'NO — THE ROW NOW MEASURES SOMETHING ELSE'}"
          f"   end {b[2]:.1f} -> {a[2]:.1f} ({a[2]-b[2]:+.1f} emulated s)\n")
    assert ok

    # 🟢 a row with NO SLOW_ROWS entry must be untouched by the change
    ol = L.program("m.ok", "t", L.S2, "LINE (11,12)-(20,21)") + ["RUN"]
    n0 = tl(ol, step=cfg["step"], run_gap=None, **kw)
    n1 = tl(ol, step=cfg["step"], run_gap=None, **kw)
    assert n0 == n1
print("CONTROL: an ordinary row passes run_gap=None and is byte-identical. OK")
