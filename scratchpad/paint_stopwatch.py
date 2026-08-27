#!/usr/bin/env python3
"""D-PAINTVRAM: EXACT emulated-time duration of a PAINT, on all three machines.

The mark stopwatch (docs/spec-probe-budget.md §6): the case's own BASIC POKEs a
watched address either side of the operation, and openMSX logs the emulated
instant of every write -- so the difference IS the operation's duration, on the
black-box references too, and it repeats bit-identically across runs.

⚠️ The watchpoint is armed at the LAST injection, so the marks must be POKEd by
the RUNNING PROGRAM, after `RUN`.
"""
from __future__ import annotations
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                   # noqa: E402

ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW", "CLS")),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW", "CLS")),
    "zb":     dict(machine=ZB, boot=8.0, reset=("NEW", "CLS")),
}
MARK = 0xE000
VRAM2 = ("vram_segs", [(0x0000, 0x1800), (0x2000, 0x1800)])

# (label, the ONE operation being timed)
OPS = [
    ("paint.flood",  "PAINT(128,96),15"),
    ("paint.circle", "CIRCLE(128,96),60,15:PAINT(128,96),15"),
    ("circle",       "CIRCLE(128,96),80,15"),
    ("line",         "LINE(0,0)-(255,191),15"),
]


def measure(side, op):
    cfg = SIDES[side]
    body = ["10 SCREEN2", f"20 POKE&H{MARK:04X},1", f"30 {op}",
            f"40 POKE&H{MARK:04X},255", "50 GOTO50"]
    spec = ("direct", list(cfg["reset"]) + body + ["RUN"])
    so: dict = {}
    omsx_repl.run_batch(cfg["machine"], [spec], reset=(), boot=cfg["boot"],
                        step=2.5, run_gap=120.0, cap_gap=8.0, capture=VRAM2,
                        timeout=600.0, verify_delivery=False,
                        sentinel=(MARK, 255), settle_out=so)
    marks = so.get("marks", {}).get(0, [])
    t = {v: i for i, v in marks}
    if 1 not in t or 255 not in t:
        return None, marks
    return t[255] - t[1], marks


def main():
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    print(f"{'operation':<14} {'vg8020':>12} {'cf3300':>12} {'zb':>12}   verdict")
    for label, op in OPS:
        if only and label not in only:
            continue
        d = {}
        for side in ("vg8020", "cf3300", "zb"):
            dur, marks = measure(side, op)
            d[side] = dur
            if dur is None:
                print(f"  !! {label} {side}: NO MARKS -- {marks}")
        if all(v is not None for v in d.values()):
            best = min(d["vg8020"], d["cf3300"])
            r = d["zb"] / best
            verdict = (f"🔴 {r:.2f}x SLOWER" if r > 1.25 else
                       f"✅ {r:.2f}x" if r >= 0.8 else f"✅ {r:.2f}x (faster)")
            print(f"{label:<14} {d['vg8020']:>12.6f} {d['cf3300']:>12.6f} "
                  f"{d['zb']:>12.6f}   {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
