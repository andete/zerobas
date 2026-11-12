#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""STRTMS step (1)(a): is PSG R13 (the envelope shape -- a write restarts the envelope)
written on EVERY envelope note, or only when S / M change? The packet carries no
"S changed" flag (playq_run*.out), so the answer decides the servicer. An openMSX
watchpoint logs every PSG register select ($A0) and every data write ($A1) with R11..R13
selected, with its value and emulated time, during `PLAY "<mml>"`. Black-box: I/O port
traffic only.

    python3 -u scratchpad/psgenv_probe.py [ROW ...]
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402

MACHS = (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK"))
ROWS = {
    "s0ccc":   "S0M5000CCC",
    "s8cde":   "S8M300CDE",
    "s0cs0c":  "S0M5000CS0C",
    "vcs0c":   "V10CS0M5000CC",
    # ROUND 2: R8 too -- the amplitude an envelope note writes (V5, then S3)
    "v5s3c":   "V5S3C",
}
LO = {"v5s3c": 8}


def run(machine, mml, lo=11):
    log = probe_tmp.tmp(f"psgenv_{machine[:6]}.log")
    if os.path.exists(log):
        os.remove(log)
    pro = (f"set ::pl [open {{{log}}} w]",
           "fconfigure $::pl -buffering line",
           "set ::preg 0",
           "debug set_watchpoint write_io 0xA0 {} {set ::preg $::wp_last_value}",
           "debug set_watchpoint write_io 0xA1 {} "
           f"{{if {{$::preg >= {lo} && $::preg <= 13}} "
           "{puts $::pl \"$::preg $::wp_last_value [machine_info time]\"}}")
    case = ["NEW", f'10 PLAY "{mml}":T=TIME', "20 IF TIME-T<250 THEN 20",
            '30 PRINT "[D]"', "RUN"]
    raw = omsx_repl.run_cases(machine, [("direct", case)], batch=False,
                              reset=("", "SCREEN 0"), prologue=pro, run_gap=8.0)[0] or ""
    ev = []
    for ln in open(log):
        p = ln.split()
        if len(p) == 3:
            ev.append((int(p[0]), int(p[1]), float(p[2])))
    if not ev:
        return f"<NO WRITES>{' [D]' if '[D]' in raw else ' (no [D])'}"
    t0 = ev[0][2]
    return " ".join(f"R{r}={v:X}@{t - t0:.2f}" for r, v, t in ev)


def main():
    for name in sys.argv[1:] or list(ROWS):
        for side, m in MACHS:
            print(f"ROW {name:7} {side} {run(m, ROWS[name], LO.get(name, 11))}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
