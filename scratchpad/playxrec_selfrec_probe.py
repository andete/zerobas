#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""PLAY X self-recursion on the VG-8020: SP logged once per emulated second
inside a program-opened window, and the ON ERROR handler's ERR/ERL read off the
screen (run_gap, NOT cap_gap -- the capture must wait for the error). Clean room:
SP and RAM addresses only."""
import os, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl
TCL = r'''
set ::open 0
set ::spmin 65535
set ::log {}
debug set_watchpoint write_mem 0xE000 {} {
    if {$::wp_last_value == 201} { set ::open 1 ; set ::t0 [machine_info time] ; __tick }
    if {$::wp_last_value == 202} { set ::open 0 ; lappend ::log "CLOSE [expr {[machine_info time]-$::t0}]" }
}
debug set_watchpoint write_mem {0x8000 0xFFFF} {} {
    if {!$::open} { return }
    set sp [reg SP]
    if {$sp < $::spmin} { set ::spmin $sp }
}
proc __tick {} {
    if {$::open} { lappend ::log "T [format %.1f [expr {[machine_info time]-$::t0}]] [format %04X $::spmin] [format %04X [reg SP]]" }
    after time 1 __tick
}
proc __dump {} {
    set f [open {@OUT@} w]
    foreach l $::log { puts $f $l }
    close $f
    after time 1 __dump
}
after time 1 __dump
'''
fd, out = tempfile.mkstemp(); os.close(fd)
lines = ['NEW', '10 ON ERROR GOTO 50', '20 A$="XA$;"',
         '30 POKE&HE000,201:PLAY"XA$;":POKE&HE000,202', '40 PRINT"[NOERR]":END',
         '50 POKE&HE000,202:PRINT"[E";ERR;ERL;"]":RESUME 60', '60 END', 'RUN']
MACH = sys.argv[1] if len(sys.argv) > 1 else "Philips_VG_8020"   # zerobas: C-BIOS_MSX1_EU_REPACK_DISK
scr = omsx_repl.run_cases(MACH, [("direct", lines)], batch=False,
                          reset=("CLS",), boot=8.0, capture="screen",
                          run_gap=20.0, timeout=300.0,
                          prologue=(TCL.replace("@OUT@", out),))
print(open(out).read())
rows = [scr[0][r*omsx_repl.COLS:(r+1)*omsx_repl.COLS].rstrip() for r in range(omsx_repl.ROWS)] if scr and scr[0] else []
print("screen:", " | ".join(r for r in rows if r.strip()))
