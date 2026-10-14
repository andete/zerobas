#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-PULONG measurement: PRINT USING with a format longer than 32 characters.

zerobas copies the format into PU_FMT (32 B, basic/sysvars.inc) and TRUNCATES a
longer one (PU_FMTMAX). Prediction (2026-10-14): `short` SAME; `tail` (35-char
format, six fields) and `late` (its only field at position 33) DIVERGE, `late`
as ERR 5 on zerobas. Typed BASIC in, the text screen out. VG-8020 vs zerobas NODISK.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

E = ["30 END", '90 PRINT "ERR";ERR:END', "RUN"]
CASES = {
    "short": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT USING "X=###";5'] + E,
    "tail": ["NEW", "10 ON ERROR GOTO 90",
             '20 PRINT USING "A=### B=### C=### D=### E=### F=###";1;2;3;4;5;6'] + E,
    "late": ["NEW", "10 ON ERROR GOTO 90",
             '20 PRINT USING "................................###";7'] + E,
    "w24": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT USING "' + "#" * 24 + '";1'] + E,
    "w25": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT USING "' + "#" * 25 + '";1'] + E,
    "w30e": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT USING "' + "#" * 26 + '^^^^";1'] + E,
    "w20e": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT USING "' + "#" * 20 + '^^^^";1'] + E,
    "d24": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT USING "############.############";1'] + E,
    "d25": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT USING "############.#############";1'] + E,
    "s24": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT USING "**######################";1'] + E,
    "s25": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT USING "**#######################";1'] + E,
    "m24": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT USING "$$######################";1'] + E,
    "m25": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT USING "$$#######################";1'] + E,
    "c25": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT USING "##########,##############";1'] + E,
    "p25": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT USING "+########################";1'] + E,
    "x25": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT USING "#########################-";1'] + E,
    "d24b": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT USING "###########.############";1'] + E,
    "e25": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT USING "#####################^^^^";1'] + E,
    "t25": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT USING "########################-";1'] + E,
    "c24": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT USING "##########,#############";1'] + E,
    "e24p": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT USING "+###################^^^^";1'] + E,
    "big": ["NEW", "10 ON ERROR GOTO 90", '15 CLEAR 1000:F$=STRING$(100,"A")+"##"', '20 PRINT USING F$;5'] + E,
    "big2": ["NEW", "10 ON ERROR GOTO 90", '15 CLEAR 1000:F$="#"+STRING$(120,"-")+"##"', '20 PRINT USING F$;5;6;7'] + E,
    "gc": ["NEW", "10 ON ERROR GOTO 90", '12 CLEAR 250:F$="X"+"=## Y=## Z=##"',
           '20 PRINT USING F$;LEN(STRING$(90,"A"));LEN(STRING$(90,"B"));LEN(STRING$(90,"C"))'] + E,
    "tmp": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT USING "A=##"+" B=##";1;2'] + E,
    "lit2": ["NEW", "10 ON ERROR GOTO 90", '20 PRINT USING "& and &";"X";"YZ"'] + E,
    "var": ["NEW", "10 ON ERROR GOTO 90",
            '15 F$="....................................##"',
            '20 PRINT USING F$;12'] + E,
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
    print(f"\n{'PASS' if not bad else 'FAIL'}: long PRINT USING formats ({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
