#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TAPELOAD (BMX Simulator, 2026-10-17): which spellings of BLOAD's `,R` run the
loaded code? BMX's line-50 BLOAD loads a code file with an exec address and the
VG-8020 runs it; zerobas returned to BASIC with RUNFLAG 0 (no ,R seen) and the
program ended. The line is the game's and is not read; OUR tape (one binary file
at $D000: ld a,$5A / ld ($D100),a / ret) is loaded with several spellings, and
the row prints PEEK(&HD100): 90 = the code ran, 0 = it did not.
"""
import os, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
from cas_encode import build_cas                    # noqa: E402

CODE = bytes([0x3E, 0x5A, 0x32, 0x00, 0xD1, 0xC9])
FORMS = {
    "r":      'BLOAD"CAS:",R',
    "rlow":   'BLOAD"CAS:",r',
    "rsp":    'BLOAD"CAS:" ,R',
    "rsp2":   'BLOAD"CAS:", R',
    "rcolon": 'BLOAD"CAS:",R:',
    "rnamed": 'BLOAD"CAS:T",R',
    "rbare":  'BLOAD"T",R',
    "rofs":   'BLOAD"CAS:",R,0',
    "plain":  'BLOAD"CAS:"',                       # the control: no ,R -> 0
}
MACHINES = (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK"))


def rows(scr):
    if scr is None:
        return None
    r = [scr[i:i + 40].strip() for i in range(0, len(scr), 40)]
    return " | ".join(x for x in r if x.startswith("[") or "rror" in x) or "<nothing>"


def main():
    tmp = tempfile.mkdtemp(prefix="blrform_")
    path = os.path.join(tmp, "t.cas")
    open(path, "wb").write(build_cas("T", 0xD000, 0xD000, CODE))
    for name in (sys.argv[1:] or list(FORMS)):
        got = {}
        for side, m in MACHINES:
            lines = ["NEW", "CLEAR 200,&HCFFF", "POKE &HD100,0", FORMS[name], "@WAIT20",
                     'PRINT"[";PEEK(&HD100);"]"']
            got[side] = rows(omsx_repl.run_cases(m, [("direct", lines)], batch=False,
                                                 reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                                                 run_gap=10.0, cassette=path)[0])
        print(f"ROW {name:7} VG=[{got['VG']}] ZB=[{got['ZB']}] "
              f"{'SAME' if got['VG'] == got['ZB'] else 'DIVERGES'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
