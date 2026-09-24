#!/usr/bin/env python3
r"""D-PAINTHANG, re-measured with the RIGHT CLOCK (2026-09-24).

`TIME` counts in the interrupt handler, and PAINT brackets every pixel read and
plot with DI/EI -- so a jiffy count taken across a PAINT UNDER-COUNTS. A zerobas
flood read `T=115` jiffies while its screen stayed blank 60 s after RUN. This
times the PAINT statement between two program-written marks (emulated time,
docs/spec-probe-mark.md), which interrupts cannot distort, on both machines.
NO-VERDICT (per-side seconds and the ratio)."""
import os, sys
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(_R, "probes", "lib"), os.path.join(_R, "probes", "basic")]
import omsx_repl
MACHINES = ("Philips_VG_8020", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))
CASES = [("empty-full", ["SCREEN3"]),
         ("one-block",  ["SCREEN3", "PSET(20,20),15"]),
         ("h-line",     ["SCREEN3", "LINE(0,100)-(255,100),15"]),
         ("small-box",  ["SCREEN3", "LINE(40,40)-(80,80),15,B"])]
print(f"{'case':11} {'vg8020 s':>10} {'zb s':>10} {'zb/ref':>7}")
for name, setup in CASES:
    res = []
    for m in MACHINES:
        body = setup + ["POKE&HE000,201", "PAINT(60,60),11", "POKE&HE000,202", "SCREEN0"]
        so = {}
        omsx_repl.run_case(m, "stored", body, sentinel=(0xE000, 202), sentinel_capture=True,
                           cap_gap=900.0, timeout=1800.0, settle_out=so)
        mk = so.get("marks", {}).get(0, [])
        t1 = [t for t, v in mk if v == 201]; t2 = [t for t, v in mk if v == 202]
        res.append((t2[0] - t1[0]) if t1 and t2 else None)
    r, z = res
    print(f"{name:11} {r if r is None else round(r,3):>10} {z if z is None else round(z,3):>10} "
          f"{(round(z/r,2) if r and z else '-'):>7}", flush=True)
