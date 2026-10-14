#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO: which published work-area cells does a TAPE `BLOAD ...,R` write, on
the VG-8020 -- the reference's home for the state zerobas keeps in its own
workspace ($E98A..$F37F: CURPTR / ENDPTR / EXECPTR, the tape header buffers,
FN_RESUME ...), which tape loaders overwrite (TODO D-WSZERO).

refwork_probe.py's method, with a cassette: a write watchpoint over the published
DATA span $F39A..$FD99 (it excludes the reference's RAM-resident code), armed
after boot, records ADDRESSES only; each case minus the control. Our own
synthetic tape: one binary "T", 16 bytes at &HC000, its code a bare `ret`.

Prediction (2026-10-14): on the VG-8020 the BLOAD cases write FILNAM (the name
searched for) and a handful of cells beside it, nothing large; zerobas writes
FILNAM nowhere (its name buffer is in its own workspace).
"""
import os, sys, tempfile
os.environ["ZEROBAS_REFCACHE"] = "0"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(REPO, "probes", "lib"), os.path.join(REPO, "scratchpad")]
import omsx_repl                                   # noqa: E402
import refwork_probe as rw                         # noqa: E402
from cas_encode import build_cas                   # noqa: E402

CASES = {
    "control": ["10 END", "RUN"],
    "bloadr": ['BLOAD"CAS:",R'],
    "bloadprog": ['10 CLEAR 100,&HC000:BLOAD"CAS:",R:PRINT 1', "RUN"],
}


def run(machine, lines, tape):
    fd, path = tempfile.mkstemp(suffix=".txt", prefix="refwork_bl_")
    os.close(fd)
    os.unlink(path)
    pro = (
        "set ::__wseen [dict create]",
        f"set ::__wf {{{path}}}",
        "proc __wrec {} { set a $::wp_last_address; "
        "if {![dict exists $::__wseen $a]} { dict set ::__wseen $a 1; "
        "set f [open $::__wf a]; puts $f $a; close $f } }",
        f"after time 7.5 {{debug set_watchpoint write_mem {{0x{rw.SPAN[0]:04X} 0x{rw.SPAN[1]:04X}}} {{}} {{__wrec}}}}",
    )
    omsx_repl.run_cases(machine, [("direct", ["NEW"] + lines)], batch=False,
                        reset=("", "SCREEN 0"), run_gap=30.0, prologue=pro, cassette=tape)
    if not os.path.exists(path):
        return None
    addrs = {int(l) for l in open(path) if l.strip()}
    os.unlink(path)
    return addrs


def main():
    tape = os.path.join(tempfile.mkdtemp(prefix="refwork_bl_"), "t.cas")
    open(tape, "wb").write(build_cas("T", 0xC000, 0xC000, bytes([0xC9]) + bytes(15)))
    res = {m: {n: run(m, l, tape) for n, l in CASES.items()} for m in rw.MACHINES}
    span = rw.SPAN[1] - rw.SPAN[0] + 1
    for m in rw.MACHINES:
        ctl = res[m]["control"]
        if ctl is None or len(ctl) > span // 2:
            print(f"INSTRUMENT FAULT: {m}'s control: {'nothing' if ctl is None else len(ctl)} addresses")
            return 2
    for m in rw.MACHINES:
        ctl = res[m]["control"]
        print(f"=== {m}")
        for n in CASES:
            if n == "control" or res[m][n] is None:
                print(f"  {n}: {'no reading' if n != 'control' else ''}")
                continue
            extra = res[m][n] - ctl
            parts = []
            for lo, hi in rw.ranges(extra):
                parts.append(f"{rw.name_of(lo)} " + (f"${lo:04X}-${hi:04X}" if hi > lo else f"${lo:04X}"))
            print(f"  {n:10s} {len(extra):4d} B: " + "; ".join(parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
