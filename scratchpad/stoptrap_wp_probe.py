#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FORINT's parked STOP-trap double fire (TODO D-FORINT, 2026-10-20): WHY does one
100 ms Ctrl-STOP tap fire stop-trap-acceptance's counting handler twice on the draft and
once on 508043a2? Instrumenting the BASIC program moved the window, so this instrument does
not touch the program: openMSX write watchpoints on the STOP trap's ZTRAP entry, TRAPPEND
and the handler's counter cell, each write logged with emulated time, our own PC (zerobas
only -- the reference is never run here) and the value; plus the tap's key edges.
    python3 -u scratchpad/stoptrap_wp_probe.py [start]     (default 0.299)
"""
import os, sys, re
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import basic_probe_stop_trap as P                   # noqa: E402


def sym(name):
    for line in open(os.path.join(REPO, "build", "basic-reloc.sym"), errors="replace"):
        m = re.match(rf"{name}\s+EQU\s+0?([0-9A-Fa-f]+)H", line)
        if m:
            return int(m.group(1), 16)
    raise SystemExit(f"no symbol {name}")


def main():
    start = float(sys.argv[1]) if len(sys.argv) > 1 else 0.299
    log = os.path.join("/tmp", f"stoptrap_wp_{os.getpid()}.log")
    ztrap = sym("ZTRAP")
    stop_ent = ztrap + 1 * 3                         # ZTI_STOP * ZTRAP_ENTSZ
    trappend = sym("TRAPPEND")
    tcl = (f'set ::__wpf [open {{{log}}} w]\n'
           # log a write only when it CHANGES the cell: the edge-shadow release at
           # every statement boundary rewrites the same value thousands of times
           f'array set ::__last {{}}\n'
           f'proc __wl {{tag}} {{ set a $::wp_last_address; set v $::wp_last_value;'
           f' if {{[info exists ::__last($a)] && $::__last($a) == $v}} return;'
           f' set ::__last($a) $v;'
           f' puts $::__wpf "[format %.6f [machine_info time]] $tag'
           f' pc=[format %04X [reg pc]] a=[format %04X $a] v=[format %02X $v]"; flush $::__wpf }}\n'
           f'debug set_watchpoint write_mem {{{stop_ent:#x} {stop_ent + 2:#x}}} {{}} {{__wl STOP}}\n'
           f'debug set_watchpoint write_mem {trappend:#x} {{}} {{__wl PEND}}\n'
           f'debug set_watchpoint write_mem 0xD000 {{}} {{__wl FLAG}}\n')
    orig = P.key_proc
    P.key_proc = lambda: orig() + "\n" + tcl
    r = P.run(P.ZB_MACHINE, P.CPROG, [(start, start + 0.10)])
    print(f"start {start}: result {None if r is None else {k: r.get(k) for k in ('flag', 'ran', 'done')}}")
    try:
        rows = open(log).read().splitlines()
    except OSError:
        rows = ["(no watchpoint log)"]
    rows = [r for r in rows if float(r.split()[0]) > 10.0]   # past boot's RAM test
    for row in rows[:200]:
        print("  " + row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
