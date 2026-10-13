#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-OFFICIAL gate: jobs zerobas keeps in the OFFICIAL MSX work-area cell, as
the VG-8020 does. `make officialcell-acceptance`.

Joost's rule (2026-10-13): every RAM cell zerobas invented is checked against
how the reference does the job, and gives way to the official cell where one
exists. Each row runs a tiny program that makes the job happen, PEEKs the
published address (MSX2 Technical Handbook's work-area map) and prints it in
brackets -- VG-8020 against the diskless build. Typed BASIC and published
addresses only.

  GATED (moved, must agree):
    trcflg / -ctl   TRON -> TRCFLG $F7C4 = 175, TROFF -> 0
    maxfil / -ctl   MAXFILES=3 -> MAXFIL $F85F = 3; boot 1
  REPORTED (not moved yet; printed, never scored):
    datptr / -ctl   READ -> DATPTR $F6C8

Measurement history: scratchpad/officialcell_probe.py (before:
scratchpad/officialcell_before.out -- zerobas 0 in every row).
"""
import os, sys
os.environ.setdefault("ZEROBAS_REFCACHE", "0")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
ROWS = [  # (name, gated, lines)
    ("trcflg", True, ["10 TRON:A=PEEK(&HF7C4):TROFF", '20 ?"["A"]"', "RUN"]),
    ("trcflg-ctl", True, ['10 A=PEEK(&HF7C4):?"["A"]"', "RUN"]),
    ("maxfil", True, ['10 MAXFILES=3:?"["PEEK(&HF85F)"]"', "RUN"]),
    ("maxfil-ctl", True, ['10 ?"["PEEK(&HF85F)"]"', "RUN"]),
    ("datptr", False, ['10 READ A:?"["PEEK(&HF6C8)+256*PEEK(&HF6C9)"]"', "20 DATA 5", "RUN"]),
    ("datptr-ctl", False, ['10 ?"["PEEK(&HF6C8)+256*PEEK(&HF6C9)"]"', "20 DATA 5", "RUN"]),
]


def read(machine, lines):
    raw = omsx_repl.run_cases(machine, [("direct", ["NEW"] + lines)], batch=False,
                              reset=("", "SCREEN 0"), run_gap=6.0)[0]
    v = omsx_repl.result_span(raw) if raw else None
    return None if v is None else v.strip()


def main():
    bad = 0
    for name, gated, lines in ROWS:
        r, z = read(REF, lines), read(ZB, lines)
        if gated and (r is None or z is None):
            print(f"{name:11s} INSTRUMENT FAULT: no reading (ref={r}, zb={z})")
            return 2
        same = r == z
        tag = ("SAME" if same else "DIVERGES") if gated else "reported"
        bad += gated and not same
        print(f"{name:11s} {tag:9s} ref {r!s:>7}  zb {z!s:>7}", flush=True)
    print("officialcell gate:", "PASS" if not bad else f"FAIL ({bad})")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
