#!/usr/bin/env python3
r"""❌ D-PAINTHANG WITHDRAWN 2026-09-24: this probe first passed `cap_gap`,
which does NOT delay the capture after RUN; its "never finishes" rows were that.
Now `run_gap`. The real timing is scratchpad/paintclock_probe.py (1.73x, any shape).

D-PAINTHANG (2026-09-24) -- a SCREEN 3 PAINT that floods to the screen edges
finishes on the VG-8020 (66 jiffies) and had not finished on zerobas after 400
emulated seconds, with no error (ON ERROR GOTO trapped nothing). Narrowing: which
geometry triggers it? Each case reports [P inside outside jiffies] or [E err line].
NO-VERDICT (per-side readings, a characterisation)."""
import os, re, sys
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(_R, "probes", "lib"), os.path.join(_R, "probes", "basic")]
import omsx_repl
MACHINES = ("Philips_VG_8020", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))
CASES = [
    ("small-box",  ["SCREEN3", "LINE(40,40)-(80,80),15,B", "T=TIME", "PAINT(60,60),11"]),
    ("edge-box",   ["SCREEN3", "LINE(0,0)-(80,80),15,B", "T=TIME", "PAINT(40,40),15"]),
    ("empty-full", ["SCREEN3", "T=TIME", "PAINT(60,60),11"]),
]
for name, body in CASES:
    got = []
    for m in MACHINES:
        prog = ["ON ERROR GOTO 100"] + body + [
            "T=TIME-T:A=POINT(60,60):B=POINT(200,150)", 'SCREEN0:PRINT"[P";A;B;T;"]":END']
        lines = [f"{10*(i+1)} {b}" for i, b in enumerate(prog)] + [
            '100 SCREEN0:PRINT"[E";ERR;ERL;"]":END', "RUN"]
        raw = omsx_repl.run_case(m, "direct", lines, run_gap=30.0, timeout=900.0) or ""
        f = re.findall(r"\[([EP][^\]]*)\]", raw)
        got.append(" ".join(f[-1].split()) if f else "<NOT DONE>")
    print(f"{name:11} vg8020 {got[0]:18} zb {got[1]}", flush=True)
