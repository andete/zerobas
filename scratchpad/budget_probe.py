#!/usr/bin/env python3
"""ACTUAL-vs-BUDGET per case — the instrument the emulated-time-budget item needs.

Every probe case buys a window of EMULATED time between its last injected line
(`RUN`) and its capture: `step` (or a per-phase override like graphics'
`PAINT_STEP = 90.0`) plus whatever `cap_gap` adds. That window is a hand-picked
margin. This measures what the machine ACTUALLY needed inside it: sample the
capture region N times across the window, and find the LAST sample at which the
region still changed. Everything after that instant is margin.

🔴 THE INSTRUMENT MUST NOT MOVE THE THING IT MEASURES. openMSX `after time`
callbacks are atomic w.r.t. the emulated CPU and cost zero emulated time, so a
sampled run should be trajectory-identical to an un-sampled one. That is
ASSERTED here (`--inert`), not assumed.

⚠️ A settle point is a LOWER BOUND on what the budget must be, not a licence to
cut to it: the sample grid is coarse (window/N), the machine that settles latest
across the three is the one that sets the floor, and a case whose region is still
changing at the LAST sample has not settled at all inside its window.
"""
from __future__ import annotations

import os
import sys

ROOT = "/Users/joost/projects/zerobas"
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "scratchpad"))
import omsx_repl                                                   # noqa: E402

N = 40                      # samples per window -> resolution = window/40

ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW", "CLS")),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW", "CLS")),
    "zb":     dict(machine=ZB, boot=8.0, reset=("NEW", "CLS")),
}

# 🔴 PATTERN **AND** COLOUR. A first cut sampled only the pattern table
# (0x0000-0x17FF) and reported the PAINT flood settling in 0.254 s on BOTH
# references -- because they fill by writing the COLOUR table alone (measured:
# reference pattern all 0x00 / colour all 0x0F; zerobas pattern all 0xFF /
# colour all 0xF4 -- same visible screen, POINT 15 on all three, different
# bytes, the filed "the two engines write DIFFERENT BYTES" fact). A sampler
# pointed at a region the work never writes reports "settled immediately" for
# every machine that does the work elsewhere, and a budget cut on that reading
# would be cut on nothing [[readout-blind-to-its-own-subject]].
VRAM2 = ("vram_segs", [(0x0000, 0x1800), (0x2000, 0x1800)])   # pattern + colour

# (label, budget `step`, capture, program) -- the shapes whose budgets are the
# expensive ones, taken from probes/basic/basic_probe_graphics.py.
CASES = [
    # graphics' heaviest: a whole-screen PAINT flood. PAINT_STEP = 90.0 exists
    # for exactly this row, with the comment "generous; see above".
    ("paint.flood", 90.0, VRAM2,
     ["SCREEN2", "PAINT(128,96),15", "GOTO30"]),
    # a bounded PAINT inside a circle -- the ordinary graphics case
    ("paint.circle", 90.0, VRAM2,
     ["SCREEN2", "CIRCLE(128,96),60,15:PAINT(128,96),15", "GOTO30"]),
    # a plain draw, no fill: should settle almost immediately
    ("circle", 90.0, VRAM2,
     ["SCREEN2", "CIRCLE(128,96),80,15", "GOTO30"]),
    # the default text-case budget (step 2.5): an error + PRINT readout
    ("text.err", 2.5, "screen",
     ["ONERRORGOTO900", "SCREEN2", "CIRCLE(50,50),",
      'R=POINT(30,50):SCREEN0:CLS:PRINT"[";ERR;R;"]":END',
      'R=POINT(30,50):SCREEN0:CLS:PRINT"[";ERR;R;"]":END']),
]


def _prog(body):
    out = [f"{10 * (i + 1)} {ln}" for i, ln in enumerate(body)]
    for i, ln in enumerate(out):                    # point a GOTO at itself
        if ln.split(" ", 1)[1].startswith("GOTO"):
            out[i] = f"{(i + 1) * 10} GOTO{(i + 1) * 10}"
    return out


def measure(side, label, step, cap, body):
    cfg = SIDES[side]
    spec = ("direct", list(cfg["reset"]) + _prog(body) + ["RUN"])
    so: dict = {}
    caps = omsx_repl.run_batch(
        cfg["machine"], [spec], reset=(), boot=cfg["boot"], step=step,
        cap_gap=8.0, capture=cap, timeout=600.0, verify_delivery=False,
        settle_n=N, settle_out=so)
    samples = so.get("samples", {}).get(0, [])
    span = so.get("span", {}).get(0)
    if not samples or not span:
        return None
    t_run, t_cap = span
    # the LAST instant at which the capture region still changed
    last_change = None
    for i in range(1, len(samples)):
        if samples[i][1] != samples[i - 1][1]:
            last_change = samples[i][0]
    # 🔴 NO OBSERVED CHANGE IS A BOUND, NOT A VALUE. Every sample identical means
    # the work finished before the FIRST one -- so all that is known is
    # `used < first sample offset`, and printing that offset as "used" would be
    # reporting the grid instead of the machine.
    bounded = last_change is None
    settled = samples[0][0] if bounded else last_change
    still_moving = samples[-1][1] != samples[-2][1] if len(samples) > 1 else False
    return dict(t_run=t_run, t_cap=t_cap, settled=settled, bounded=bounded,
                window=t_cap - t_run, used=settled - t_run,
                margin=t_cap - settled, still_moving=still_moving,
                cap=caps[0])


def main():
    inert = "--inert" in sys.argv
    sides = [a for a in sys.argv[1:] if a in SIDES] or list(SIDES)
    only = [a for a in sys.argv[1:] if a.startswith("only=")]
    labels = only[0][5:].split(",") if only else None

    if inert:
        # 🔴 the instrument's own control: sampling must not move the capture.
        print("=== INERTNESS: capture with sampling ON vs OFF ===", flush=True)
        bad = 0
        for side in sides:
            cfg = SIDES[side]
            for label, step, cap, body in CASES:
                if labels and label not in labels:
                    continue
                spec = ("direct", list(cfg["reset"]) + _prog(body) + ["RUN"])
                kw = dict(reset=(), boot=cfg["boot"], step=step, cap_gap=8.0,
                          capture=cap, timeout=600.0, verify_delivery=False)
                off = omsx_repl.run_batch(cfg["machine"], [spec], **kw)[0]
                on = omsx_repl.run_batch(cfg["machine"], [spec],
                                         settle_n=N, settle_out={}, **kw)[0]
                ok = off == on
                bad += 0 if ok else 1
                print(f"  {'ok ' if ok else 'MOVED'} {side:7s} {label:13s} "
                      f"identical={ok}", flush=True)
        print(f"  -> {'INERT' if not bad else str(bad) + ' PERTURBED'}\n",
              flush=True)
        if bad:
            return 1

    print(f"{'case':<14} {'side':<8} {'window':>8} {'used':>8} {'margin':>8} "
          f"{'used%':>6}  note", flush=True)
    for label, step, cap, body in CASES:
        if labels and label not in labels:
            continue
        for side in sides:
            r = measure(side, label, step, cap, body)
            if r is None:
                print(f"{label:<14} {side:<8} {'-':>8} — NO SAMPLES", flush=True)
                continue
            note = ""
            if r["still_moving"]:
                note = "🔴 STILL CHANGING AT THE LAST SAMPLE — budget may be TIGHT"
            elif r["bounded"]:
                note = "settled before the first sample (upper bound)"
            used = ("<%.3f" % r["used"]) if r["bounded"] else "%.3f" % r["used"]
            print(f"{label:<14} {side:<8} {r['window']:8.2f} {used:>9} "
                  f"{r['margin']:8.2f} {100*r['used']/r['window']:5.1f}%  {note}",
                  flush=True)
    print("\nwindow = emulated s bought between RUN and capture; used = to the "
          "last change\nin the capture region; margin = the rest. Resolution is "
          f"window/{N}.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
