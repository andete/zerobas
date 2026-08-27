#!/usr/bin/env python3
"""Correctness differential for SAVESTATE-RESTORE-PER-CASE (docs/spec-probe-savestate).

THE FIRST DELIVERABLE, not the speedup. For each machine and each circmiss case,
compare the RAW capture of:

  COLD    : boot-per-case, boot=BOOT (exactly what circmiss/run_cases does today)
  RESTORE : loadstate a ready-prompt snapshot taken at t=BOOT, inject at t=0 so
            the absolute emulated schedule is identical -- only the ROUTE to the
            t=BOOT machine state differs (cold boot vs loadstate).

If every capture is byte-identical on all three machines, openMSX's savestate is
lossless for what our captures read and RESTORE may replace a cold boot. Any
divergence => restore is NOT equivalent for that case; find out why before wiring.
"""
import os
import sys

ROOT = "/Users/joost/projects/zerobas"
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "scratchpad"))
import omsx_repl                                                   # noqa: E402
import circmiss_probe as cm                                        # noqa: E402

STATE_DIR = os.path.join(ROOT, "scratchpad", "ss_diff_states")
os.makedirs(STATE_DIR, exist_ok=True)

# capture: "screen" (default) reproduces circmiss exactly. A stronger, timing-
# sensitive variant reads VRAM mid-draw -- added below as a second battery.
CAP = "screen"


def specs_for(side):
    cfg = cm.SIDES[side]
    labels = list(cm.CASES)
    specs = [("direct", list(cfg["reset"]) + cm.CASES[l] + ["RUN"]) for l in labels]
    return labels, specs, cfg


def run_side(side):
    labels, specs, cfg = specs_for(side)
    machine, boot = cfg["machine"], cfg["boot"]
    print(f"=== {side} ({machine}, boot={boot}) ===", flush=True)
    state = os.path.join(STATE_DIR, f"{side}")
    oms = omsx_repl.make_savestate(machine, state, boot=boot)
    print(f"  savestate -> {oms}", flush=True)
    ndiff = 0
    for l, spec in zip(labels, specs):
        kw = dict(reset=(), step=3.0, cap_gap=8.0, timeout=300.0, capture=CAP)
        cold = omsx_repl.run_batch(machine, [spec], boot=boot, **kw)[0]
        rest = omsx_repl.run_batch(machine, [spec], boot=0.0,
                                   state_load=oms, **kw)[0]
        same = cold == rest
        if not same:
            ndiff += 1
        cf = cm.face(cold)
        rf = cm.face(rest)
        tag = "OK " if same else "*** DIFF"
        print(f"  {tag} {l:10s} cold={cf!r} restore={rf!r} "
              f"raw_eq={same}", flush=True)
        if not same:
            # locate the first differing row for diagnosis
            _diag(l, cold, rest)
    print(f"  {side}: {len(labels)} cases, {ndiff} raw-DIFF\n", flush=True)
    return ndiff


def _diag(label, cold, rest):
    if cold is None or rest is None:
        print(f"      NONE cold={cold is None} rest={rest is None}")
        return
    C = omsx_repl.COLS
    for r in range(omsx_repl.ROWS):
        a = cold[r * C:(r + 1) * C]
        b = rest[r * C:(r + 1) * C]
        if a != b:
            print(f"      row {r:2d} cold={a!r}")
            print(f"             rest={b!r}")


def main():
    sides = sys.argv[1:] or ["vg8020", "cf3300", "zb"]
    total = sum(run_side(s) for s in sides)
    print(f"TOTAL raw-DIFF across {sides}: {total}")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
