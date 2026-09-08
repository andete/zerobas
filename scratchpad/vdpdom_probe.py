#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-VDPDOM — VDP(n)= and BASE(n)= take int16 where the reference takes a byte?

Picked by ranking every handler by COMMENT DENSITY -- a proxy for how much it has
been examined -- rather than by name. `ex_base_assign` came out near the bottom of
the substantial handlers, and reading it says why it is worth a row set:

    g8_open_paren  -> g8_num_operand   ; the INDEX n
    g8_num_operand -> str_eval_one + gfx_eval_int16

So BOTH the register index and the assigned value get the **int16** domain --
ERR 6 only beyond +-32767. That is exactly the shape D-RAWVAL found in
POKE/VPOKE/OUT hours ago: a value that is semantically a BYTE evaluated in the
address domain, which WRAPS. VDP()= and BASE()= are the same raw-write family and
were not in that sweep.

\U0001f534 THE READOUT DEFENDS ITSELF. A successful bad VDP write reprograms the
display and can destroy the evidence of its own success -- register 0 alone
carries the mode bits. Every row therefore runs `SCREEN 0` (which reprograms every
register) BEFORE printing, so a row that wrote garbage still reports.

\U0001f7e2 AND `BASE(n)=addr` IS NOT ASSUMED TO BE A BYTE. Its value is a VRAM
ADDRESS, so int16 may well be right there; only the INDEX is asked of BASE. The
byte question is put to VDP's value alone, where the register really is 8 bits.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_sides                                                # noqa: E402

SIDES = probe_sides.sides("vg8020", "cf3300", "zb")
CASES = [
    ("ctl",      "VDP(0)=0",    "CONTROL: a legal register write"),
    ("v.val256", "VDP(0)=256",  "VALUE past a byte -- 0 = wrapped"),
    ("v.valneg", "VDP(0)=-1",   "VALUE negative -- the separating cell"),
    ("v.reg99",  "VDP(99)=0",   "INDEX past the register file"),
    ("v.regneg", "VDP(-1)=0",   "INDEX negative"),
    ("b.reg99",  "BASE(99)=0",  "BASE INDEX past its table"),
    ("b.regneg", "BASE(-1)=0",  "BASE INDEX negative"),
]


def main() -> int:
    out = {}
    for tag, stmt, note in CASES:
        row = {}
        for side, c in SIDES.items():
            p = ["10 ON ERROR GOTO 900", "20 E=0", f"30 {stmt}",
                 "40 GOTO 950", "900 E=ERR",
                 '950 SCREEN 0:PRINT"ZQ";E;"QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=12.0,
                cap_gap=4.0, timeout=420.0)[0] or "")
            v = [g for g in re.findall(r'ZQ\s*([0-9]+)\s*QZ', raw)
                 if '"' not in g and ';' not in g]
            row[side] = v[-1] if v else None
        out[tag] = row
        f = {s_: ("<none>" if row[s_] is None else f"ERR={row[s_]}")
             for s_ in SIDES}
        vd = probe_sides.verdict(f["vg8020"], f["cf3300"], f["zb"])
        mark = {"SAME": "", "REFS-SPLIT": "   \U0001f7e1 REFS-SPLIT",
                "DIFF": "   \U0001f534 DIFF"}[vd]
        print(f"  {tag:9s} {stmt:14s} vg={f['vg8020']:9s} cf={f['cf3300']:9s} "
              f"zb={f['zb']:9s}{mark}   {note}", flush=True)

    ctl = out.get("ctl", {})
    if any(ctl.get(s_) != "0" for s_ in SIDES):
        print(f"\n\U0001f534 THE CONTROL DID NOT READ ERR 0 ({ctl}) -- either the "
              f"legal write is failing or the SCREEN 0 readout is not surviving, "
              f"and no row above means anything.")
        return 2
    dis = [t for t in out
           if probe_sides.verdict(out[t]["vg8020"], out[t]["cf3300"],
                                  out[t]["zb"]) == "DIFF"]
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    for t in out:
        print(f"   {t:9s} vg {out[t]['vg8020']}   cf {out[t]['cf3300']}   "
              f"zb {out[t]['zb']}")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
