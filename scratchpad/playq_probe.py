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
    # ROUND 2 (VG-8020 only, `--vg`): the variants the first reading did not vary
    "s0m1000c": 'S0M1000C',
    "s8c":      'S8C',
    "m255c":    'M255C',
    "s1v10c":   'S1V10C',
    "t32l1c":   'T32L1C',
    "t255l64c": 'T255L64C',
    "cdot":     'C.',
    "o1c":      'O1C',
    "o8b":      'O8B',
    "t32r1":    'T32R1',
    "v0c":      'V0C',
    # ROUND 3: when are the M bytes sent?
    "m1000c":   'M1000C',
    "s0m1000cc": 'S0M1000CC',
    "m1000s0c": 'M1000S0C',
    "s0c":      'S0C',
    "s0cm1000c": 'S0CM1000C',
    # ROUND 4: rests after S / M, N0, and voice B's queue (PLAY "C","E": QUETAB+6)
    "s0r4":     'S0R4',
    "m1000r4c": 'M1000R4C',
    "n0":       'N0',
    "voiceb":   'AB',
    # ROUND 5: M named again with the same value / a new one
    "mmsame":   'M1000CM1000C',
    "mmnew":    'M1000CM2000C',
    # ROUND 6: N0's 5 ticks -- from T, L, or neither?
    "n0t60":    'T60N0',
    "n0l8":     'L8N0',
    "n0t255l1": 'T255L1N0',
    "cn0":      'CN0',
}


def prog(mml):
    if mml == "AB":            # two voices: voice B's descriptor and buffer
        return ['PLAY "C","E":T=TIME', "IF TIME-T<120 THEN 20",
                'Q$="":FOR I=0 TO 5:Q$=Q$+RIGHT$("0"+HEX$(PEEK(&HF95F+I)),2):NEXT',
                'A=PEEK(&HF963)+256*PEEK(&HF964):V$="":FOR I=0 TO 15:V$=V$+RIGHT$("0"+HEX$(PEEK(A+I)),2):NEXT',
                'PRINT "[Q";Q$;"]":PRINT "[V";V$;"]"']
    return [f'CLEAR 500:PLAY "{mml}":T=TIME', "IF TIME-T<120 THEN 20",
            'Q$="":FOR I=0 TO 5:Q$=Q$+RIGHT$("0"+HEX$(PEEK(&HF959+I)),2):NEXT',
            'V$="":FOR I=0 TO 31:V$=V$+RIGHT$("0"+HEX$(PEEK(&HF975+I)),2):NEXT',
            'PRINT "[Q";Q$;"]":PRINT "[V";V$;"]"']


def main():
    args = [a for a in sys.argv[1:] if a != "--vg"]
    names = args or list(CASES)
    machs = ("Philips_VG_8020",) if "--vg" in sys.argv else ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK")
    for mach in machs:
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
