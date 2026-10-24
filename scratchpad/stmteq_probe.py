#!/usr/bin/env python3
"""D-STMTEQ + D-BAREEXTRA: does a malformed statement act before its error?

Each case prints a `[MARK]` line first: a screen that loses it was cleared by the
statement before the error. Typed keys in, the text screen out (no ROM read).
Cases: SCREEN=1, SCREEN 1 X, CLS 1, CLS=1, END 1 / STOP 1 in a program, and two
controls that DO clear (SCREEN 1:SCREEN 0, CLS:PRINT).

    python3 -u scratchpad/stmteq_probe.py [MACHINE ...]
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MARK = 'PRINT "[MARK]"'
AFTER = 'PRINT "[AFTER]";PEEK(&HFCAF)'
CASES = {
    "scr_eq": [MARK, "SCREEN=1", AFTER],
    "scr_junk": [MARK, "SCREEN 1 X", AFTER],
    "scr_ok": [MARK, "SCREEN 1:SCREEN 0", AFTER],
    "cls_1": [MARK, "CLS 1", AFTER],
    "cls_eq": [MARK, "CLS=1", AFTER],
    "cls_ok": [MARK, 'CLS:PRINT "[AFTER]"'],
    "end_1": ['10 PRINT "[A]";:END 1', '20 PRINT "[B]"', "RUN"],
    "stop_1": ['10 PRINT "[A]";:STOP 1', '20 PRINT "[B]"', "RUN"],
}


def reading(scr):
    rows = [scr[i:i + 40].rstrip() for i in range(0, len(scr or ""), 40)]
    keep = [r.strip() for r in rows if any(k in r for k in ("[MARK]", "[AFTER]", "[A]", "[B]", "rror", "Break"))]
    return " | ".join(k for k in keep if not k.startswith("PRINT") and not k[:2].isdigit())


def main():
    for m in sys.argv[1:] or ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"]:
        for name, lines in CASES.items():
            scr = omsx_repl.run_cases(m, [("direct", lines)], batch=False, boot=10.0,
                                      reset=("SCREEN 0:WIDTH 40", "NEW"), step=3.0,
                                      run_gap=8.0)[0]
            print(f"{m:30s} {name:9s} {reading(scr)}", flush=True)


if __name__ == "__main__":
    main()
