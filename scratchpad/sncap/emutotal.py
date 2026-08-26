#!/usr/bin/env python3
"""The WHOLE converted matrix, in emulated seconds -- computed, not timed.

Same source as emutime.py: `omsx_repl._tcl` generates the timeline from the
case's own lines, deterministically, with no emulator. Sums the per-case
schedule over every row x every side so the gate-level figure is arithmetic
rather than a wall reading taken on a contended host.
"""
import re, sys
sys.path.insert(0, "probes/lib"); sys.path.insert(0, "probes/basic")
import omsx_repl, probe_signal


def sched(lines, *, boot, step, cap_gap, reset, run_gap=None):
    slots = []
    tcl = omsx_repl._tcl("/dev/null", [("direct", list(reset) + lines)],
                         boot, step, cap_gap, (), "screen", None, 12.0, (),
                         slots, hb_path=None, settle_n=0,
                         sentinel=(0xE000, 255), run_gap=run_gap,
                         sentinel_capture=True)
    end = max(float(m) for m in re.findall(r"after time ([\d.]+)", tcl)) - 30.0
    run = max(float(m) for m in
              re.findall(r"after time ([\d.]+) \{ __(?:inj|key) ", tcl))
    return end, run


def total(name, rows):
    """rows: iterable of (before_lines, after_lines_or_None, kw)"""
    tb = ta = 0.0
    marked = unmarked = 0
    for before, after, kw in rows:
        eb, _ = sched(before, **kw)
        tb += eb
        if after is None:                      # not converted: unchanged
            ta += eb
            unmarked += 1
        else:
            _, ra = sched(after, **kw)
            ta += ra                           # exits at t_run + delta (~0.2 s)
            marked += 1
    print(f"{name:<12} {marked:4d} marked + {unmarked:3d} not   "
          f"{tb:8.0f} -> {ta:8.0f} emulated s   "
          f"({ta-tb:+7.0f}, {100*(ta-tb)/tb:+5.1f}%)   "
          f"~{0.003*(tb-ta):5.1f} s wall at the spec's 0.003 s/emulated s")
    return tb, ta


import basic_probe_penderr as P, basic_probe_screenerr as S
import basic_probe_stmtpend as T, basic_probe_tmfp as M
import basic_probe_lineerr as L, basic_probe_deffn as D

GB = GA = 0.0
for mod, nm in ((P, "penderr"), (S, "screenerr"), (T, "stmtpend"), (M, "tmfp")):
    rows = []
    for side, cfg in mod.SIDES.items():
        for label, kind, stmt in mod.CASES:
            tpl = (mod.TEMPLATES[kind] if nm == "stmtpend"
                   else (mod.TRAP_PROG if kind == "t" else mod.UNTRAP_PROG))
            raw = [ln.format(stmt=stmt) for ln in tpl] + ["RUN"]
            new = (mod.program(kind, stmt) + ["RUN"]) if kind == "t" else None
            rows.append((raw, new, dict(boot=cfg["boot"], step=cfg["step"],
                                        cap_gap=2.5, reset=cfg["reset"])))
    b, a = total(nm, rows); GB += b; GA += a

rows = []
for side, cfg in L.SIDES.items():
    for label, kind, seed, stmt in L.CASES:
        rd = L.GXPOS_RD if label in L.GXPOS_ROWS else L.GRPAC_RD
        tpl = L.TRAP_PROG if kind == "t" else L.UNTRAP_PROG
        raw = [ln.format(stmt=stmt, seed=seed, **rd) for ln in tpl] + ["RUN"]
        new = (L.program(label, kind, seed, stmt) + ["RUN"]) if kind == "t" else None
        # BEFORE this file was written the budget rode on `step`; it now rides
        # on `run_gap`, so the two configurations differ in the kwargs too.
        rows.append((raw, new, dict(boot=cfg["boot"], step=cfg["step"],
                                    cap_gap=2.5, reset=cfg["reset"],
                                    run_gap=L.SLOW_ROWS.get(label))))
b, a = total("lineerr", rows); GB += b; GA += a

rows = []
cfg = D.SIDES["zb"]
for label in sorted(set(D.WANT)):
    after, marked = D.build(label)
    if marked:
        before = [ln.replace(":" + probe_signal.POKE, "") for ln in after]
    else:
        before, after = after, None
    rows.append((before, after, dict(boot=cfg["boot"], step=8.0,
                                     cap_gap=10.0, reset=cfg["reset"])))
b, a = total("deffn", rows); GB += b; GA += a

print(f"\n{'TOTAL':<12} {'':>4}          {'':>3}   {GB:8.0f} -> {GA:8.0f} "
      f"emulated s   ({GA-GB:+7.0f}, {100*(GA-GB)/GB:+5.1f}%)   "
      f"~{0.003*(GB-GA):5.1f} s wall")
