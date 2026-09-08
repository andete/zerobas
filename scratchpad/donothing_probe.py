#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DONOTHING3 — SET / IPL / CMD are tokenised, then refused on sight.

Three of the eight words in CRUNCH_DIFF_PINNED that the reference tokenises and
zerobas did not. All three are Disk-BASIC STATEMENTS with no verb behind them:
the reference raises ERR 5 (Illegal function call) for the bare form AND for a
form with a tail, so the tail is never parsed and the handler refuses immediately.
`gb_illegal` is already `ld a,5 / jp raise_error`, so three `stmt_table` rows are
the entire main-side cost.

🔴 FOUR SIDES, NOT THREE, AND THE FOURTH IS THE POINT. The VG-8020 IS DISKLESS,
so it does not tokenise these words at all and answers ERR 2 (Syntax error) --
it is NOT the oracle here, the CF-3300 is [[probe-sides]]. But zerobas's kwtable
lives in the sub-ROM, which is present in the DISKLESS build too, so
`C-BIOS_MSX1_EU_REPACK_NODISK` will tokenise `SET` where a real diskless MSX
leaves it a variable name. That is measured here rather than assumed either way,
because diskless is an official target and any disk-related work owes it a row.

  d.ctl      a legal statement -- ERR 0 everywhere, or the probe reads nothing
  d.var      `SET=1` -- the variable a diskless machine still has
  d.set/ipl/cmd            bare      -> ERR 5 on the CF-3300
  d.settail/ipltail        with tail -> ERR 5 too, NOT ERR 2
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_sides                                                # noqa: E402

SIDES = probe_sides.sides("vg8020", "cf3300", "zb", "zb_nodisk")
CASES = [
    ("d.ctl",     "PRINT 1",       "CONTROL: legal, ERR 0 everywhere"),
    ("d.set",     "SET",           "bare SET"),
    ("d.settail", "SET ZZZ QQQ",   "SET with a tail -- 5, not 2"),
    ("d.ipl",     "IPL",           "bare IPL"),
    ("d.ipltail", "IPL ZZZ QQQ",   "IPL with a tail"),
    ("d.cmd",     "CMD",           "bare CMD"),
    ("d.var",     "SET=1:PRINT 0", "SET as a variable name"),
]


def main() -> int:
    out = {}
    for tag, stmt, note in CASES:
        row = {}
        for side, c in SIDES.items():
            p = ["10 ON ERROR GOTO 900", f"20 {stmt}",
                 '30 PRINT"ZQ";0;"QZ":END',
                 '900 PRINT"ZQ";ERR;"QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=10.0,
                cap_gap=4.0, timeout=420.0)[0] or "")
            # the fence is in the source the machine echoes back: take the LAST
            # match and refuse any that carries the quoting of the typed line
            v = [g for g in re.findall(r'ZQ\s*([0-9]+)\s*QZ', raw)
                 if '"' not in g and ';' not in g]
            row[side] = v[-1] if v else None
        out[tag] = row
        f = {s_: ("<none>" if row[s_] is None else f"ERR={row[s_]}")
             for s_ in SIDES}
        vd = probe_sides.verdict(f["vg8020"], f["cf3300"], f["zb"])
        mark = {"SAME": "", "REFS-SPLIT": "   \U0001f7e1 REFS-SPLIT",
                "DIFF": "   \U0001f534 DIFF"}[vd]
        nod = "" if f["zb_nodisk"] == f["vg8020"] else \
              f"   \U0001f534 NODISK {f['zb_nodisk']} vs vg {f['vg8020']}"
        print(f"  {tag:10s} {stmt:14s} vg={f['vg8020']:8s} cf={f['cf3300']:8s} "
              f"zb={f['zb']:8s} nodisk={f['zb_nodisk']:8s}{mark}{nod}",
              flush=True)

    ctl = out.get("d.ctl", {})
    if any(ctl.get(s_) != "0" for s_ in SIDES):
        print(f"\n\U0001f534 THE CONTROL DID NOT READ ERR 0 ({ctl}) -- no row above "
              f"means anything.")
        return 2
    bad = [t for t in ("d.set", "d.settail", "d.ipl", "d.ipltail", "d.cmd")
           if out[t].get("cf3300") != "5" or out[t].get("zb") != "5"]
    print(f"\n=== against the CF-3300 (the oracle; the VG-8020 is DISKLESS): "
          f"{len(bad)} row(s) not matching ERR 5: {bad or 'none'} ===")
    nd = [t for t in out if out[t].get("zb_nodisk") != out[t].get("vg8020")]
    print(f"=== diskless target vs the VG-8020: {len(nd)} divergent row(s): "
          f"{nd or 'none'} ===")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
