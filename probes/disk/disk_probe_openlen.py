#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional + differential oracle for OPEN..AS #n LEN=r random record size
(disk-BASIC option-closure Item 3).

The default random record length is 256 bytes (2 records per 512-byte sector);
LEN=r sets it to any r that tiles the sector (a power of two in 1..256). This
probe drives LEN=128 -- FOUR records per sector -- and writes records 1..4, which
ALL live in the file's first 512-byte sector (offsets 0/128/256/384). Each PUT
therefore read-modify-writes that one shared sector and must preserve the other
three; reading all four back after a close/reopen proves the 128-byte tiling
round-trips end to end (parse of the LEN= clause, the generalized record->sector
geometry, the shared-sector RMW, and the directory size stamp -- 4*128 = 512, not
4*256). If the geometry had stayed hard-wired at 256, records 2..4 would land in
different sectors and the byte pattern would differ; the real National CF-3300
produces the byte-identical four lines, so the differential catches any drift.

  OPEN "G.DAT" AS #1 LEN=128 : FIELD #1,5 AS A$,5 AS B$
  (PUT #1,1..4 with distinct content) : CLOSE : reopen : GET #1,1..4

Strictly black-box: types REPL lines, reads VRAM. /tmp copy of the disk only.
Reuses disk_probe_getput.py's openMSX driver (build_tcl/run), not duplicated.
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes

import argparse

from disk_probe_getput import run  # noqa: E402  (reuse the openMSX driver)

PROGRAM = [
    'open"g.dat" as #1 len=128',
    'field#1,5 as a$,5 as b$',
    'lset a$="rec01"', 'rset b$="AA"', "put#1,1",
    'lset a$="rec02"', 'rset b$="BB"', "put#1,2",
    'lset a$="rec03"', 'rset b$="CC"', "put#1,3",
    'lset a$="rec04"', 'rset b$="DD"', "put#1,4",
    "close",
    'open"g.dat" as #1 len=128',
    'field#1,5 as a$,5 as b$',
    "get#1,1", 'print"<";a$;"|";b$;">"',
    "get#1,2", 'print"<";a$;"|";b$;">"',
    "get#1,3", 'print"<";a$;"|";b$;">"',
    "get#1,4", 'print"<";a$;"|";b$;">"',
    "close",
]
EXPECT = ["rec01|   AA", "rec02|   BB", "rec03|   CC", "rec04|   DD"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default=_os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_BASIC_DISK"))
    ap.add_argument("--ref-machine", default="National_CF-3300")
    ap.add_argument("--no-ref", action="store_true")
    args = ap.parse_args()
    rc = 0

    got = run(args.machine, PROGRAM, "/tmp/zol.txt")
    print(f"--- zerobas OPEN LEN=128 GET/PUT round-trip ---\nrecords: {got}")
    okf = got == EXPECT
    print("functional:", "PASS" if okf else f"FAIL (expected {EXPECT})")
    rc = rc or (0 if okf else 1)

    if not args.no_ref:
        ref = run(args.ref_machine, PROGRAM, "/tmp/zol_ref.txt", cf3300=True)
        print(f"\n--- CF-3300 differential ---\nrecords: {ref}")
        okr = ref == got == EXPECT
        print("differential:", "PASS — identical to zerobas" if okr
              else "FAIL — CF-3300 differs")
        rc = rc or (0 if okr else 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
