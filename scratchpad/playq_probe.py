#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BIOSRUNG (3), STRTMS step (1): the REFERENCE's PLAY queue packet format, read from
RAM after a PLAY -- VG-8020 against zerobas.

STRTMS starts what PUTQ queued; zerobas's queues carry its own packet stream
(sub/playparse.asm), so the reference's format must be known first. A short PLAY on
voice A, waited out, then QUETAB's voice-0 descriptor ($F959, 6 B) and the first 32 B
of VOICAQ ($F975) are PEEKed and printed as hex. The ring's bytes stay where they were
written after the interrupt has consumed them. Black-box: work-area RAM only -- no ROM
byte, no code.

    python3 -u scratchpad/playq_probe.py
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

CASES = {
    "c":      'C',
    "cde":    'CDE',
    "l8c":    'L8C',
    "o5c":    'O5C',
    "v10c":   'V10C',
    "t200c":  'T200C',
    "r4":     'R4',
    "n60":    'N60',
}


def prog(mml):
    return [f'PLAY "{mml}":T=TIME', "IF TIME-T<120 THEN 20",
            'Q$="":FOR I=0 TO 5:Q$=Q$+RIGHT$("0"+HEX$(PEEK(&HF959+I)),2):NEXT',
            'V$="":FOR I=0 TO 31:V$=V$+RIGHT$("0"+HEX$(PEEK(&HF975+I)),2):NEXT',
            'PRINT "[Q";Q$;"]":PRINT "[V";V$;"]"']


def main():
    names = list(CASES)
    for mach in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK"):
        raws = omsx_repl.run_cases(mach, [("stored", prog(CASES[n])) for n in names],
                                   batch=False, run_gap=6.0)
        for n, raw in zip(names, raws):
            txt = " ".join("".join(raw or "").split())
            q = txt.rfind("[Q")
            v = txt.rfind("[V")
            print(f"{mach[:10]:10} {n:6} {txt[q:q + 16] if q >= 0 else '<NO Q>'}  "
                  f"{txt[v:v + 70] if v >= 0 else '<NO V>'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
