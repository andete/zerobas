#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-EVALSLOPE apparatus check (2026-10-20): input-devices-acceptance phase C, case `up`
(row 8 $20 held 8 s across a STICK/STRIG sampling RUN), reads MIS-ECHOED 'RUN' -> 'UN' on
the climber build; a39cefcc passes. Is the R really lost, or is the cursor parked on it?
Runs the case exactly as phase C does (same kw), echo guard off, and reads at the capture:
  1. the SCREEN-0 name table, raw bytes of every row holding 'UN' (the cursor cell is a
     live cell; non-print decodes to blank in the harness);
  2. CSRY / CSRX ($F3DC / $F3DD, work-area RAM): where the cursor stands.
    python3 -u scratchpad/upcase_cell_probe.py      (UC_MACHINE to override)
"""
import os, sys
os.environ["ZEROBAS_ECHOGUARD"] = "off"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import omsx_repl                                    # noqa: E402
import basic_probe_input_devices as P               # noqa: E402

M = os.environ.get("UC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
KW = dict(reset=("NEW", "CLS"), holds=[(8, 0x20)], hold_secs=8.0, cap_gap=25.0, batch=False)


def main():
    scr = omsx_repl.run_cases(M, [("stored", P.SAMPLER)], capture=("vram", 0, 960), **KW)[0]
    raw = bytes.fromhex(scr) if isinstance(scr, str) else (scr or b"")
    if isinstance(scr, str) is False and isinstance(scr, (bytes, bytearray)):
        raw = bytes(scr)
    for row in range(len(raw) // 40):
        cells = raw[row * 40:(row + 1) * 40]
        text = "".join(chr(b) if 32 <= b < 127 else "." for b in cells).rstrip()
        if text:
            print(f"row {row:2} {text!r:44} head={cells[:4].hex()}")
    cur = omsx_repl.run_cases(M, [("stored", P.SAMPLER)],
                              capture=("mem_abs", [(0xF3DC, 2)]), **KW)[0]
    print(f"CSRY/CSRX raw: {cur!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
