#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BIOSRUNG (3), FNKSB ($00C9): called DIRECTLY after CNSDFG ($F3DE) is changed BEHIND
BASIC's back, VG-8020 against zerobas.

biosregs-acceptance's fnksb_on / fnksb_off read a CNSDFG that KEY ON / KEY OFF had
already set, so C-BIOS's stub (it does nothing) agreed. Here KEY OFF then CNSDFG := $FF
(the line hidden, the flag says shown), and KEY ON then CNSDFG := 0; then FNKSB. The
readout: CNSDFG, CRTCNT ($F3B1) and the first cells of the key row (SCREEN 0 / WIDTH 40:
row 23 at $0398). Black-box: registers, work-area RAM, VRAM.

    python3 -u scratchpad/fnksb_probe.py [ROW ...]
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import basic_probe_biosregs as B   # noqa: E402  (prog, read, MACHINES)

AFTER = ('A=PEEK(&HF3DE):R=PEEK(&HF3B1):V$="":FOR I=0 TO 5:V$=V$+HEX$(VPEEK(&H398+I))+",":NEXT:'
         'PRINT:PRINT "[C";HEX$(A);R;V$;"]"')   # (no END: biosregs' [R] row prints after)
ROWS = {
    "off_ff": B.prog(0x00C9, 0, before="KEY OFF:POKE &HF3DE,255", after=AFTER),
    "on_00":  B.prog(0x00C9, 0, before="KEY ON:POKE &HF3DE,0", after=AFTER),
    "off_00": B.prog(0x00C9, 0, before="KEY OFF", after=AFTER),
    "on_ff":  B.prog(0x00C9, 0, before="KEY ON", after=AFTER),
    # CONTROL: off_ff's setup with KILBUF ($0156) called instead -- does the VG-8020's
    # BASIC repaint the row by itself (then FNKSB is not what painted it)?
    # A on the flag-clear path: CNSDFG's 0, or the caller's A kept?
    "on_00_a5a": B.prog(0x00C9, 0x5A, before="KEY ON:POKE &HF3DE,0", after=AFTER),
    "off_ff_kilbuf": B.prog(0x0156, 0, before="KEY OFF:POKE &HF3DE,255", after=AFTER),
}


def main():
    only = sys.argv[1:] or list(ROWS)
    for name in only:
        got = {side: B.read(m, ROWS[name]) for side, m in B.MACHINES}
        verdict = "NO-REFERENCE" if not got["VG"] else (
            "SAME" if got["VG"] == got["ZB"] else "DIVERGES")
        print(f"ROW {name:7} VG=[{got['VG']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
