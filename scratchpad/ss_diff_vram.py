#!/usr/bin/env python3
"""Stronger, TIMING-SENSITIVE correctness battery for savestate-restore.

The screen battery (ss_diff.py) compares text captures, which are robust to a
one-tick injection offset. This one captures raw VRAM mid/after a graphics draw
-- exactly what graphics-acceptance reads -- where a lossy savestate or a
phase-misaligned injection would first diverge. Same cold-vs-restore method.

Each case draws in SCREEN 2 then `GOTO`-self loops so the capture reads live VRAM
before the prompt corrupts it (see omsx_repl `_cap_expr` "vram").
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

# SCREEN-2 pattern table is 0x0000..0x17FF (6144 B). Capture the whole thing.
VRAM = ("vram", 0x0000, 0x1800)

# stored programs that draw something non-trivial, then loop forever holding VRAM.
DRAWS = {
    "circle":  ["SCREEN2", "CIRCLE(128,96),80,15", "GOTO40"],
    "line":    ["SCREEN2", "LINE(0,0)-(255,191),8", "GOTO40"],
    "linebf":  ["SCREEN2", "LINE(20,20)-(200,150),4,BF", "GOTO40"],
    "circarc": ["SCREEN2", "CIRCLE(128,96),70,7,0.2,3.0", "GOTO40"],
    "paint":   ["SCREEN2", "CIRCLE(128,96),60,15:PAINT(128,96),15", "GOTO40"],
}


def run_side(side):
    cfg = cm.SIDES[side]
    machine, boot = cfg["machine"], cfg["boot"]
    print(f"=== VRAM {side} ({machine}, boot={boot}) ===", flush=True)
    state = os.path.join(STATE_DIR, f"{side}")
    oms = omsx_repl.make_savestate(machine, state, boot=boot)
    ndiff = 0
    for name, body in DRAWS.items():
        # renumber into a stored program: 10 SCREEN2 / 20 draw / 40 GOTO40
        lines = [f"{10*(i+1)} {ln}" for i, ln in enumerate(body)]
        # fix the GOTO target to the actual last line number
        last = 10 * len(body)
        lines[-1] = f"{last} GOTO{last}"
        spec = ("direct", list(cfg["reset"]) + lines + [f"RUN"])
        kw = dict(reset=(), step=3.0, cap_gap=8.0, timeout=300.0, capture=VRAM)
        cold = omsx_repl.run_batch(machine, [spec], boot=boot,
                                   verify_delivery=False, **kw)[0]
        rest = omsx_repl.run_batch(machine, [spec], boot=0.0, state_load=oms,
                                   verify_delivery=False, **kw)[0]
        same = cold == rest
        ndiff += 0 if same else 1
        cl = len(cold) if cold else None
        # count differing nibbles for a divergence magnitude
        nd = None
        if cold and rest and len(cold) == len(rest):
            nd = sum(1 for a, b in zip(cold, rest) if a != b)
        print(f"  {'OK ' if same else '*** DIFF'} {name:8s} "
              f"len={cl} raw_eq={same} diff_nibbles={nd}", flush=True)
    print(f"  VRAM {side}: {ndiff} raw-DIFF\n", flush=True)
    return ndiff


def main():
    sides = sys.argv[1:] or ["vg8020", "cf3300", "zb"]
    total = sum(run_side(s) for s in sides)
    print(f"TOTAL VRAM raw-DIFF across {sides}: {total}")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
