#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BIOSRUNG (3), CALBAS ($0159): "call the BASIC interpreter at IX, from any slot",
called DIRECTLY -- VG-8020 against zerobas.

Our BASIC's internal addresses are not the VG-8020's, so the MECHANISM is what is
measured: IX = $004D (WRTVRM, the same published entry in both ROMs) with A = $5A and
HL = $3F10 -- did the call reach it (the VRAM cell), and what came back (HL / DE / BC /
A, IY)? Our own stub (biosregs' shape plus IX): ld ix,$004D / ld iy,$1234 / the
registers / call $0159 / the registers stored. Black-box: registers and VRAM.

    python3 -u scratchpad/calbas_probe.py
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import basic_probe_biosregs as B   # noqa: E402  (prog, read, MACHINES)

_stub = B.stub


def stub_ix(addr, a, bc, de, hl, buf=None):
    # ld ix,$004D / ld iy,$1234 / <biosregs' body> with ld ($D108),iy before the ret
    body = _stub(addr, a, bc, de, hl, buf)
    return ([0xDD, 0x21, 0x4D, 0x00, 0xFD, 0x21, 0x34, 0x12] + body[:-1]
            + [0xFD, 0x22, 0x08, 0xD1, 0xC9])


B.stub = stub_ix
AFTER = 'PRINT:PRINT "[C";HEX$(VPEEK(&H3F10));" IY";HEX$(PEEK(&HD109)*256+PEEK(&HD108));"]"'
ROWS = {
    "calbas_wrtvrm": B.prog(0x0159, 0x5A, hl=0x3F10, before="VPOKE &H3F10,0", after=AFTER),
}


def main():
    for name in sys.argv[1:] or list(ROWS):
        got = {side: B.read(m, ROWS[name]) for side, m in B.MACHINES}
        verdict = "NO-REFERENCE" if not got["VG"] else (
            "SAME" if got["VG"] == got["ZB"] else "DIVERGES")
        print(f"ROW {name:14} VG=[{got['VG']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
