#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""RAM-usage (TIER 4, Joost 2026-10-12: "our own buffers, test what buffers the
reference uses, and see if we can meet the same"): which of the reference's
published work-area BUFFERS does each kind of operation write, on the VG-8020
-- and does zerobas write them at all?

zerobas keeps its own buffers in its workspace ($E000..$F37F: TOKBUF 576 B,
STRSCR 256, the PRINT USING pair, ZTRAP ...) while docs/ram-map.md claims
NOTHING in the reference's KBUF / BUF ($F41F..$F65F), PARM1 / PARM2
($F6E8..$F7B3) or TRPTBL ($FC4C..$FC99). If the reference does its work there
and zerobas could too, zerobas's own copies are the RAM it uses beyond the
reference (the diskless gap, ruled to be closed).

METHOD. One boot per case per machine. A Tcl prologue arms a write watchpoint
over the work area's DATA span and records every address written (never a
value, never the writer's PC); each case's set MINUS the control case's set is
what that operation writes. Line entry is part of every case (the harness
types the program), so the control types a short line too, and the `longline`
case is how line entry itself is measured.

🔴 CLEAN ROOM. The watched span is $F39A..$FD99: it EXCLUDES the reference's
RAM-resident code -- the slot routines below $F39A (RDPRIM/WRPRIM/CLPRIM) and the
hook table from $FD9A up -- so no write into code is even recorded, and no
byte of RAM is read at all (only addresses that are written).

FIRST RUN: every case 2560 / 2560 addresses on both machines -- the watchpoint
was armed at power-on and recorded the BIOS clearing the work area. It is armed
after boot now, and a control covering half the span is refused.

Prediction: on the VG-8020, line entry writes KBUF; INPUT / LINE INPUT write
BUF; DEF FN writes PARM1 (and PARM2 for the string form); the traps write
TRPTBL; PRINT USING and number printing write FBUFFR. On zerobas NONE of
KBUF / BUF / PARM1 / PARM2 / TRPTBL is written by any case.
"""
import os, re, sys, tempfile
os.environ["ZEROBAS_REFCACHE"] = "0"     # the prologue's file is a side effect: never cache
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")
SPAN = (0xF39A, 0xFD99)
NAMES = [  # published MSX1 work-area buffers (MSX2 Technical Handbook's map)
    (0xF41F, 0xF55C, "KBUF"), (0xF55D, 0xF55D, "BUFMIN"), (0xF55E, 0xF65F, "BUF"),
    (0xF67A, 0xF697, "TEMPST"), (0xF6E8, 0xF74B, "PARM1"), (0xF750, 0xF7B3, "PARM2"),
    (0xF7C5, 0xF7EF, "FBUFFR"), (0xF7F6, 0xF805, "DAC"), (0xF847, 0xF856, "ARG"),
    (0xF866, 0xF870, "FILNAM"), (0xF871, 0xF87B, "FILNM2"), (0xFC4C, 0xFC99, "TRPTBL"),
    (0xF3DF, 0xF3E6, "RG0SAV.."), (0xF3B3, 0xF3BE, "screen tables"),
]
LONG = "10 A=1:B=2:C=3:D=4:E=5:F=6:G=7:H=8:I=9:J=10:K=11:L=12:M=13:N=14:O=15:P=16:Q=17:R=18:S=19:T=20:U=21:V=22"
CASES = {
    "control": ["10 END", "RUN"],
    "longline": [LONG, "RUN"],
    "input": ["10 INPUT A$:END", "RUN", "HELLO WORLD"],
    "linput": ["10 LINE INPUT A$:END", "RUN", "HELLO, WORLD"],
    "deffn": ["10 DEF FNA(X,Y)=X*Y+1:B=FNA(2,3):END", "RUN"],
    "deffns": ['10 DEF FNB$(A$,B$)=A$+B$:C$=FNB$("Q","R"):END', "RUN"],
    "traps": ["10 ON INTERVAL=1 GOSUB 100:INTERVAL ON", "20 ON KEY GOSUB 100:KEY(1) ON",
              "30 ON STOP GOSUB 100:STOP ON", "40 FOR I=1 TO 200:NEXT:END", "100 RETURN", "RUN"],
    "using": ['10 PRINT USING "###.##";3.14159:END', "RUN"],
    "numfmt": ["10 PRINT 1/3;12345678;-1.5E+20:END", "RUN"],
    "strings": ['10 A$=STRING$(100,"X")+"Y":B$=MID$(A$,5,10):C$=A$+B$:END', "RUN"],
    "val": ['10 A=VAL("123.5")+VAL("&H1F"):END', "RUN"],
    "list": ["10 REM HELLO", "20 PRINT 1", "LIST"],
}


def name_of(a):
    for lo, hi, n in NAMES:
        if lo <= a <= hi:
            return n
    return f"${a:04X}"


def ranges(addrs):
    out, cur = [], None
    for a in sorted(addrs):
        if cur and a == cur[1] + 1:
            cur[1] = a
        else:
            cur = [a, a]
            out.append(cur)
    return out


def run(machine, lines):
    fd, path = tempfile.mkstemp(suffix=".txt", prefix="refwork_")
    os.close(fd)
    os.unlink(path)
    pro = (
        "set ::__wseen [dict create]",
        f"set ::__wf {{{path}}}",
        "proc __wrec {} { set a $::wp_last_address; "
        "if {![dict exists $::__wseen $a]} { dict set ::__wseen $a 1; "
        "set f [open $::__wf a]; puts $f $a; close $f } }",
        # ARMED AFTER BOOT: the BIOS cold start clears the whole work area, so
        # a watchpoint armed at power-on saw all 2560 addresses in EVERY case
        # (the first run). The harness types from 8.0 s; boot is done well
        # before 7.5 s on both machines.
        f"after time 7.5 {{debug set_watchpoint write_mem {{0x{SPAN[0]:04X} 0x{SPAN[1]:04X}}} {{}} {{__wrec}}}}",
    )
    omsx_repl.run_cases(machine, [("direct", ["NEW"] + lines)], batch=False,
                        reset=("", "SCREEN 0"), run_gap=12.0, prologue=pro)
    if not os.path.exists(path):
        return None
    addrs = {int(l) for l in open(path) if l.strip()}
    os.unlink(path)
    return addrs


def main():
    res = {m: {} for m in MACHINES}
    for m in MACHINES:
        for name, lines in CASES.items():
            res[m][name] = run(m, lines)
            got = res[m][name]
            print(f"{m[:12]:12s} {name:9s} {'NONE' if got is None else len(got):>5} addresses",
                  flush=True)
    print()
    span = SPAN[1] - SPAN[0] + 1
    for m in MACHINES:
        ctl = res[m]["control"]
        if ctl is None or len(ctl) > span // 2:
            print(f"INSTRUMENT FAULT: {m}'s control wrote "
                  f"{'nothing readable' if ctl is None else len(ctl)} of {span} addresses -- "
                  f"the watchpoint saw the boot's clear, not the cases; no table")
            return 2
    for m in MACHINES:
        ctl = res[m]["control"] or set()
        print(f"=== {m}: written beyond the control (address ranges, by published name)")
        for name in CASES:
            if name == "control" or res[m][name] is None:
                continue
            extra = res[m][name] - ctl
            byname = {}
            for lo, hi in ranges(extra):
                byname.setdefault(name_of(lo), []).append((lo, hi))
            parts = [f"{n} " + ",".join(f"${lo:04X}-${hi:04X}" if hi > lo else f"${lo:04X}"
                                        for lo, hi in rs) for n, rs in sorted(byname.items())]
            print(f"  {name:9s} {len(extra):4d} B: " + ("; ".join(parts) if parts else "--"))
        print(f"  control   {len(ctl):4d} B: " + "; ".join(
            sorted({name_of(lo) for lo, _ in ranges(ctl)})))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
