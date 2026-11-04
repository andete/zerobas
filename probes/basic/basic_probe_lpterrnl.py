#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LPTERRNL (gate: lpterrnl-acceptance): an error ends a partial printer line.

On the VG-8020 an error -- trapped or not, inside the LPRINT or in a later
statement -- puts CR/LF on the printer when its head is mid-line, before the
handler's own output. zerobas flushed only at the prompt, so a trapped error
glued the handler's LPRINT onto the line (fixed 2026-11-05: basic/interp.asm
raise_error calls lpt_flush).

Our own programs, one per boot; openMSX's printer logger captures what the
printer receives (CR / LF shown as \\r \\n). Typed BASIC in, the log out.

    python3 -u probes/basic/basic_probe_lpterrnl.py [--gate] [vg8020,zb]

--gate: every row must read the same on both sides (exit 1 if not; exit 2 if a
VG-8020 row is empty -- an unread reference agrees with nothing).
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402
from basic_probe_editverb import prn_reading       # noqa: E402

H = "10 ON ERROR GOTO 90"
CASES = {
    # the error INSIDE the LPRINT; the handler LPRINTs
    "inlp":   [H, '20 LPRINT "A[";1/0', "30 END", '90 LPRINT "E";ERR:RESUME 30'],
    # the error in the NEXT statement, after an LPRINT that ended with ;
    "after":  [H, '20 LPRINT "A[";:X=1/0', "30 END", '90 LPRINT "E";ERR:RESUME 30'],
    # the handler prints NOTHING to the printer; the program LPRINTs after
    "quiet":  [H, '20 LPRINT "A[";1/0', '30 LPRINT "Z":END', "90 RESUME 30"],
    "quiet2": [H, '20 LPRINT "A[";:X=1/0', '30 LPRINT "Z":END', "90 RESUME 30"],
    # untrapped
    "untrap": ['20 LPRINT "A[";1/0'],
    # control: no error at all
    "ctrl":   ['20 LPRINT "A[";:LPRINT "Z"'],
}
SIDES = {"vg8020": ("Philips_VG_8020", 8.0), "zb": ("C-BIOS_MSX1_EU_REPACK_NODISK", 8.0)}


def main():
    gate = "--gate" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--gate"]
    sides = (args[0] if args else "vg8020,zb").split(",")
    got = {}
    for side in sides:
        m, boot = SIDES[side]
        log = probe_tmp.tmp(f"lpterrnl_{side}.log")
        plug = (f"set printerlogfilename {{{log}}}", "plug printerport logger")
        cases = [("direct", ["NEW"] + lines + ["RUN"]) for lines in CASES.values()]
        caps = omsx_repl.run_cases(m, cases, batch=False, reset=(), boot=boot, step=4.0,
                                   prologue=plug, capture=("screen_printer", log))
        for name, raw in zip(CASES, caps):
            got[(side, name)] = prn_reading(raw)
            print(f"{side:7s} {name:7s} {got[(side, name)]}", flush=True)
    print(__import__("probe_refcache").summary())
    if not gate:
        return 0
    if any(got.get(("vg8020", n), "<").startswith("<") for n in CASES):
        print("BROKEN FIXTURE: a VG-8020 row was not read")
        return 2
    bad = [n for n in CASES if got.get(("vg8020", n)) != got.get(("zb", n))]
    print(f"lpterrnl: {len(CASES) - len(bad)}/{len(CASES)} rows agree" + (f"; DIVERGE {bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
