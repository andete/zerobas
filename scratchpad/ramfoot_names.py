#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RAMFOOT naming pass: which DOCUMENTED work-area cells the VG-8020 writes
for the 16 ops and zerobas does not, named from C-BIOS's systemvars.asm (the
sysvar denominator's own generator), with any D-REHOME verdict attached.

Offline: reads scratchpad/ramfoot_run.out, runs no emulator. The names are a
LABEL for a byte, never a verdict (sysvarsweep's rule)."""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(REPO, "probes", "basic"), os.path.join(REPO, "probes", "lib")]
import basic_probe_sysvarsweep as svs   # noqa: E402

RUN = os.path.join(REPO, "scratchpad", "ramfoot_run.out")


def expand(field):
    out = set()
    for tok in field.split():
        m = re.match(r"\$([0-9A-F]{4})(?:-\$([0-9A-F]{4}))?", tok)
        if m:
            a = int(m.group(1), 16)
            b = int(m.group(2), 16) if m.group(2) else a
            out |= set(range(a, b + 1))
    return out


def main():
    table = svs.load_table(svs.CBIOS_SRC)
    names, head_of = svs.build_namer(table)
    rehomed = {n: (zb, v) for n, _a, _w, zb, v in svs.REHOMED}
    op, per = None, {}
    for ln in open(RUN):
        m = re.match(r"^(\w+) +\d+ +\d+ +\d+ +\d+ +\d+$", ln)
        if m:
            op = m.group(1)
            continue
        m = re.match(r"^   ref std only: (.*)$", ln)
        if m and op:
            for a in expand(m.group(1)):
                per.setdefault(a, []).append(op)
    if not per:
        print("REFUSE: no `ref std only` cells parsed from", RUN)
        return 2
    heads = {}
    for a, ops in per.items():
        h = head_of.get(a, a)
        heads.setdefault(h, [set(), set()])
        heads[h][0].add(a)
        heads[h][1] |= set(ops)
    print(f"{len(per)} reference-only documented bytes in {len(heads)} variables\n")
    print(f"{'variable':22} {'addr':6} {'bytes':>5}  {'ops':>3}  D-REHOME / zerobas home")
    for h in sorted(heads):
        cells, ops = heads[h]
        nm = names.get(h, "?").split("+")[0]
        rh = " / ".join(f"{v} (zb ${zb:04X})" for n, (zb, v) in rehomed.items()
                        if n in nm.split("/"))
        print(f"{nm:22} ${h:04X} {len(cells):5}  {len(ops):3}  {rh or '-'}"
              f"   [{', '.join(sorted(ops))}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
