#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BIOSRUNG (3), OUTDLP's FAILURE face: the published "if failed, Device I/O error".
No printer plugged in (openMSX's default: the port reads NOT READY), OUTDLP called
DIRECTLY with A = "A", CTRL-STOP held about 3 s later -- VG-8020 against zerobas. The
readout: an error / Break line on the screen, or the registers if it returned (CF is
not shown by biosregs' stub; the [R] line says it RETURNED). Black-box: the screen and
registers.

    python3 -u scratchpad/outdlp_fail_probe.py
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import basic_probe_biosregs as B   # noqa: E402
import omsx_repl                   # noqa: E402

ROWS = {
    "outdlp_noprn": B.prog(0x014D, 0x41, after='PRINT "[C RET]"'),
    "lptout_noprn": B.prog(0x00A5, 0x41, after='PRINT "[C RET]"'),   # the base entry, for scale
    # CONTROL: does this exact hold (RUN + step + lead = RUN+6 s, for 3 s) break a
    # program at all? A plain loop must answer `Break in 10` on both.
    "loop_control": ["NEW", "10 GOTO 10", "RUN"],
    # NARROWING: zerobas's LPTOUT never returned. Does BREAKX itself see the hold, in a
    # loop of our own (lp: call $00B7 / jr nc,lp / ret)? And BASIC's own LPRINT?
    "breakx_loop": ["NEW", "10 CLEAR 200,&HCFFF:FOR I=0 TO 5:READ X:POKE &HD000+I,X:NEXT",
                    '20 DEFUSR=&HD000:Q=USR(0):PRINT "[C BRKX]"', "30 DATA 205,183,0,48,251,201",
                    "RUN"],
    "lprint_noprn": ["NEW", '10 LPRINT "A":PRINT "[C LPR]"', "RUN"],
}
CTRL_STOP = ((6, 0x02), (7, 0x10))


# hold_secs 1.0 read blank on both, LPTOUT too (outdlp_fail_run.out) -- no reading; 3.0
def stored(p):
    # 🔴 a `direct` case: the hold broke not even `10 GOTO 10` on either machine
    # (outdlp_fail_run3.out) -- stored mode, as ctrlstop_probe.py: drop NEW / RUN and
    # the line numbers (run_cases numbers 10, 20, ...; the rows' own are 10, 20, ...)
    return [ln.split(" ", 1)[1] for ln in p if ln not in ("NEW", "RUN")]


def read(machine, p):
    scr = omsx_repl.run_cases(machine, [("stored", stored(p))], batch=False,
                              reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                              holds=[CTRL_STOP], hold_lead=0.5, hold_secs=2.0)[0]   # ctrlstop_probe.py's: a clean Break
    if not scr:
        return None
    rows = [scr[i:i + 40].strip() for i in range(0, len(scr), 40)]
    keep = [x for x in rows if x.startswith("[R") or x.startswith("[C") or "rror" in x
            or "Break" in x]
    return " | ".join(keep) or "<NO OUTPUT>"


def main():
    for name in sys.argv[1:] or list(ROWS):
        got = {side: read(m, ROWS[name]) for side, m in B.MACHINES}
        verdict = "SAME" if got["VG"] == got["ZB"] else "DIVERGES"
        print(f"ROW {name:13} VG=[{got['VG']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
