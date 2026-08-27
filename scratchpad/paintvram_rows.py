#!/usr/bin/env python3
"""Run ONLY the new D-PAINTVRAM rows (PHASE H-V + PHASE H's paint_then_pset),
so they can be scored RED on today's build before anything is fixed."""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import basic_probe_graphics as g
import omsx_repl

f = g.phase_h_vram()
print("PHASE H-V fails:", f)

print("=== PHASE H row: paint_then_pset ===")
row = [c for c in g.PAINT_FILL_CASES if c[0] == "paint_then_pset"][0]
label, setup, pts = row
specs = [("stored", g.paint_points_prog(setup, pts))]
ref = omsx_repl.run_cases(g.REF, specs, batch=False, run_gap=g.PAINT_STEP,
                          cap_gap=g.PAINT_CAP_GAP, timeout=g.PAINT_TIMEOUT)[0]
zb = omsx_repl.run_cases(g.ZB, specs, batch=False, run_gap=g.PAINT_STEP,
                         cap_gap=g.PAINT_CAP_GAP, timeout=g.PAINT_TIMEOUT)[0]
rp, zp = g._points(ref, len(pts)), g._points(zb, len(pts))
ok = rp is not None and rp == zp
print(f"  {'PASS' if ok else 'FAIL'} {label:22} ref={rp} zb={zp}")
raise SystemExit(0 if (f == 0 and ok) else 1)
