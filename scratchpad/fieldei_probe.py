#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FIELDDI, measure first (2026-11-01): do FIELD / LSET / RSET come back with
interrupts OFF on zerobas? (A D-REREAD batch 8 reviewer: chan_gate_bare's return
has no `ei`.) Black box: TIME (the VDP interrupt's counter) across a fixed busy
loop right after the statement. Interrupts on -> TIME advances by the loop's
frames; off -> it stands still. The CF-3300 is the oracle (Disk BASIC); a control
row runs the loop with no file statement. Typed BASIC in, the screen out.
"""
import os, re, shutil, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides, probe_tmp  # noqa: E402

probe_sides.require_disk("cf3300", "zb")
SIDES = probe_sides.sides("cf3300", "zb")
SRC = os.path.join(ROOT, "disk", "test720.dsk")
CASES = [("ctl", "A=0"), ("field", "FIELD #1,8 AS B$"),
         ("lset", 'LSET A$="X"'), ("rset", 'RSET A$="X"')]


def main():
    for tag, op in CASES:
        row = {}
        for side, c in SIDES.items():
            dsk = probe_tmp.tmp(f"fieldei_{tag}_{side}.dsk")
            shutil.copy(SRC, dsk)
            p = ['10 OPEN "T.DAT" AS #1 LEN=16:FIELD #1,8 AS A$',
                 f"20 T=TIME:{op}:FOR I=1 TO 600:NEXT:D=TIME-T",
                 '30 CLOSE:KILL "T.DAT":PRINT "ZQ";D;"QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=10.0,
                cap_gap=4.0, timeout=420.0, diska=dsk)[0] or "")
            v = re.findall(r'ZQ\s*(-?[0-9]+)\s*QZ', raw)
            row[side] = v[-1] if v else None
        print(f"  {tag:6s} {op:20s} " + "  ".join(f"{s}={row[s]}" for s in SIDES), flush=True)


if __name__ == "__main__":
    main()
