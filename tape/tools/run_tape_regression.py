#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause

"""Tier-1 deterministic regression for the full zerobas-tape stack.

Self-contained -- uses only clean-room content (no copyrighted ROMs, no game
tapes). Every input is generated from code, so the suite is reproducible
anywhere the openMSX machines and zerobas are installed.
The optional real-tape corpus tier (Tier 2/3) lives in the companion
msx-preservation repo at tools/omsx/bios_probe_realtape.py.

What it asserts:

  1. .cas BLOAD (3744 baud) on the rolled-together shipping target
     C-BIOS_MSX1_EU_BASIC -- stock C-BIOS + zerobas-tape IPS + zerobas IPS, no
     cart, no VG-8020 ROM. Proves the open stack BLOAD"CAS:",R-s a .cas end to
     end (the 3744 read-margin path).

  2. .cas readback at 3744 baud on C-BIOS_MSX1_EU_TAPE: a .cas container with
     the known two-block test pattern is synthesised by openMSX at 3744 baud
     (the same speed it uses for any .cas), then read back byte-for-byte via
     TAPION/TAPIN. Isolates the tape signal layer at 3744 baud from the full
     BLOAD application stack.

  3. Write -> read round-trip at 1200 and 2400 baud on C-BIOS_MSX1_EU_TAPE: a
     write cart lays a two-block BSAVE file via TAPOON/TAPOUT, openMSX records it
     to a WAV, a read cart reads it back via TAPION/TAPIN, and the bytes must
     match. Guards the slower bauds against regression.

  4. Open-stack WAV BLOAD at 1200 and 2400: zerobas BLOADs a tape written by the
     zerobas-tape write path and runs it (,R handoff). The end-to-end open stack on
     a recorded WAV.

Prerequisites (local setup, not committed): the C-BIOS_MSX1_EU_BASIC and
C-BIOS_MSX1_EU_TAPE openMSX machines (install with zerobas/zerobas-tape's
install-openmsx-machine.py) and a built zerobas basic.rom.

  make test
  python3 tools/run_tape_regression.py
  python3 tools/run_tape_regression.py --zerobas ~/projects/zerobas/build/basic.rom
  python3 tools/run_tape_regression.py --msx-preservation /path/to/msx-preservation
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_MSX_PRES_CANDIDATES = [
    os.path.join(_REPO, os.pardir, "msx-preservation"),
]


def _find_msx_preservation(override=None):
    if override:
        p = os.path.abspath(override)
    else:
        p = os.environ.get("MSX_PRESERVATION", "")
        if not p:
            p = next(
                (os.path.normpath(c) for c in _MSX_PRES_CANDIDATES
                 if os.path.isdir(c)), "")
    if not p or not os.path.isdir(p):
        sys.exit(
            "error: msx-preservation repo not found -- pass --msx-preservation PATH, "
            "set $MSX_PRESERVATION, or check it out next to this repo "
            f"(looked in: {', '.join(os.path.normpath(c) for c in _MSX_PRES_CANDIDATES)})"
        )
    return p


BASIC_MACHINE = "C-BIOS_MSX1_EU_BASIC"
TAPE_MACHINE = "C-BIOS_MSX1_EU_TAPE"
DONE = 0x7FF0


def _run(cmd, timeout=200):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=timeout)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def t_cas_bload(bload) -> tuple[str, bool, str]:
    rc, out = _run([sys.executable, bload, "--machine", BASIC_MACHINE, "--repl"])
    ok = (rc == 0) and ("PASS  PC at landmark" in out)
    detail = "JONG@E000 + ,R handoff" if ok else \
             (out.strip().splitlines()[-1] if out.strip() else "no output")
    return (f".cas BLOAD @3744 ({BASIC_MACHINE})", ok, detail)


def t_cas_readback(tapfile, omsx_run) -> tuple[str, bool, str]:
    """Mount a generated .cas; openMSX synthesises it at 3744 baud; read via TAPION/TAPIN."""
    cas = tempfile.mktemp(suffix=".cas", prefix="rt_cas_")
    r   = tempfile.mktemp(suffix=".rom", prefix="rt_r_cas_")
    cap = tempfile.mktemp(suffix=".txt", prefix="rt_cas_")
    try:
        _run([sys.executable, tapfile, "--write-cas", cas])
        _run([sys.executable, tapfile, "--read", r])
        _run([sys.executable, omsx_run, "--machine", TAPE_MACHINE, "--cart", r,
              "--cassette", cas, "--bp", hex(DONE), "--reg", "PC",
              "--mem", "memory:0xE000:28", "--out", cap, "--timeout", "90"])
        rc, out = _run([sys.executable, tapfile, "--analyze", cap])
        ok = (rc == 0) and ("MATCH" in out)
        detail = ".cas -> 3744-baud synthesis -> TAPION/TAPIN" if ok else \
                 out.strip().splitlines()[-1]
    finally:
        for f in (cas, r, cap):
            if os.path.exists(f):
                os.unlink(f)
    return ("cas readback @3744 (openMSX synthesis)", ok, detail)


def t_roundtrip(omsx_run, tapfile, baud: int) -> tuple[str, bool, str]:
    w   = tempfile.mktemp(suffix=".rom", prefix=f"rt_w_{baud}_")
    r   = tempfile.mktemp(suffix=".rom", prefix=f"rt_r_{baud}_")
    wav = tempfile.mktemp(suffix=".wav", prefix=f"rt_{baud}_")
    cap = tempfile.mktemp(suffix=".txt", prefix=f"rt_{baud}_")
    try:
        _run([sys.executable, tapfile, "--write", w, "--baud", str(baud)])
        _run([sys.executable, tapfile, "--read", r])
        _run([sys.executable, omsx_run, "--machine", TAPE_MACHINE, "--cart", w,
              "--record", wav, "--bp", hex(DONE), "--reg", "PC",
              "--out", tempfile.mktemp(), "--timeout", "90"])
        _run([sys.executable, omsx_run, "--machine", TAPE_MACHINE, "--cart", r,
              "--cassette", wav, "--bp", hex(DONE), "--reg", "PC",
              "--mem", "memory:0xE000:28", "--out", cap, "--timeout", "90"])
        rc, out = _run([sys.executable, tapfile, "--analyze", cap])
        ok = (rc == 0) and ("MATCH" in out)
        detail = "two-block round-trip byte-identical" if ok else \
                 out.strip().splitlines()[-1]
    finally:
        for f in (w, r, wav, cap):
            if os.path.exists(f):
                os.unlink(f)
    return (f"round-trip write->read @{baud}", ok, detail)


def t_openstack(openstack, baud: int, zerobas: str) -> tuple[str, bool, str]:
    rc, out = _run([sys.executable, openstack, "--cart", zerobas,
                    "--baud", str(baud)])
    ok = (rc == 0) and ("PASS  open-stack BLOAD" in out)
    detail = "zerobas + C-BIOS + zerobas-tape, ,R handoff" if ok else \
             (out.strip().splitlines()[-1] if out.strip() else "no output")
    return (f"open-stack WAV BLOAD @{baud}", ok, detail)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--msx-preservation",
                    help="path to the msx-preservation repo "
                         "(default: sibling ../msx-preservation, or $MSX_PRESERVATION)")
    ap.add_argument("--zerobas",
                    default=os.path.expanduser("~/projects/zerobas/build/basic.rom"),
                    help="path to a built zerobas basic.rom (for the open-stack tests)")
    ap.add_argument("--skip-openstack", action="store_true",
                    help="skip the open-stack WAV tests (e.g. if zerobas isn't built)")
    args = ap.parse_args()

    msx_pres  = _find_msx_preservation(args.msx_preservation)
    omsx_run  = os.path.join(msx_pres, "tools", "omsx_run.py")
    tapfile   = os.path.join(msx_pres, "tools", "omsx", "bios_probe_tapfile.py")
    bload     = os.path.join(msx_pres, "basic-spec", "tools", "basic_probe_bload.py")
    openstack = os.path.join(msx_pres, "basic-spec", "tools",
                              "basic_probe_bload_openstack.py")

    tests = [
        lambda: t_cas_bload(bload),
        lambda: t_cas_readback(tapfile, omsx_run),
        lambda: t_roundtrip(omsx_run, tapfile, 1200),
        lambda: t_roundtrip(omsx_run, tapfile, 2400),
    ]
    if not args.skip_openstack:
        if not os.path.exists(args.zerobas):
            print(f"warning: zerobas not found at {args.zerobas}; "
                  "skipping open-stack tests (use --zerobas or --skip-openstack)\n",
                  file=sys.stderr)
        else:
            tests += [
                lambda: t_openstack(openstack, 1200, args.zerobas),
                lambda: t_openstack(openstack, 2400, args.zerobas),
            ]

    print("Tier-1 zerobas-tape full-stack regression\n")
    results = []
    for t in tests:
        name, ok, detail = t()
        results.append(ok)
        print(f"  [{'PASS' if ok else 'FAIL'}]  {name:34} {detail}")
    passed = sum(results)
    print(f"\n{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
