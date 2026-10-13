#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""RAM order step (2), the claim to verify before removing GFX_DBUF: does
resolving a DRAW substitution (`XA$;`, `=A;`) ALLOCATE anything on zerobas?

GFX_DBUF exists because "the resident's eval between round trips can reuse the
temp-string pool a DRAW argument lives in". If a substitution only LOOKS A
VARIABLE UP (the reference's rule, which zerobas now enforces -- D-DRAWSUBVAR),
no string moves during a DRAW and the string can be read in place.

ZEROBAS ONLY -- our own code, so writers are named by PC against our sym files.
A write watch over $8000..$F37F, bracketed by program-written marks ($C000 and
$C001: the watch keeps one record per (PC, address), so one address would lose
the second mark). Two programs draw the SAME figure:

  subst    DRAW "BM50,50XA$;R=A;XB$;"   (A$="R5", B$="D5", A=3)
  literal  DRAW "BM50,50R5R3D5"

Writers present in `subst` and absent from `literal` are what resolving a
substitution costs. Prediction (2026-10-13): only the resident's eval scratch,
DRAW's own GFX_* cells and the stack -- no heap allocation, no GC.
"""
import os, sys, tempfile
os.environ.setdefault("ZEROBAS_REFCACHE", "0")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(REPO, "probes", "lib"), os.path.join(REPO, "scratchpad")]
import omsx_repl                                   # noqa: E402
from dowrite_probe import syms, where, runs        # noqa: E402

MACHINE = "C-BIOS_MSX1_EU_REPACK_NODISK"
PROGS = {
    "subst": ['A$="R5":B$="D5":A=3:SCREEN 2',
              'POKE &HC000,1:DRAW "BM50,50XA$;R=A;XB$;":POKE &HC001,2', "SCREEN 0"],
    "literal": ['A$="R5":B$="D5":A=3:SCREEN 2',
                'POKE &HC000,1:DRAW "BM50,50R5R3D5":POKE &HC001,2', "SCREEN 0"],
}


def run(lines):
    fd, path = tempfile.mkstemp(suffix=".txt", prefix="drawalloc_")
    os.close(fd)
    os.unlink(path)
    pro = ("set ::__seen [dict create]", f"set ::__wf {{{path}}}",
           "proc __wrec {} { set k \"[reg PC] [debug read ioports 0xA8] $::wp_last_address\"; "
           "if {![dict exists $::__seen $k]} { dict set ::__seen $k 1; "
           "set f [open $::__wf a]; puts $f \"$k [machine_info time]\"; close $f } }",
           "after time 6 { debug set_watchpoint write_mem {0x8000 0xF37F} {} {__wrec} }")
    omsx_repl.run_cases(MACHINE, [("stored", lines)], batch=False, reset=("", "SCREEN 0"),
                        run_gap=10.0, prologue=pro)
    rows = [l.split() for l in open(path) if l.strip()] if os.path.exists(path) else []
    if os.path.exists(path):
        os.unlink(path)
    return [(int(p), int(s), int(a), float(t)) for p, s, a, t in rows]


def window(got):
    t0 = [t for p, s, a, t in got if a == 0xC000]
    t1 = [t for p, s, a, t in got if a == 0xC001]
    if not t0 or not t1:
        return None
    return [(p, s, a) for p, s, a, t in got if t0[-1] < t < t1[-1]]


def main():
    tabs = {"main": syms(os.path.join(REPO, "build", "basic-reloc.sym")),
            "sub": syms(os.path.join(REPO, "build", "sub.sym"))}
    seen = {}
    for name, lines in PROGS.items():
        w = window(run(lines))
        if w is None:
            print(f"{name}: INSTRUMENT FAULT -- no mark pair")
            return 2
        by = {}
        for p, s, a in w:
            by.setdefault(where(p, s, tabs), set()).add(a)
        seen[name] = by
        print(f"{name:8s} {len(w):4d} distinct writes by {len(by)} writer(s)", flush=True)
    only = {k: v for k, v in seen["subst"].items() if k not in seen["literal"]}
    print(f"\nWRITERS IN `subst` ONLY: {len(only)}")
    for k, v in sorted(only.items(), key=lambda kv: min(kv[1])):
        rs = runs(sorted(v))
        print(f"  {k:34s} {len(v):4d} B  " + ", ".join(f"${lo:04X}..${hi:04X}" for lo, hi in rs[:5])
              + (" ..." if len(rs) > 5 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
