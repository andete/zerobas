#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Does the reference keep PLAY's `X<var>;` return points on the BASIC (Z80) stack?

Joost's question, 2026-09-24. Black-box, on the VG-8020: a window the program
opens/closes around one PLAY statement (POKE &HE000,201/202), a write watchpoint
over $8000..$FFFF that samples SP on every write, for nesting depth 0..3, and a
self-recursive `A$="XA$;"` under ON ERROR (does it end in ERR 7 Out of memory,
another error, or never?).

  depth-per-level constant and > 0  -> each level pushes onto the stack
  depth-independent SP              -> the return points live elsewhere

Clean room: SP and RAM addresses at program-written marks; no ROM byte read.
"""
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))

REF = "Philips_VG_8020"
MARK = 0xE000
N = 'O7L64C'
SYNC = ['5 X7=TIME', '6 IF TIME=X7 THEN 6']
W = '30 POKE&HE000,201:PLAY"XA$;":POKE&HE000,202'
# ⏱ each window opens just after a TIME tick, so an interrupt's own pushes
# (the first run's d1 < d0 noise) do not land inside a short PLAY
CASES = [
    ("d0", SYNC + [f'30 POKE&HE000,201:PLAY"{N}":POKE&HE000,202']),
    ("d1", [f'10 A$="{N}"'] + SYNC + [W]),
    ("d2", [f'10 B$="{N}":A$="XB$;"'] + SYNC + [W]),
    ("d3", [f'10 C$="{N}":B$="XC$;":A$="XB$;"'] + SYNC + [W]),
    ("d4", [f'10 D$="{N}":C$="XD$;"', '12 B$="XC$;":A$="XB$;"'] + SYNC + [W]),
    ("d5", [f'10 E$="{N}":D$="XE$;"', '12 C$="XD$;":B$="XC$;"', '14 A$="XB$;"'] + SYNC + [W]),
    ("d6", [f'10 F$="{N}":E$="XF$;"', '12 D$="XE$;":C$="XD$;"',
            '14 B$="XC$;":A$="XB$;"'] + SYNC + [W]),
    ("rec", ['10 ON ERROR GOTO 50', '20 A$="XA$;"',
             '30 POKE&HE000,201:PLAY"XA$;":POKE&HE000,202',
             '40 PRINT"[NOERR]":END',
             '50 POKE&HE000,202:PRINT"[E";ERR;ERL;"]":RESUME 60', '60 END']),
]

TCL = r'''
set ::w 0
set ::open 0
array set ::sp0 {}
array set ::spmin {}
debug set_watchpoint write_mem @MARK@ {} {
    if {$::wp_last_value == 201} {
        incr ::w ; set ::open 1
        set ::sp0($::w) [reg SP] ; set ::spmin($::w) [reg SP]
    } elseif {$::wp_last_value == 202} { set ::open 0 }
}
debug set_watchpoint write_mem {0x8000 0xFFFF} {} {
    if {!$::open} { return }
    set sp [reg SP]
    if {$sp < $::spmin($::w)} { set ::spmin($::w) $sp }
}
proc __dump {} {
    set f [open {@OUT@} w]
    foreach k [array names ::sp0] { puts $f "S $k $::sp0($k) $::spmin($k)" }
    close $f
    after time 1 __dump
}
after time 1 __dump
'''


def run(key, lines):
    import omsx_repl
    fd, out = tempfile.mkstemp(prefix="playxstack-")
    os.close(fd)
    t = TCL.replace("@MARK@", str(MARK)).replace("@OUT@", out)
    scr = omsx_repl.run_cases(REF, [("direct", ["NEW"] + lines + ["RUN"])],
                              batch=False, reset=("CLS",), boot=8.0,
                              capture="screen", prologue=(t,))
    got = {}
    for ln in open(out):
        p = ln.split()
        if len(p) == 4:
            got[int(p[1])] = (int(p[2]), int(p[3]))
    os.unlink(out)
    return got, (scr[0] if scr else None)


def main():
    import omsx_repl
    for key, lines in CASES:
        got, scr = run(key, lines)
        tail = omsx_repl.screen_tail(scr, "RUN") if scr else None
        if not got:
            print(f"{key:4} NO WINDOW  screen: {tail!r}")
            continue
        sp0, spmin = got[min(got)]
        print(f"{key:4} SP at window {sp0:04X}  lowest {spmin:04X}  "
              f"depth {sp0 - spmin:5d} B   screen: {tail!r}")
        if key == "rec" and scr:
            rows = [scr[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].rstrip()
                    for r in range(omsx_repl.ROWS)]
            print("     full screen: " + " | ".join(r for r in rows if r.strip()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
