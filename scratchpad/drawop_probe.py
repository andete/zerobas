#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DRAWOP — DRAW's missing operand, and the same shared tail for the THIRD time.

`SCREEN2:DRAW` is ERR 13 here and 24 on both references (D-MISSOP3) -- the last
of the roots that slice found. `ex_draw` ends with `call str_eval / jp
nc,gfx_typeerr`, which is the shape D-PUSING and D-MIDOP each split.

🔴 D-MISSOP3's ORIGINAL `DRAW` ROW AGREED AT 5 ON ALL THREE AND HID THIS. In
SCREEN 0 the mode gate refuses before the operand is looked at, so the row was
structurally incapable of seeing the divergence. Every row here that must reach
the tail says SCREEN2 first, and two rows test the mode-gate ordering the source
asserts in prose.

Predictions pinned in scratchpad/drawop_predictions.md before this ran once.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_signal                                               # noqa: E402

ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_M, boot=8.0, reset=("NEW",)),
}


def case(stmt):
    return probe_signal.mark_ends([
        "10 ONERRORGOTO900",
        f"20 {stmt}",
        '50 SCREEN0:CLS:PRINT"[";ERR;"]":END',
        '900 SCREEN0:CLS:PRINT"[";ERR;"]":END'])


CASES = {
    # --- the shared str_eval tail, in a GRAPHICS mode where it is reachable ---
    'd.none':    case('SCREEN2:DRAW'),
    'd.colon':   case('SCREEN2:DRAW:PRINT1'),
    'd.plus':    case('SCREEN2:DRAW+'),
    'd.num':     case('SCREEN2:DRAW 5'),
    # --- the source's OWN justification for the mode gate coming first -------
    'd.scr0':    case('DRAW'),
    'd.scr0num': case('DRAW 5'),
    # --- controls ------------------------------------------------------------
    'd.ok':      case('SCREEN2:DRAW"R10"'),
    'd.var':     case('SCREEN2:A$="R10":DRAW A$'),
}


BR = re.compile(r"\[([^\]]*)\]")
NUM = re.compile(r"^[-0-9. ]*$")


def face(cap):
    if cap is None:
        return "<NO CAPTURE>"
    for m in BR.finditer("".join(cap)):
        if NUM.match(m.group(1)):
            return " ".join(m.group(1).split()) or "<EMPTY>"
    return "<NO OUTPUT>"


def main():
    only, sides = None, ["vg8020", "cf3300", "zb"]
    for a in sys.argv[1:]:
        if a.startswith("--sides="):
            sides = [x for x in a.split("=", 1)[1].split(",") if x in SIDES]
        else:
            only = a.split(",")
    labels = [l for l in CASES if not only or any(o in l for o in only)]
    faces, tally = {}, probe_signal.Tally()
    for s in sides:
        cfg = SIDES[s]
        faces[s] = {}
        for l in labels:
            out = {}
            caps = omsx_repl.run_cases(
                cfg["machine"],
                [("direct", list(cfg["reset"]) + CASES[l] + ["RUN"])],
                batch=False, boot=cfg["boot"], step=3.0, cap_gap=8.0,
                timeout=300.0, **probe_signal.kwargs(out))
            tally.add(out, label=f"{s}/{l}")
            faces[s][l] = face(caps[0])
            print(f"  ran {s:7s} {l:<13s} -> {faces[s][l]!r}", flush=True)
    print()
    W = max(len(l) for l in labels)
    ndiff = nmeas = 0
    for l in labels:
        vals = {s: faces[s][l] for s in sides}
        refs = {vals[s] for s in sides if s != "zb"}
        line = f"  {l:<{W}}  " + "  ".join(f"{s}={vals[s]!r}" for s in sides)
        if not refs:
            print(line + "   (zb only)"); continue
        if len(refs) != 1:
            note = "   ⚠️ THE REFERENCES DISAGREE — not a want"
        elif any("<NO" in v for v in vals.values()):
            note = "   .... NOT MEASURED"
        elif vals["zb"] not in refs:
            note = "   🔴 DIFF"; ndiff += 1; nmeas += 1
        else:
            note = "   ✅"; nmeas += 1
        print(line + note)
    print(f"\n  {nmeas} scored, {ndiff} DIFF, {len(labels) - nmeas} not measured")
    print(tally.line())
    return 1 if nmeas != len(labels) else 0


if __name__ == "__main__":
    sys.exit(main())
