#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""RAM order step (3): WHO still writes STRSCR?

strscr_probe.out: concatenation, STR$, MID$ and STRING$ build their results
straight in the string space on BOTH machines -- zerobas writes nothing in
STRSCR for them. STRSCR still has 129 references, so this names its writers
over a broad corpus. ZEROBAS ONLY (our own code; writers by PC).

Prediction (2026-10-14): a handful of producers -- INPUT / LINE INPUT, READ of
string DATA, PRINT USING, KEY / function-key strings, HEX$ / OCT$ / BIN$.
"""
import os, re, sys, tempfile
os.environ.setdefault("ZEROBAS_REFCACHE", "0")
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(_R, "probes", "lib"), os.path.join(_R, "probes", "basic")]
import omsx_repl                                   # noqa: E402
from basic_probe_floorcensus import syms, where   # noqa: E402

MACHINE = "C-BIOS_MSX1_EU_REPACK_NODISK"
CASES = {
    "funcs": ['10 A$=HEX$(255)+OCT$(8)+BIN$(5)+CHR$(65)+SPACE$(3)+LEFT$("ABCD",2)',
              '20 B$=RIGHT$("ABCD",2)+STR$(VAL("12"))+INKEY$:C$=LEFT$(A$,1)'],
    "read": ['10 READ A$,B$,C:READ D$', '20 DATA "HELLO",WORLD,12,"A,B"'],
    "using": ['10 PRINT USING "###.## &   &";3.14159;"ABCDEF"',
              '20 PRINT USING "\\  \\ !";"HELLO";"Q"'],
    "key": ['10 KEY 1,"HELLO"+CHR$(13):KEY 2,STRING$(10,65):A$=""'],
    "input": ['10 INPUT A$,B', '20 LINE INPUT C$', '30 A$=INPUT$(3)'],
}
TYPE_AFTER = {"input": ["XYZ,5", "A LINE", "QQQ"]}


def run(name, lines, lo, hi):
    fd, path = tempfile.mkstemp(suffix=".txt", prefix="strscr_")
    os.close(fd)
    os.unlink(path)
    pro = ("set ::__seen [dict create]", f"set ::__wf {{{path}}}",
           "proc __wrec {} { set k \"[reg PC] [debug read ioports 0xA8] $::wp_last_address\"; "
           "if {![dict exists $::__seen $k]} { dict set ::__seen $k 1; "
           "set f [open $::__wf a]; puts $f $k; close $f } }",
           f"after time 7 {{ debug set_watchpoint write_mem {{0x{lo:04X} 0x{hi:04X}}} {{}} {{__wrec}} }}")
    omsx_repl.run_cases(MACHINE, [("direct", ["NEW"] + lines + ["RUN"] + TYPE_AFTER.get(name, []))],
                        batch=False, reset=("", "SCREEN 0"), run_gap=12.0, prologue=pro)
    rows = [l.split() for l in open(path) if l.strip()] if os.path.exists(path) else []
    if os.path.exists(path):
        os.unlink(path)
    return [(int(p), int(s), int(a)) for p, s, a in rows]


def main():
    tab = {"main": syms(os.path.join(_R, "build", "basic-reloc.sym")),
           "sub": syms(os.path.join(_R, "build", "sub.sym"))}
    lo = next(a for a, n in tab["main"] if n == "STRSCR")
    hi = lo + 0xFF
    print(f"STRSCR ${lo:04X}..${hi:04X}")
    for name, lines in CASES.items():
        by = {}
        for p, s, a in run(name, lines, lo, hi):
            by.setdefault(where(p, s, tab).split("+")[0], set()).add(a)
        print(f"{name:6s} " + ("; ".join(f"{w} {len(v)} B" for w, v in sorted(by.items())) or "nothing"),
              flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
