#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""BDOSX acceptance gate — the STANDING differential replay of the whole BDOS surface.

The BDOSX/BDOSX2/BDOSX3/BDOSX0 exercisers (disk/docs/tier2-bdos-coverage.md) each
drive a block of MSX-DOS-1 BDOS functions from a real `.COM` and were proven
0-byte-identical to stock ONCE, during the M19-M26 milestone chain. This turns
those one-shot proofs into a re-runnable gate: for every exerciser it (re)builds
the throwaway disk and replays the SAME differential the build script prints, then
asserts convergence — so "proven once" becomes "proven every release".

The build scripts are the single source of truth for the exact probe invocations
(the anchors/regions are computed from freshly-assembled symbol addresses), so this
runner does NOT duplicate them: it runs each `build_bdosx*_disk.py`, harvests the
`disk_probe_diff.py ...` command lines it emits, and executes them. Two assertion
styles, by probe mode:

  * `capture` — diffs a memory region on ours vs stock; the probe already exits 1
    on any byte-diff, so its exit code IS the gate.
  * `callseq` — compares the BDOS call sequence; the probe always exits 0, so we
    gate on its "ALIGNED, NO DIVERGENCE" verdict line.
  * `screen`  — prints both machines' screens for human comparison only (no machine
    verdict); run for the record but NOT gated (skipped unless --with-screen).

HEAVY / oracle-dependent: boots openMSX for BOTH machines per probe, so it needs
the installed oracle machines (`make machines-oracle`) and your own CF-3300
reference ROMs — exactly like the other probes under probes/README.md. Not part of
the fast emulator-free `make unit-test`. Clean-room: stock is a black box; the
exercisers + this runner are our own code, diffed against the stock oracle.

Usage:
  python3 probes/disk/disk_bdos_acceptance.py [--dos-disk test.dsk] [--only BDOSX3]
                                              [--with-screen] [--list]
Exit: 0 = every gated differential converged; 1 = a divergence / build/probe error.
"""
from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DEFAULT_DOS_DISK = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")

# name -> build script; each emits the disk_probe_diff.py command(s) to replay.
EXERCISERS = [
    ("BDOSX",  "build_bdosx_disk.py"),
    ("BDOSX2", "build_bdosx2_disk.py"),
    ("BDOSX3", "build_bdosx3_disk.py"),
    ("BDOSX0", "build_bdosx0_disk.py"),
]

CMD_RE = re.compile(r"(python3\s+probes/disk/disk_probe_diff\.py\s+.*)$")


def build_and_plan(name: str, script: str, dos_disk: str) -> tuple[list[list[str]], str]:
    """Run the build script; return (list of probe arg-lists, its raw output)."""
    out_dsk = f"/tmp/zerobas_acc_{name.lower()}.dsk"
    proc = subprocess.run(
        ["python3", os.path.join(HERE, script), "--dos-disk", dos_disk, "--out", out_dsk],
        cwd=ROOT, capture_output=True, text=True)
    blob = proc.stdout + proc.stderr
    if proc.returncode != 0:
        raise RuntimeError(f"{script} failed (exit {proc.returncode}):\n{blob}")
    cmds = []
    for line in blob.splitlines():
        m = CMD_RE.search(line.strip())
        if m:
            cmds.append(shlex.split(m.group(1))[1:])   # drop the leading "python3"
    if not cmds:
        raise RuntimeError(f"{script} emitted no disk_probe_diff.py commands:\n{blob}")
    return cmds, blob


def mode_of(argv: list[str]) -> str:
    for a in argv[1:]:                 # argv[0] == "probes/disk/disk_probe_diff.py"
        if not a.startswith("-"):
            return a
    return "?"


def gate(mode: str, rc: int, out: str) -> tuple[bool, str]:
    """Pass/fail verdict for one probe run, by mode."""
    if mode == "capture":
        return rc == 0, ("0-byte-diff" if rc == 0 else "BYTE-DIFF (probe exit 1)")
    if mode == "callseq":
        if "NO DIVERGENCE" in out:
            return True, "ALIGNED, no divergence"
        m = re.search(r"FIRST DIVERGENCE.*", out)
        return False, (m.group(0) if m else "no ALIGNED verdict emitted")
    return True, "screen (not gated)"


def run_probe(argv: list[str]) -> tuple[int, str]:
    proc = subprocess.run(["python3"] + argv, cwd=ROOT, capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", default=DEFAULT_DOS_DISK,
                    help="source MSX-DOS 1 disk the exercisers run from (default: test.dsk)")
    ap.add_argument("--only", action="append",
                    help="run only this exerciser (repeatable), e.g. --only BDOSX3")
    ap.add_argument("--with-screen", action="store_true",
                    help="also run the (non-gated) screen probes")
    ap.add_argument("--list", action="store_true",
                    help="build + print the replay plan without running any probe")
    args = ap.parse_args()

    if not os.path.isfile(args.dos_disk):
        print(f"DOS source disk not found: {args.dos_disk}", file=sys.stderr)
        return 1
    # work off a /tmp copy of the DOS source so the committed oracle can't mutate.
    dos_copy = "/tmp/zerobas_acc_src.dsk"
    shutil.copyfile(args.dos_disk, dos_copy)

    wanted = {n.upper() for n in args.only} if args.only else None
    total = passed = failed = skipped = 0
    failures = []

    for name, script in EXERCISERS:
        if wanted and name not in wanted:
            continue
        print(f"\n===== {name} ({script}) =====")
        try:
            cmds, _ = build_and_plan(name, script, dos_copy)
        except RuntimeError as e:
            print(f"  BUILD-ERROR: {e}")
            failed += 1
            failures.append(f"{name}: build error")
            continue
        for argv in cmds:
            mode = mode_of(argv)
            region = next((argv[i + 1] for i, a in enumerate(argv) if a == "--mem"), "")
            label = f"{name} {mode}" + (f" {region}" if region else "")
            if mode == "screen" and not args.with_screen:
                print(f"  SKIP  {label} (screen; not gated — use --with-screen)")
                skipped += 1
                continue
            if args.list:
                print(f"  PLAN  {label}: {' '.join(argv)}")
                continue
            total += 1
            rc, out = run_probe(argv)
            ok, why = gate(mode, rc, out)
            print(f"  {'PASS' if ok else 'FAIL'}  {label}: {why}")
            if ok:
                passed += 1
            else:
                failed += 1
                failures.append(f"{label}: {why}")
                tail = "\n".join(out.splitlines()[-12:])
                print(f"    --- probe tail ---\n{tail}")

    if args.list:
        print("\n(plan only — no probes run)")
        return 0

    print(f"\n===== BDOSX acceptance: {passed}/{total} gated differentials converged "
          f"({skipped} screen skipped) =====")
    if failed:
        print("DIVERGENCE — the BDOS surface no longer matches stock:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL CONVERGED — the BDOS surface still matches the stock oracle byte-for-byte.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
