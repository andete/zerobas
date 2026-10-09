# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-AMPB (gate: ampb-acceptance): `&B` binary numbers in a program and at the prompt.

Both references crunch `&B101` as the typed characters (no token), and the
VG-8020 READS them when the line runs; zerobas said Syntax error until
D-AMPB (2026-10-09). The rows pin the measured rules: the value (`&B101` 5,
16 ones -1), lowercase, a bare `&B` is 0, the number stops at the first byte
that is not 0/1 (`PRINT &B12` prints 1 and 2), 17 significant digits is
Overflow, `&X1` stays Syntax error, and LIST shows the text unchanged.

Each row prints `ROW <name> VG=[...] ZB=[...] <verdict>`.
Exit 0 all agree; 1 a divergence; 2 the VG-8020 gave no reading.
Clean-room: typed BASIC in, the text screen out. VG-8020 vs zerobas NODISK.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

CASES = {
    "prog": ["NEW", '10 PRINT "[";&B101;"]"', "20 A=&B11111111:PRINT A", "30 PRINT &B1+1", "RUN"],
    "direct": ['PRINT "[";&B101;"]"'],
    "big": ["NEW", '10 PRINT &B1111111111111111', "RUN"],
    # round 2 (2026-10-09): the edges a fix must keep
    "big17": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT &B11111111111111111', "30 END",
              '90 PRINT "ERR";ERR:END', "RUN"],
    "nodig": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT "[";&B;"]"', "30 END",
              '90 PRINT "ERR";ERR:END', "RUN"],
    "lower": ["NEW", '10 PRINT &b101', "RUN"],
    "junk": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT &B12', "30 END",
             '90 PRINT "ERR";ERR:END', "RUN"],
    "badx": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT &X1', "30 END",
             '90 PRINT "ERR";ERR:END', "RUN"],
    "expr": ["NEW", '10 A=&B10*3:PRINT A;-&B101;&B1+&B1', "RUN"],
    "list": ["NEW", '10 A=&B101', "LIST"],
}


def rows(scr, start):
    if scr is None:
        return None
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    if start in r:
        r = r[r.index(start) + 1:]
    return " | ".join(x for x in r if x and x not in ("Ok", "ZB"))


def main():
    only = sys.argv[1:] or list(CASES)
    bad, blind = [], []
    for name in only:
        lines = CASES[name]
        got = {}
        for side, m in (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK")):
            got[side] = rows(omsx_repl.run_cases(m, [("direct", lines)], batch=False,
                                                 reset=("", "SCREEN 0:WIDTH 40"), step=3.0)[0],
                             lines[-1])
        if got["VG"] is None:
            blind.append(name)
            verdict = "NO-REFERENCE"
        elif got["VG"] == got["ZB"]:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad.append(name)
        print(f"ROW {name} VG=[{got['VG']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: the VG-8020 gave no reading on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: &B binary numbers ({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
