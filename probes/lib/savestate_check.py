#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""savestate-check -- the standing correctness gate for SAVESTATE-RESTORE-PER-CASE.

A restored ready-prompt snapshot may replace a cold C-BIOS boot in the probe
harness ONLY while it is proven byte-identical to that cold boot. This gate
re-proves it every run, on the SUBJECT (repack disk) and BOTH oracles
(Philips_VG_8020, National_CF-3300), across text, POINT and raw-VRAM captures --
the last being where a lossy savestate or a phase-misaligned injection would
first diverge (docs/spec-probe-savestate.md).

Method, per machine: take one snapshot at the ready prompt (t=BOOT), then for each
case compare the RAW capture of
  COLD    : boot-per-case at boot=BOOT (exactly what run_cases/run_case does), vs
  RESTORE : loadstate that snapshot, inject at boot=0 so the absolute emulated
            schedule -- hence the VDP/interrupt phase -- is identical.
Any raw byte difference fails the gate for that case.

🔴 A 0-DIFF TALLY IS VACUOUS WITHOUT TEETH. If the comparison could not tell two
genuinely different captures apart it would pass no matter what savestate did, so
the gate also asserts cold(draw) != cold(error) on each machine -- a within-run
control that a real divergence is detectable. A gate whose knife reddens nothing
is not measuring [[apparatus-is-part-of-the-measurement]]."""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omsx_repl                                                   # noqa: E402

ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_M, boot=8.0, reset=("NEW",)),
}

# A ready-numbered graphics program; renumber into direct-mode entry lines.
def _prog(*body):
    return [f"{10 * (i + 1)} {ln}" for i, ln in enumerate(body)]


# (label, capture-spec, program-body). The bodies span the readouts real gates
# take: a text/error screen, a POINT-into-text draw, and two raw-VRAM draws.
VRAM_ALL = ("vram", 0x0000, 0x1800)          # SCREEN-2 pattern table (6144 B)
CASES = [
    # error path: mandatory radius omitted -> ERR 24, nothing drawn
    ("err", "screen",
     _prog("ONERRORGOTO900", "SCREEN2", "CIRCLE(50,50),",
           'R=POINT(30,50):SCREEN0:CLS:PRINT"[";ERR;R;"]":END',
           'R=POINT(30,50):SCREEN0:CLS:PRINT"[";ERR;R;"]":END')),
    # draw path: a legal circle, POINT read back into a text readout
    ("draw", "screen",
     _prog("ONERRORGOTO900", "SCREEN2", "CIRCLE(50,50),20",
           'R=POINT(30,50):SCREEN0:CLS:PRINT"[";ERR;R;"]":END',
           'R=POINT(30,50):SCREEN0:CLS:PRINT"[";ERR;R;"]":END')),
    # raw VRAM, held live: a circle
    ("vcircle", VRAM_ALL, _prog("SCREEN2", "CIRCLE(128,96),80,15", "GOTO30")),
    # raw VRAM, held live: a filled paint (heavier, more VDP traffic)
    ("vpaint", VRAM_ALL,
     _prog("SCREEN2", "CIRCLE(128,96),60,15:PAINT(128,96),15", "GOTO40")),
]


def _spec(cfg, body):
    # renumber the last GOTO to the real last line number
    body = list(body)
    for i, ln in enumerate(body):
        if ln.split(" ", 1)[1].startswith("GOTO"):
            body[i] = f"{(i + 1) * 10} GOTO{(i + 1) * 10}"
    return ("direct", list(cfg["reset"]) + body + ["RUN"])


def run_side(side, state_dir):
    cfg = SIDES[side]
    machine, boot = cfg["machine"], cfg["boot"]
    oms = omsx_repl.make_savestate(machine, os.path.join(state_dir, side),
                                   boot=boot)
    fails = []
    faces = {}
    for label, cap, body in CASES:
        spec = _spec(cfg, body)
        kw = dict(reset=(), step=3.0, cap_gap=8.0, timeout=300.0, capture=cap,
                  verify_delivery=False)
        cold = omsx_repl.run_batch(machine, [spec], boot=boot, **kw)[0]
        rest = omsx_repl.run_batch(machine, [spec], boot=0.0, state_load=oms, **kw)[0]
        faces[label] = cold
        ok = cold is not None and cold == rest
        if not ok:
            fails.append(label)
        print(f"  {'ok ' if ok else 'DIFF'} {side:7s} {label:8s} "
              f"cap_none={cold is None} raw_eq={cold == rest}", flush=True)
    # TEETH: the comparison must distinguish two genuinely different captures.
    teeth_ok = (faces.get("err") is not None and faces.get("draw") is not None
                and faces["err"] != faces["draw"])
    print(f"  {'ok ' if teeth_ok else 'DEAD'} {side:7s} TEETH "
          f"err!=draw={teeth_ok}", flush=True)
    return fails, teeth_ok


def main():
    sides = [s for s in sys.argv[1:] if s in SIDES] or list(SIDES)
    state_dir = tempfile.mkdtemp(prefix="ss_check_")
    print(f"=== savestate-check ({', '.join(sides)}) ===", flush=True)
    all_fail, teeth_bad = [], []
    for s in sides:
        fails, teeth = run_side(s, state_dir)
        all_fail += [(s, f) for f in fails]
        if not teeth:
            teeth_bad.append(s)
    n = len(sides) * len(CASES)
    teeth_msg = "OK" if not teeth_bad else "DEAD on " + ",".join(teeth_bad)
    print(f"\nsavestate-check: {n - len(all_fail)}/{n} restore==cold, "
          f"{len(all_fail)} DIFF; teeth {teeth_msg}", flush=True)
    if all_fail:
        print("  DIFFs: " + ", ".join(f"{s}:{f}" for s, f in all_fail))
    ok = not all_fail and not teeth_bad
    print("=== PASS ===" if ok else "=== FAIL ===")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
