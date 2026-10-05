#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-INPUTDNOHASH, part 2: an ASCII digit run left in program text (a number
after a letter run and a space -- `AS 1` stores `41 53 20 31` on the VG-8020
too, scratchpad/asnum_crunch.py) -- how does the EVALUATOR take it?

Each body runs as a program line with an error trap; the reading is fenced
`R<...>#`, quoted text being echoed source (the echo fence).

    python3 -u scratchpad/asciinum_eval.py
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

BODIES = {
    "print2":  'AS=7:PRINT"R";AS 12;"#"',       # var, space, ASCII 12: one item or two?
    "assign":  'X=AS 1.5:PRINT"R";X;"#"',       # var then ASCII digits in an expression
    "plus":    'X=2+AS 3:PRINT"R";X;"#"',
}


def prog(body):
    return ["NEW", "5 ON ERROR GOTO 900", f"10 {body}", "20 END",
            '900 PRINT"R<ERR";ERR;">#":END', "RUN"]


def run(machine):
    out = {}
    for k, b in BODIES.items():
        raw = omsx_repl.run_cases(machine, [("direct", prog(b))], batch=False,
                                  reset=("", "SCREEN 0"), boot=10.0, step=2.0)[0] or ""
        scr = re.sub(r'"[^"\n]*"', "", re.sub(r"\s+", " ", raw))
        m = re.findall(r"\bR(<[^#]*|[^#U][^#]*)#", scr)
        out[k] = m[-1].strip() if m else None
    return out


def main():
    ref = run("Philips_VG_8020")
    ours = run(os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))
    for k in BODIES:
        print(f"{'AGREE   ' if ref[k] == ours[k] else 'DIVERGES'} {k:7} VG {ref[k]!r:24} zb {ours[k]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
