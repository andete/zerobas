#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional probe: does zerobas's BLOAD disk-filename parser build the right FCB?

RE-SITED 2026-09-01 (D-FCBSITE). The original broke at a FROZEN main-ROM
address for do_disk_bload -- and the D-PROBEREACH5 audit found BOTH of that
design's legs gone: do_disk_bload was evicted to the sub-ROM (build/sub.sym,
a page-1 tenant), and so was the 8.3 name build itself (build_83_name ->
SUBROM_IDX_FCBNAME). Worse, the probe's chosen machine (plain
C-BIOS_MSX1_BASIC, "no disk slot") has NO ZEROBAS SUB-ROM AT ALL, so on
today's tree the parse it wanted to observe cannot even RUN there --
subrom_call answers absent. A frozen address rots; a frozen MACHINE CHOICE
rots too.

The re-site drops the breakpoint entirely. The subject was never the address
-- it is the 12 FCB bytes at DISK_FCB ($E0DB) after the parse -- and those
persist in RAM after the statement completes (the failed find of a nonexistent
file does not wipe them). So: boot the REPACK machine (sub-ROM present), type
each BLOAD of a nonexistent file through the omsx_repl harness (its delivery
is echo-paced -- event-synced by construction, docs/dev-workflow.md), and
capture ("mem_abs", [(DISK_FCB, 12)]) once the line has run.

The scratch FCB (basic/sysvars.inc):
  +0       drive code (0=default->1 effective, 1=A, 2=B)
  +1..+11  11-byte 8.3 name field (8 name + 3 ext, space-padded, upper-cased)

Cases (unchanged from the original -- the expectations were never the rot):
  BLOAD"A:NOSUCH.BIN" -> drive 1 (A), name "NOSUCH  BIN"
  BLOAD"NOSUCH.BIN"   -> drive 1 (A, default), name "NOSUCH  BIN"
  BLOAD"B:NO.TXT"     -> drive 2 (B), name "NO      TXT"
(Names changed to files NOT on test720.dsk so the load FAILS cleanly after the
parse and no fixture bytes move; the original TEST.BIN/HI.TXT would LOAD on
the repack machine, which the old diskless design never had to think about.)

Strictly an observation of zerobas's own scratch RAM; no ROM is read or
disassembled.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "lib"))
import omsx_repl                                             # noqa: E402

DISK_FCB = 0xE0DB
FCB_LEN = 12
MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE")
if not MACHINE:
    sys.exit("no zerobas machine: pass ZEROBAS_BASIC_MACHINE (there is no "
             "default; one would silently pick the build under test -- "
             "docs/spec-lean-retire-s1-explicit-machine.md)")

CASES = [
    ('bload"a:nosuch.bin"', 1, b"NOSUCH  BIN"),
    ('bload"nosuch.bin"',   1, b"NOSUCH  BIN"),
    ('bload"b:no.txt"',     2, b"NO      TXT"),
]


def main() -> int:
    cases = [("direct", ["NEW", line]) for line, _, _ in CASES]
    caps = omsx_repl.run_cases(MACHINE, cases, batch=False, reset=(),
                               capture=("mem_abs", [(DISK_FCB, FCB_LEN)]))
    rc = 0
    for (line, exp_drv, exp_name), cap in zip(CASES, caps):
        if not cap:
            print(f"FAIL {line}: <NO CAPTURE>")
            rc = 1
            continue
        fcb = bytes.fromhex(cap.strip())[:FCB_LEN]
        drv, name = fcb[0], fcb[1:12]
        ok = drv == exp_drv and name == exp_name
        print(f"{'PASS' if ok else 'FAIL'} {line:22s} drive={drv} "
              f"name={name!r}" + ("" if ok else
              f"   want drive={exp_drv} name={exp_name!r}"))
        rc = rc or (0 if ok else 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
