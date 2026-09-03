#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-GICINI — the abort seam must stop the music. docs/spec-basic-gicini.md.

Both references run a GICINI-equivalent teardown when a program ABORTS (untrapped
error, in run mode or direct mode), when it BREAKS (`STOP` / Ctrl-STOP), and on
`BEEP`: MUSICF goes to 0 and the PSG tone amplitudes are silenced. zerobas did
none of them and held the note forever. Six rows, both references agreeing on
every one, fixed 2026-09-03.

TWO HALVES, AND THE SECOND ONE EXISTS BECAUSE A KNIFE PROVED THE FIRST IS BLIND
TO IT. `--rows` scores the 36 BASIC-visible rows against WANT. `--trace` scores
the PSG amplitude. Knife K-GI4 (scratchpad/gicini_knives.py) deleted the
amplitude loop while keeping `ld (MUSICF),a` and **moved zero of the 36 rows** —
the machine sustains the note, which is the actual user-visible symptom, and
every row stays green because every row reads MUSICF. The trace half is not
belt-and-braces; it is the only cover that exists for half of `psg_silence`.

WHERE `WANT` COMES FROM. Read off BOTH references (Philips VG-8020 and National
CF-3300), boot-per-case, and GENERATED from the run log rather than transcribed —
36 rows retyped by hand is how a prediction ends up in the result column. The
generator refuses any row the two references disagree on; it refused none.

🟢 THE TRACE HALF CARRIES ITS OWN CONTROL AND IT IS LOAD-BEARING. Three separate
rounds of this trace read amplitude 0 on every side INCLUDING the control, which
is what "the abort silenced it" and "the machine never booted" look like alike
(typing before boot; a raw 0x0D where Tcl needed a two-character escape). So
`ctl` — the same program with `GOTO` in place of `STOP`, which never aborts —
must read NON-ZERO or the trace scores RED without looking at the subject.
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, HERE)
import probe_tmp                                                  # noqa: E402
import psgtrace                                                   # noqa: E402
import basic_probe_deffn as D                                     # noqa: E402

# ~60 s of music: the fixture types one line per 8 s slot, so a shorter string
# outlives nothing and four rows silently measured the drain instead of the
# subject (spec §4). T32 is the slowest MSX tempo; the NOTE COUNT is deliberately
# unchanged, because a longer MML string fills the 128 B ring and makes PLAY
# block, which is a different fixture again.
LONG = "T32L1CDEFGAB"
M = "PEEK(&HFB3F)"          # MUSICF: a published work-area address, so the same
                            # expression names the same thing on all three sides

CASES = {
    "m.ctl0":   ([], M),
    "m.sound":  (["SOUND 8,15"], M),
    "m.drain":  (['PLAY"L64C"', "FOR I=1 TO 900:NEXT"], M),
    "m.one":    ([f'PLAY"{LONG}"'], M),
    "m.two":    ([f'PLAY"{LONG}","{LONG}"'], M),
    "m.three":  ([f'PLAY"{LONG}","{LONG}","{LONG}"'], M),
    "m.skipb":  ([f'PLAY"{LONG}",,"{LONG}"'], M),
    "m.voiceb": ([f'PLAY,"{LONG}"'], M),
    "m.empty":  (['PLAY""'], M),
    "m.rest":   (['PLAY"R1"'], M),
    "m.err":    ([f'PLAY"{LONG}"', "ON ERROR GOTO 50", "ERROR 5", "RESUME 60"], M),
    "m.clear":  ([f'PLAY"{LONG}"', "CLEAR"], M),
    "m.screen": ([f'PLAY"{LONG}"', "SCREEN 1:SCREEN 0"], M),
    "m.beep":   ([f'PLAY"{LONG}"', "BEEP"], M),
    "m.width":  ([f'PLAY"{LONG}"', "WIDTH 32"], M),
    "m.sound2": ([f'PLAY"{LONG}"', "SOUND 8,15"], M),
    "m.sound7": ([f'PLAY"{LONG}"', "SOUND 7,63"], M),
    "m.cls":    ([f'PLAY"{LONG}"', "CLS"], M),
    "m.keyoff": ([f'PLAY"{LONG}"', "KEY OFF"], M),
    "m.beep2":  (["BEEP"], M),
    "m.playfn": ([f'PLAY"{LONG}"'], "PLAY(0)"),
    "m.playfn0": ([], "PLAY(0)"),
}
_R = f'CLS:PRINT"[";{M};"]"'
DIRECT = {
    "e.ctl":      [_R],
    "e.direct":   [f'PLAY"{LONG}"', _R],
    "e.end":      [f'10 PLAY"{LONG}"', "20 END", "RUN", _R],
    "e.untrap":   [f'10 PLAY"{LONG}"', "20 ERROR 5", "RUN", _R],
    "e.stop":     [f'10 PLAY"{LONG}"', "20 STOP", "RUN", _R],
    "e.errnat":   [f'10 PLAY"{LONG}"', "20 GOSUB 999", "RUN", _R],
    "e.errdir":   [f'PLAY"{LONG}"', "GOSUB 999", _R],
    "e.cont":     [f'10 PLAY"{LONG}"', "20 STOP", "30 END", "RUN", "CONT", _R],
    # 🟢 THE TWO ROWS THAT SAY THE FOUR ABOVE AGREE FOR THE RIGHT REASON: a
    # HARMLESS statement in the event's position. If these read 0 the fixture has
    # outlived its own queue and the whole `e.*` block is measuring the drain.
    "e.nop":      [f'PLAY"{LONG}"', "X=1", _R],
    "e.nop2":     [f'PLAY"{LONG}"', "PRINT", _R],
    # 🎯 the fix must leave the queue REUSABLE, not merely quiet
    "e.replay":   [f'10 PLAY"{LONG}"', "20 STOP", "RUN", f'PLAY"{LONG}"', _R],
    "e.replayfn": [f'10 PLAY"{LONG}"', "20 STOP", "RUN", f'PLAY"{LONG}"',
                   'CLS:PRINT"[";PLAY(0);"]"'],
    "e.new":      [f'10 PLAY"{LONG}"', "RUN", "NEW", _R],
    "e.runagain": [f'10 PLAY"{LONG}"', "RUN", "RUN", _R],
}

# 🟢 CONTROLS: rows with no abort and no BEEP in them. A red here means the
# apparatus, not the seam, and is reported separately.
CONTROLS = {"m.ctl0", "m.sound", "m.drain", "m.one", "m.two", "m.three",
            "m.empty", "m.rest", "e.ctl", "e.direct", "e.nop", "e.nop2"}

WANT = {
    'e.cont'        : '0',
    'e.ctl'         : '0',
    'e.direct'      : '1',
    'e.end'         : '1',
    'e.errdir'      : '0',
    'e.errnat'      : '0',
    'e.new'         : '1',
    'e.nop'         : '1',
    'e.nop2'        : '1',
    'e.replay'      : '1',
    'e.replayfn'    : '-1',
    'e.runagain'    : '1',
    'e.stop'        : '0',
    'e.untrap'      : '0',
    'm.beep'        : '0',
    'm.beep2'       : '0',
    'm.clear'       : '1',
    'm.cls'         : '1',
    'm.ctl0'        : '0',
    'm.drain'       : '0',
    'm.empty'       : '0',
    'm.err'         : '1',
    'm.keyoff'      : '1',
    'm.one'         : '1',
    'm.playfn'      : '-1',
    'm.playfn0'     : '0',
    'm.rest'        : '1',
    'm.screen'      : '1',
    'm.skipb'       : 'ERR 2 AT 20',
    'm.sound'       : '0',
    'm.sound2'      : '1',
    'm.sound7'      : '1',
    'm.three'       : '7',
    'm.two'         : '3',
    'm.voiceb'      : 'ERR 2 AT 20',
    'm.width'       : '1',
}

TRACE_MACHINES = {
    "vg8020": ("Philips_VG_8020", 8.0, ""),
    "cf3300": ("National_CF-3300", 14.0, "\\rSCREEN 0\\rNEW\\r"),
    "zb":     (D.SIDES["zb"]["machine"], 8.0, ""),
}
TRACE_STIM = {
    "ctl":  '10 PLAY"L1CDEFGAB"\\r20 GOTO 20\\rRUN',   # never aborts -> must SOUND
    "stop": '10 PLAY"L1CDEFGAB"\\r20 STOP\\rRUN',      # aborts -> must be SILENT
}


def trace_peak(side, kind):
    machine, boot, reset = TRACE_MACHINES[side]
    # probe_tmp.tmp(), not a hardcoded root: this probe runs inside the parallel
    # battery, and a fixed name is the collision-plus-leak pair that module
    # exists to close (`make temp-root-check` is what caught it here).
    out = probe_tmp.tmp(f"gicini_psg_{side}_{kind}.txt")
    psgtrace.trace(machine, reset + TRACE_STIM[kind], out, n=400,
                   tp=boot + 1.0, arm=boot + 6.0, deadline=boot + 20.0)
    if not os.path.exists(out):
        return None
    rows = psgtrace.parse(out)
    if not rows:
        return None
    return max(max(r[8], r[9], r[10]) for _, r in rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sides", default="zb")
    ap.add_argument("--rows", action="store_true", help="score the BASIC rows")
    ap.add_argument("--trace", action="store_true", help="score the PSG trace")
    ap.add_argument("--gate", action="store_true", help="both halves; rc=1 on red")
    a = ap.parse_args()
    if a.gate:
        a.rows = a.trace = True
    if not (a.rows or a.trace):
        a.rows = a.trace = True

    D.CASES.update(CASES)
    D.DIRECT.update(DIRECT)
    order = sorted(WANT)
    red_gate, red_ctl, blank = [], [], []

    if a.rows:
        sides = a.sides.split(",")
        res = {s: D.run_side(s, order) for s in sides}
        w = max(len(l) for l in order)
        print(f"\n{'row':<{w}}  {'want':>14}  " +
              "  ".join(f"{s:>14}" for s in sides) + "   verdict")
        for l in order:
            vals = [str(res[s].get(l)) for s in sides]
            ok = all(v == WANT[l] for v in vals)
            if not ok:
                (red_ctl if l in CONTROLS else red_gate).append(l)
            if any(v in ("<NO OUTPUT>", "<NO CAPTURE>", "None") for v in vals):
                blank.append(l)
            print(f"{l:<{w}}  {WANT[l]:>14}  " +
                  "  ".join(f"{v:>14}" for v in vals) +
                  f"   {'ok' if ok else 'RED'}")
        print(f"\nrows: {len(order)}  gate-red {len(red_gate)}  "
              f"control-red {len(red_ctl)}  blank {len(blank)}")
        if red_ctl:
            print("  🔴 CONTROL RED -- the apparatus, not the seam: "
                  + " ".join(red_ctl))
        if red_gate:
            print("  🔴 GATE RED: " + " ".join(red_gate))

    trace_red = []
    if a.trace:
        print("\n--- PSG amplitude (the half no row can see; knife K-GI4) ---")
        ctl = trace_peak("zb", "ctl")
        stop = trace_peak("zb", "stop")
        print(f"  zb/ctl  peak amplitude {ctl}   (must be NON-ZERO: the control)")
        print(f"  zb/stop peak amplitude {stop}  (must be 0: silenced by the abort)")
        if not ctl:
            trace_red.append("ctl-blind")
            print("  🔴 CONTROL READS SILENT -- the trace is not looking at music; "
                  "the `stop` reading below says NOTHING.")
        if stop != 0:
            trace_red.append("stop-sounding")
            print("  🔴 the aborted program is still sounding")

    bad = red_gate + red_ctl + blank + trace_red
    print("\n" + ("GICINI: PASS" if not bad else f"GICINI: RED ({len(bad)})"))
    return 1 if (a.gate and bad) else 0


if __name__ == "__main__":
    sys.exit(main())
