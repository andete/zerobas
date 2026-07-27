#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""FAT-primitive ERROR-disposition gate — the path `diskbasic-acceptance` misses.

WHY THIS EXISTS.  The repack build reaches every FAT12 primitive through resident
shims that bounce into the sub-ROM tenant (`fatprim_bounce`, basic/fat.asm) and
marshal the primitive's disposition back over the DISKOP result block: Cy=1 on a
tenant error, Cy=0 on success.  On 2026-07-27 the thirteen duplicated shim bodies
were collapsed into that one shared body, and the collapse was checked by
DELIBERATELY NEUTERING the error tail (`scf` -> `or a`) and re-running the gates:

    make diskbasic-acceptance-repack   ->  34/34 CONVERGED, with the error
                                           disposition provably broken.

All 34 oracle-differential verbs exercise the SUCCESS path only.  A gate that
stays green while the code under test is broken is measuring nothing
(the standing lesson), so this probe measures the other half.

WHAT IT MEASURES.  Seven verbs driven at a filename that does not exist, each of
which must reach `fat_find` (or `fat_io_open`) and take the STATUS != 0 return.
zerobas answers with its OWN lowercase `load error` (a DOCUMENTED divergence from
the reference's "File not found" -- see basic/PROVENANCE.md / load_error), so this
is deliberately a SELF-CHECK against zerobas's pinned wording, not an oracle
differential: an oracle comparison here would fail on the divergence, not on the
disposition.

FALSIFICATION RECORD (this is the evidence the gate measures its subject).  With
the error tail neutered, four of the seven cases below SILENTLY REPORT NOTHING --
load-missing, run-missing, open-missing, merge-missing.  Restoring the tail
restores `load error` on all seven.  If you change fatprim_bounce, re-run that
experiment rather than trusting a green here.

  python3 probes/disk/disk_probe_fat_error_disposition.py [--machine NAME]
"""
from __future__ import annotations
import argparse, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "lib"))
import omsx_repl  # noqa: E402

# Each verb must route a "not found" through the FAT primitive shim layer and
# surface zerobas's load_error.  Kept to DIRECT-mode one-liners so the failure
# lands on the line right below the echoed command.
CASES = [
    ("load-missing",  'LOAD"A:NOSUCH.BAS"'),
    ("run-missing",   'RUN"A:NOSUCH.BAS"'),
    ("kill-missing",  'KILL"A:NOSUCH.BAS"'),
    ("bload-missing", 'BLOAD"A:NOSUCH.BIN"'),
    ("open-missing",  'OPEN"A:NOSUCH.DAT" FOR INPUT AS #1'),
    ("name-missing",  'NAME"A:NOSUCH.BAS" AS "B.BAS"'),
    ("merge-missing", 'MERGE"A:NOSUCH.BAS"'),
]
WANT = "load error"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default="C-BIOS_MSX1_EU_REPACK_DISK")
    ap.add_argument("--diska", default=None)
    ap.add_argument("--boot-per-case", action="store_true",
                    help="isolation escape hatch when a batched case looks wrong")
    args = ap.parse_args()

    specs = [("direct", [line]) for _, line in CASES]
    raws = omsx_repl.run_cases(args.machine, specs,
                               batch=not args.boot_per_case,
                               reset=("NEW", "CLS"), capture="screen",
                               diska=args.diska)

    ok = True
    print("=" * 72)
    print("FAT-primitive ERROR disposition (Cy=1 out of fatprim_bounce)")
    print("=" * 72)
    for (key, line), raw in zip(CASES, raws):
        tail = omsx_repl.screen_tail(raw, line)
        got = " | ".join(t.strip() for t in str(tail or "").split("\n") if t.strip())
        good = WANT in (tail or "")
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  {key:14} {line:38} -> {got[:60]!r}")
        if not good:
            print(f"        want {WANT!r} -- a SILENT return here is the exact "
                  f"signature of a broken error tail")

    print(f"\n===== FAT error disposition: "
          f"{sum(1 for _ in CASES) if ok else '<7'}/{len(CASES)} =====")
    print("ALL PASS" if ok else "SOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
