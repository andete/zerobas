#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""RAM lever: are the workspace's UNATTRIBUTED runs really free -- on BOTH
builds? (Packing the cells above them down would raise the ceiling for both.)

tools/ram_map.py lists runs no declared width covers and warns, every time,
that a run is a CANDIDATE, never free space: a stack growing down from a named
top, or a cell addressed only as an offset, is invisible to it. The disk ROM's
48-byte interrupt stack under INT_STK_TOP ($EAB9..$EAE8) is exactly that.

THE CANDIDATES: runs of >= 16 B in $E26A..$F37F that NEITHER map covers (both
maps' unattributed runs, intersected), less spans already known to be live by
their own declaration but width-less (the disk interrupt stack, the Z80 stack's
floor region $F200..$F37F).

METHOD (dowrite_probe.py's): each build, a write watchpoint per candidate run,
armed at POWER-ON, recording (PC, primary slot register, address) -- our own
code on our own machines -- over the 20 cases of nodiskuse_probe.py.

Prediction: most candidates are never written; on the DISK build at least one
is (a disk-ROM cell addressed by offset).
"""
import os, sys, tempfile
os.environ["ZEROBAS_REFCACHE"] = "0"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl                                   # noqa: E402
import ram_map                                     # noqa: E402
from nodiskuse_probe import CASES, SPAN            # noqa: E402
from dowrite_probe import syms, where, runs        # noqa: E402

MACHINES = ("C-BIOS_MSX1_EU_REPACK_NODISK", "C-BIOS_MSX1_EU_REPACK_DISK")
KNOWN_LIVE = [(0xEAB9, 0xEAE8, "disk interrupt stack under INT_STK_TOP"),
              (0xF200, 0xF37F, "the Z80 stack's region (FN_STK_FLOOR .. $F37F)")]


def candidates():
    maps = {c: ram_map.Map(c, SPAN[0], SPAN[1] + 1) for c in ("basic", "disk")}
    covered = set()
    for m in maps.values():
        for a in m.addrs:
            w = m.width.get(a)
            if w is None:          # width-less: cover up to the next address of EITHER map
                nxt = min([x for mm in maps.values() for x in mm.addrs if x > a] + [SPAN[1] + 1])
                w = nxt - a
            covered |= set(range(a, a + w))
    for lo, hi, _ in KNOWN_LIVE:
        covered |= set(range(lo, hi + 1))
    free = sorted(set(range(SPAN[0], SPAN[1] + 1)) - covered)
    return [r for r in runs(free) if r[1] - r[0] + 1 >= 16]


def run(machine, lines, watch):
    fd, path = tempfile.mkstemp(suffix=".txt", prefix="holecheck_")
    os.close(fd)
    os.unlink(path)
    pro = ["set ::__seen [dict create]", f"set ::__wf {{{path}}}",
           "proc __wrec {} { set k \"[reg PC] [debug read ioports 0xA8] $::wp_last_address\"; "
           "if {![dict exists $::__seen $k]} { dict set ::__seen $k 1; "
           "set f [open $::__wf a]; puts $f $k; close $f } }"]
    pro += [f"debug set_watchpoint write_mem {{0x{lo:04X} 0x{hi:04X}}} {{}} {{__wrec}}"
            for lo, hi in watch]
    omsx_repl.run_cases(machine, [("direct", ["NEW"] + lines)], batch=False,
                        reset=("", "SCREEN 0"), run_gap=12.0, prologue=tuple(pro))
    if not os.path.exists(path):
        return []
    rows = [l.split() for l in open(path) if l.strip()]
    os.unlink(path)
    return [(int(p), int(s), int(a)) for p, s, a in rows]


def main():
    cand = candidates()
    total = sum(hi - lo + 1 for lo, hi in cand)
    print(f"candidate holes (>= 16 B, in neither map, not known-live): {len(cand)}, {total} B")
    for lo, hi in cand:
        print(f"   ${lo:04X}..${hi:04X} {hi - lo + 1:4d} B")
    tabs = {"main": syms(os.path.join(REPO, "build", "basic-reloc.sym")),
            "sub": syms(os.path.join(REPO, "build", "sub.sym"))}
    for machine in MACHINES:
        hits = {}
        for name, lines in CASES.items():
            for pc, a8, addr in run(machine, lines, cand):
                w = where(pc, a8, tabs)
                hits.setdefault(w, set()).add(addr)
        print(f"\n=== {machine}: {len(hits)} writer(s) into the candidates")
        for w, addrs in sorted(hits.items()):
            rs = runs(sorted(addrs))
            print(f"   {w:34s} {len(addrs):4d} B  "
                  + ", ".join(f"${lo:04X}..${hi:04X}" for lo, hi in rs[:5]))
        clean = [r for r in cand if not any(r[0] <= a <= r[1] for s in hits.values() for a in s)]
        print(f"   never written on this build: {len(clean)} run(s), "
              f"{sum(hi - lo + 1 for lo, hi in clean)} B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
