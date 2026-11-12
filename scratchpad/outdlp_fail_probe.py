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
    # D-BRKLATCH: after LPTOUT's CTRL-STOP return, what is INTFLG -- at once, and ten
    # frames later? (ld a,"A" / call $00A5 / ld a,(INTFLG) / ld ($D100),a / ld b,10 /
    # halt / djnz / ld a,(INTFLG) / ld ($D101),a / ret) -- nothing cleared.
    # ... and WHEN it returns: JIFFY ($FC9E) before the call and after the return. Held 2 s
    # from about RUN+3.5: a return after the release reads ~100 frames apart.
    # ei / ld hl,(JIFFY) / ld ($D102),hl / ld a,"A" / call $00A5 / ld hl,(JIFFY) /
    # ld ($D104),hl / ret
    "lptout_when": ["NEW", "10 CLEAR 200,&HCFFF:FOR I=0 TO 18:READ X:POKE &HD000+I,X:NEXT",
                    '20 DEFUSR=&HD000:Q=USR(0):J=PEEK(&HD104)+256*PEEK(&HD105)-PEEK(&HD102)-256*PEEK(&HD103):PRINT "[C";J>60;"]"',
                    "30 DATA 251,42,158,252,34,2,209,62,65,205,165,0,42,158,252,34,4,209,201", "RUN"],
    # (lptout_when could not tell: it counts the wait BEFORE the press too.) Frames from
    # the return to the key up: ~0 = it waited for the release, ~100 = it returned on
    # the press. ei / ld a,"A" / call $00A5 / ld bc,0 / up: inc bc / halt /
    # ld a,(NEWKEY+7) / and $10 / jr z,up / ld ($D100),bc / ret
    "lptout_upframes": ["NEW", "10 CLEAR 200,&HCFFF:FOR I=0 TO 21:READ X:POKE &HD000+I,X:NEXT",
                        '20 DEFUSR=&HD000:Q=USR(0):N=PEEK(&HD100)+256*PEEK(&HD101):PRINT "[C";N<10;N>40;"]"',
                        "30 DATA 251,62,65,205,165,0,1,0,0,3,118,58,236,251,230,16,40,247,237,67,0,209",
                        "40 DATA 201", "RUN"],
    "lptout_intflg": ["NEW", "10 CLEAR 200,&HCFFF:FOR I=0 TO 23:READ X:POKE &HD000+I,X:NEXT",
                      '20 DEFUSR=&HD000:Q=USR(0):PRINT "[C";PEEK(&HD100);PEEK(&HD101);"]"',
                      "30 DATA 251,62,65,205,165,0,58,155,252,50,0,209,6,10,118,16,253,58,155,252,50,1",
                      "40 DATA 209,201", "RUN"],
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
