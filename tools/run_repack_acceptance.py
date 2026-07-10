#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Run an acceptance command with every openMSX launch remapped to the REPACK machine.

The disk-BASIC acceptance probes launch openMSX many different ways — most (~32/34)
call the binary DIRECTLY (`subprocess.Popen([OMSX, "-machine", NAME, ...])`), a couple
funnel through probes/lib/omsx_run.py, and the BDOS gate uses omsx_session. There is no
single Python funnel, so an env var honoured by only some probes gives FALSE coverage
(the others silently boot the LEAN machine). The one thing they ALL share is the openMSX
BINARY, resolved as `$OPENMSX` or `shutil.which("openmsx")`.

So we intercept at the binary: write a tiny wrapper named `openmsx` into a temp dir,
prepend that dir to PATH and point $OPENMSX at it (covering both resolution styles), and
have the wrapper rewrite `-machine <lean> -> <repack>` before exec'ing the REAL binary.
This is universal (every probe, however it launches) and NON-DESTRUCTIVE — it never
touches the user's installed machine .xml files. A STRICT check in the wrapper hard-fails
if a zerobas BASIC machine survives unmapped, so an un-remapped probe is caught, never
hidden (the analogue of diskbasic_acceptance's oracle-ran vacuity guard).

    python3 tools/run_repack_acceptance.py \
        --map C-BIOS_MSX1_EU_BASIC_DISK=C-BIOS_MSX1_EU_REPACK_DISK \
        --map C-BIOS_MSX1_BASIC_DISK=C-BIOS_MSX1_EU_REPACK_DISK \
        -- python3 probes/disk/diskbasic_acceptance.py
"""
from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
import tempfile

WRAPPER = r'''#!/usr/bin/env python3
import os, sys
REAL = os.environ["OPENMSX_REAL"]
MAP = {}
for pair in os.environ.get("ZEROBAS_MACHINE_MAP", "").split(";"):
    if "=" in pair:
        k, v = pair.split("=", 1)
        MAP[k.strip()] = v.strip()
argv = sys.argv[1:]
for i, a in enumerate(argv):
    if a == "-machine" and i + 1 < len(argv):
        argv[i + 1] = MAP.get(argv[i + 1], argv[i + 1])
        m = argv[i + 1].upper()
        if os.environ.get("ZEROBAS_MACHINE_STRICT") == "1" \
           and "BASIC" in m and "C-BIOS_MSX1" in m and "REPACK" not in m:
            sys.stderr.write(
                "[openmsx-repack-shim] STRICT: refusing to boot lean zerobas machine "
                f"'{argv[i + 1]}' — this probe dodged the machine map and would run the "
                "LEAN build (false repack coverage). Add its machine name to --map.\n")
            sys.exit(97)
os.execv(REAL, [REAL] + argv)
'''


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--map", action="append", default=[], metavar="OLD=NEW",
                    help="remap an openMSX machine name (repeatable)")
    ap.add_argument("--no-strict", action="store_true",
                    help="disable the lean-machine vacuity guard (not recommended)")
    ap.add_argument("cmd", nargs=argparse.REMAINDER,
                    help="-- <command to run> (e.g. -- python3 probes/disk/...)")
    args = ap.parse_args()

    cmd = args.cmd[1:] if args.cmd and args.cmd[0] == "--" else args.cmd
    if not cmd:
        sys.exit("no command given (use: ... -- python3 probes/disk/diskbasic_acceptance.py)")
    if not args.map:
        sys.exit("no --map given (nothing to remap)")

    real = os.environ.get("OPENMSX") or shutil.which("openmsx")
    if not real or not os.path.exists(real):
        sys.exit("cannot locate the real openmsx binary (set $OPENMSX or put it on PATH)")

    tmp = tempfile.mkdtemp(prefix="repack_omsx_")
    try:
        shim = os.path.join(tmp, "openmsx")
        with open(shim, "w") as f:
            f.write(WRAPPER)
        os.chmod(shim, os.stat(shim).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

        env = dict(os.environ)
        env["OPENMSX_REAL"] = real
        env["OPENMSX"] = shim                       # style: $OPENMSX
        env["PATH"] = tmp + os.pathsep + env.get("PATH", "")  # style: which("openmsx")
        env["ZEROBAS_MACHINE_MAP"] = ";".join(args.map)
        if not args.no_strict:
            env["ZEROBAS_MACHINE_STRICT"] = "1"

        print(f"[repack-acceptance] real openmsx: {real}")
        print(f"[repack-acceptance] remap: {'; '.join(args.map)}"
              f"{'  (STRICT)' if not args.no_strict else ''}")
        return subprocess.run(cmd, env=env).returncode
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
