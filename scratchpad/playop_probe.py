#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-PLAYOP — PLAY's missing operand, and the loop the filing did not count.

TODO.md:8950 (T-B10921) (D-DUPSPAN §6.3) files `PLAY` / `PLAY:PRINT 1` as ERR 24 on both
references where zerobas says 2, and states that **two of `pl_syntax`'s four
call sites move, not four**.

🔴 THAT COUNTS INSTRUCTIONS, AND `pl_voice` IS A LOOP. `basic/play.asm:74` is
`jr pl_voice`, so the three entry-side tests -- `:42` (`or a`), `:44`
(`cp COLON`), `:46` (`cp ','`) -- are re-entered after EVERY comma. Each has two
entry conditions, the FIRST voice and a SUBSEQUENT one, and a site that is right
for one may be wrong for the other. D-ONLIST had exactly this shape: one
instruction, two answers, depending on how it was reached.

The fourth site (`:73`, a 4th voice string) the filing marks UNMEASURED and
says not to assume into either half. It gets a row.

Readout `[ERR]`: 0 if the statement completed, else the MSX error code.
Predictions pinned in scratchpad/playop_predictions.md before this ran once.

⚠️ NOT COVERED: whether PLAY queues anything BEFORE raising. The seam work found
wrong ordering at SWAP and PAINT; this reads the error code only.
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
    # --- the filed claims, FIRST voice --------------------------------------
    'p.bare':       case('PLAY'),               # :42  or a
    'p.colon':      case('PLAY:PRINT1'),        # :44  cp COLON
    'p.comma':      case('PLAY,"E"'),           # :46  cp ','
    # --- the SAME three instructions, SUBSEQUENT voice ----------------------
    # pl_voice is a LOOP (`jr pl_voice` after each comma), so every one of the
    # three tests above has a second entry condition the filing does not name.
    'p.trail':      case('PLAY"A",'),           # :42 on voice 2
    'p.trailcolon': case('PLAY"A",:PRINT1'),    # :44 on voice 2
    'p.dblcomma':   case('PLAY"A",,"C"'),       # :46 on voice 2
    # --- the site the filing calls UNMEASURED -------------------------------
    'p.four':       case('PLAY"A","B","C","D"'),  # :73  cp 3 / jr nc
    # --- controls, two of them straight out of pl_voice's own header ---------
    'p.ok':         case('PLAY"A"'),
    'p.ok3':        case('PLAY"A","B","C"'),
    'p.empty':      case('PLAY""'),             # header: empty "" is allowed
    'p.num':        case('PLAY 5'),             # header: numeric -> Type mismatch
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
