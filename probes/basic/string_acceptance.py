#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""string-acceptance -- the standing gate for the string engine (arc S5; string
comparison S3; string functions S3).

Runs all four halves against the merged repack build (relocated BASIC + string
engine) and reports one PASS/FAIL:

  1. CRUNCH    (basic_probe_crunch.py --zb-machine) -- the string keywords
     (engine + comparison + functions) tokenise byte-for-byte like the VG-8020
     reference AND match the §4 captured token bytes ($FF-suffixes and the
     STRING$/INSTR bare single-byte tokens).
  2. EXECUTE   (basic_probe_string.py) -- the verbs and `+` concatenation produce
     the right screen output live on the relocated build.
  3. COMPARE   (basic_probe_str_cmp.py) -- the six relational operators on string
     operands (=/<>/</>/<=/>=) match the VG-8020 reference, both reference-lock and
     zerobas==reference (spec-basic-string-compare.md).
  4. FUNCTIONS (basic_probe_str_fn.py) -- HEX$/OCT$/SPACE$/STRING$/INSTR match the
     VG-8020 reference, both reference-lock and zerobas==reference
     (spec-basic-string-functions.md); two documented STRMAX-clamp divergences
     (SPACE$/STRING$ overflow) are asserted against zerobas's own contract instead
     of the reference, per that spec's D-3.

Together: the keywords crunch like a real MSX ROM *and* execute correctly on the
build we actually ship. Heavy + oracle-dependent (boots openMSX, needs the repack
machine from `make repack-machine` and your VG-8020 reference ROM); NOT part of the
emulator-free `unit-test`. Driven by the Makefile `string-acceptance` target.

    python3 probes/basic/string_acceptance.py
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CRUNCH = os.path.join(HERE, "basic_probe_crunch.py")
STRING = os.path.join(HERE, "basic_probe_string.py")
STRCMP = os.path.join(HERE, "basic_probe_str_cmp.py")
STRFN = os.path.join(HERE, "basic_probe_str_fn.py")
REPACK_MACHINE = "C-BIOS_MSX1_EU_REPACK_DISK"
REF_MACHINE = "Philips_VG_8020"


def run(label, argv):
    print(f"\n===== {label} =====")
    rc = subprocess.call([sys.executable] + argv)
    print(f"----- {label}: {'PASS' if rc == 0 else 'FAIL'} -----")
    return rc == 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REPACK_MACHINE,
                    help=f"repack acceptance machine (default {REPACK_MACHINE})")
    ap.add_argument("--ref", default=REF_MACHINE,
                    help=f"reference-BASIC oracle machine (default {REF_MACHINE})")
    ap.add_argument("--full", action="store_true",
                    help="also re-run the full crunch corpus on the repack build "
                         "(exhaustive relocated-kwtable proof; many boots)")
    args = ap.parse_args()

    crunch_ok = run("CRUNCH (8 string keywords, repack vs VG-8020 + §4 table)",
                    [CRUNCH, "--machine", args.ref, "--zb-machine", args.machine]
                    + (["--full"] if args.full else []))
    exec_ok = run("EXECUTE (verbs + concat, live on the repack build)",
                  [STRING, "--machine", args.machine])
    cmp_ok = run("COMPARE (6 relational operators on strings, repack vs VG-8020)",
                 [STRCMP, "--machine", args.ref, "--zb-machine", args.machine])
    fn_ok = run("FUNCTIONS (HEX$/OCT$/SPACE$/STRING$/INSTR, repack vs VG-8020)",
                [STRFN, "--machine", args.ref, "--zb-machine", args.machine])

    ok = crunch_ok and exec_ok and cmp_ok and fn_ok
    print("\n=====================")
    print(f"crunch    (byte-identical tokenise) : {'PASS' if crunch_ok else 'FAIL'}")
    print(f"execute   (correct screen output)   : {'PASS' if exec_ok else 'FAIL'}")
    print(f"compare   (string relops vs oracle) : {'PASS' if cmp_ok else 'FAIL'}")
    print(f"functions (HEX$/OCT$/SPACE$/STRING$/INSTR vs oracle): {'PASS' if fn_ok else 'FAIL'}")
    print(f"string-acceptance: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
