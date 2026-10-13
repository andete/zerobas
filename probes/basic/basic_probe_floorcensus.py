#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""floorcensus-acceptance (D-FLOORCENSUS, 2026-10-13): who WRITES the diskless floor?

On a diskless machine [TXTMAX, TXTMAX_NODISK) is PROGRAM RAM: the string space,
the channel blocks and the Z80 stack live there. Disk BASIC's cells and buffers
are declared there too, tagged DISK-ONLY, and `make ram-map-check` verifies the
DECLARATIONS -- but a tag is a claim about WRITERS, and nothing checked it:
D-FLOORREC shipped (t_fch_load copied every channel's record into FSECTOR_BUF,
256 B of program RAM per channel switch) through exactly that gap.

ZEROBAS ONLY -- our own code, so writers are named by PC against our sym files.
A write watch on the floor (bounds read from build/basic-reloc.sym), armed after
boot, records PC, slot register, address and SP for every distinct (PC, address)
during a corpus of programs. A write is a STACK write when it lands within a few
bytes of SP (pushes, calls, interrupt entry); every other writer must be one of
the PROGRAM-RAM MANAGERS in ALLOW (the string heap and its GC, the channel blocks
and their headers, the tape buffer). Anything else is a writer of a disk-only
cell on a machine without a disk: a FAIL, named.

    python3 -u probes/basic/basic_probe_floorcensus.py [--list]

`--list` prints every non-stack writer with its address runs (the allowlist's
evidence). Exit 0 clean, 1 on an unlisted writer, 2 on an instrument fault.
"""
import os, re, sys, tempfile
os.environ.setdefault("ZEROBAS_REFCACHE", "0")
_R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path[:0] = [os.path.join(_R, "probes", "lib"), os.path.join(_R, "probes", "basic")]
import omsx_repl                                   # noqa: E402

MACHINE = "C-BIOS_MSX1_EU_REPACK_NODISK"
STACK_WINDOW = (-4, 24)       # a write at SP-4 .. SP+23 is the stack's
# Program-RAM managers: routine-name PREFIXES (the label before any `+off`).
ALLOW = ("sacc", "sate", "str_body", "sfs_", "sg_", "sh_", "she_", "shf_", "heap_",
         "strheap",                          # the string heap and its GC
         "t_fch_hdr", "fhd_", "fch_", "cas_", "clr_",   # channel blocks, tape buffer
         "ef_")                              # FOR frames: the control-frame pool, which
                                             # shares program RAM with the stack

CASES = {
    "strings": ["10 CLEAR 400:A$=\"\"", "20 FOR I=1 TO 150:A$=STR$(I)+LEFT$(A$,30):NEXT",
                "30 B$=STRING$(100,65)+A$:C$=MID$(B$,3,40)", "40 PRINT LEN(A$);LEN(B$)"],
    "grp": ["10 CLEAR 1000:ON ERROR GOTO 900", "20 SCREEN 2:OPEN\"GRP:\"FOR OUTPUT AS #1",
            "30 PSET(8,8),4:PRINT #1,\"HELLO\";12;\"A\",\"B\"", "40 CLOSE #1:OPEN\"GRP:\"AS #1",
            "50 PRINT #1,\"X\":E=EOF(1):E=LOC(1):E=LOF(1):CLOSE:SCREEN 0:END",
            "900 RESUME NEXT"],
    "crt": ["10 MAXFILES=3:OPEN\"CRT:\"FOR OUTPUT AS #1:OPEN\"GRP:\"FOR OUTPUT AS #2",
            "20 PRINT #1,\"ONE\":PRINT #1,\"TWO\":CLOSE #1",
            "30 OPEN\"CRT:\"FOR OUTPUT AS #3:PRINT #3,\"THREE\":CLOSE"],
    # opengrp-acceptance's own `errors` program, verbatim: the channel paths (EOF,
    # LOC, LOF, INPUT on a GRP: channel, under errors) that reach t_fch_load. The
    # first corpus lacked it and the negative control (D-FLOORREC's cut) read
    # GREEN -- the gate could not have caught the bug it was built for.
    "grp_errors": None,
    "draw": ["10 SCREEN 2:A$=\"R5D5L5U5\":DRAW\"BM50,50S8XA$;\":CIRCLE(100,100),20",
             "20 LINE(0,0)-(30,30),15,B:PAINT(10,10),4,15", "30 PUT SPRITE 0,(10,10),15,0",
             "40 PLAY\"T255L64CDE\":SCREEN 0"],
}


def sym(name):
    for ln in open(os.path.join(_R, "build", "basic-reloc.sym")):
        m = re.match(rf"^{name}\s+EQU\s+0?([0-9A-Fa-f]+)H", ln)
        if m:
            return int(m.group(1), 16)
    raise SystemExit(f"{name} is not in build/basic-reloc.sym -- build first")


def syms(path):
    out = []
    for ln in open(path):
        m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s+EQU\s+0?([0-9A-Fa-f]+)H", ln)
        if m:
            out.append((int(m.group(2), 16), m.group(1)))
    return sorted(out)


def where(pc, a8, tabs):
    prim = a8 & 3 if pc < 0x4000 else (a8 >> 2) & 3
    tab = tabs["main"] if prim == 0 else tabs["sub"]
    lo = [p for p in tab if p[0] <= pc]
    if prim == 0 and (not lo or pc < tabs["main"][0][0]):
        return f"C-BIOS?:{pc:04X}"
    if not lo:
        return f"?:{pc:04X}"
    a, n = lo[-1]
    return f"{'main' if prim == 0 else 'sub'}:{n}+{pc - a}"


def run(lines, lo, hi):
    fd, path = tempfile.mkstemp(suffix=".txt", prefix="floorcensus_")
    os.close(fd)
    os.unlink(path)
    pro = ("set ::__seen [dict create]", f"set ::__wf {{{path}}}",
           "proc __wrec {} { set k \"[reg PC] [debug read ioports 0xA8] $::wp_last_address\"; "
           "if {![dict exists $::__seen $k]} { dict set ::__seen $k 1; "
           "set f [open $::__wf a]; puts $f \"$k [reg SP]\"; close $f } }",
           f"after time 7 {{ debug set_watchpoint write_mem {{0x{lo:04X} 0x{hi - 1:04X}}} {{}} {{__wrec}} }}")
    omsx_repl.run_cases(MACHINE, [("direct", ["NEW"] + lines + ["RUN"])], batch=False,
                        reset=("", "SCREEN 0"), run_gap=25.0, prologue=pro)
    if not os.path.exists(path):
        return None
    rows = [l.split() for l in open(path) if l.strip()]
    os.unlink(path)
    return [(int(p), int(s), int(a), int(sp)) for p, s, a, sp in rows]


def runs_of(addrs):
    out, cur = [], None
    for a in sorted(addrs):
        if cur and a == cur[1] + 1:
            cur[1] = a
        else:
            cur = [a, a]
            out.append(cur)
    return out


def main():
    import basic_probe_opengrp
    CASES["grp_errors"] = basic_probe_opengrp.CASES["errors"]
    lo, hi = sym("TXTMAX"), sym("TXTMAX_NODISK")
    tabs = {"main": syms(os.path.join(_R, "build", "basic-reloc.sym")),
            "sub": syms(os.path.join(_R, "build", "sub.sym"))}
    print(f"floor [${lo:04X}, ${hi:04X}) on {MACHINE}")
    writers, bad = {}, {}
    for name, lines in CASES.items():
        got = run(lines, lo, hi)
        if got is None:
            print(f"{name}: INSTRUMENT FAULT -- no watch record")
            return 2
        nstack = 0
        for pc, a8, addr, sp in got:
            if STACK_WINDOW[0] <= addr - sp < STACK_WINDOW[1]:
                nstack += 1
                continue
            w = where(pc, a8, tabs)
            label = w.split(":", 1)[1].split("+")[0] if ":" in w else w
            writers.setdefault(w, set()).add(addr)
            if not label.startswith(ALLOW):
                bad.setdefault(w, set()).add(addr)
        print(f"{name:8s} {len(got):5d} distinct writes, {nstack} on the stack", flush=True)
    if "--list" in sys.argv:
        for w, ad in sorted(writers.items()):
            rs = runs_of(ad)
            print(f"   {w:34s} {len(ad):4d} B  " + ", ".join(f"${a:04X}..${b:04X}" for a, b in rs[:4]))
    for w, ad in sorted(bad.items()):
        rs = runs_of(ad)
        print(f"UNLISTED WRITER {w:34s} {len(ad):4d} B  "
              + ", ".join(f"${a:04X}..${b:04X}" for a, b in rs[:4]))
    print("PASS: every non-stack writer of the floor is a program-RAM manager" if not bad
          else f"FAIL: {len(bad)} writer(s) of the diskless floor outside the program-RAM managers")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
