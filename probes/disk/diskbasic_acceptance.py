#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Disk-BASIC acceptance gate — the STANDING differential replay of the Disk-BASIC
verb surface. The BASIC-side counterpart of disk_bdos_acceptance.py.

Spec: disk/docs/diskbasic-acceptance-spec.md · scoreboard: disk/docs/diskbasic-verb-coverage.md

Unlike the BDOS gate (whose .COM exercisers need build-script command harvesting +
an address allowlist), every Disk-BASIC differential probe is a STANDALONE script
whose process exit code IS its verdict: each `disk_probe_*.py` does
`raise SystemExit(main())`, and `main()` boots the zerobas machine AND the CF-3300
reference (or, for the program loaders, compares against a real FAT12 artifact),
returning 0 on convergence / non-zero on divergence. So this runner is a thin
registry-driven subprocess dispatcher — no harvesting, no allowlist, no verdict
parsing. It runs each probe, gates on exit code, and prints an N/N scoreboard.

Two oracle styles, both dispatched identically (they differ only in the machine
each probe defaults to, which the runner leaves untouched):
  * live     — differential vs a running National_CF-3300 black box.
  * artifact — round-tripped against a real stock FAT12 image, read per public spec.

VACUITY GUARDS (the BDOS-gate lesson — a gate that can't go red is not a gate):
  1. The runner NEVER passes --no-ref; a probe with no oracle can't diverge. Any
     registry entry carrying --no-ref is rejected at startup.
  2. For a `live` probe, the run output MUST show the CF-3300 differential actually
     ran (the reference machine name appears in the probe's report); if it doesn't,
     the cell FAILS as VACUOUS even on exit 0.

HEAVY / oracle-dependent: boots openMSX (one or both machines) per probe, so it
needs the installed oracle machines (`make machines-oracle`), the seed FAT12 image
(`make test-dsk`), and your own CF-3300 reference ROMs — exactly like the other
probes under probes/README.md. NOT part of the emulator-free `make unit-test`.
Clean-room: stock is a black box; the probes + this runner are our own code.

Usage:
  python3 probes/disk/diskbasic_acceptance.py [--only FIELD] [--list] [--timeout S]
Exit: 0 = every gated probe converged; 1 = a divergence / probe error / vacuity.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TEST_DSK = os.path.join(ROOT, "disk", "test720.dsk")
DSK_COPY = "/tmp/zerobas_dbacc.dsk"          # /tmp copy so the committed image can't mutate
# live-oracle vacuity markers: a `live` probe MUST print evidence its CF-3300
# reference actually ran. Probes name it differently ("CF-3300 differential" vs
# "STOCK ran"), so accept any; matched case-insensitively.
REF_MARKERS = ("cf-3300", "stock")

# label -> (probe script, extra args, style). Extra args are almost always empty;
# each probe's own defaults pick the right machine. The set is the ✅ rows of
# disk/docs/diskbasic-verb-coverage.md §2 (kept in sync with that scoreboard).
REGISTRY = [
    # --- live CF-3300 differentials ---------------------------------------------
    ("FILES",          "disk_probe_files.py",           [], "live"),
    ("KILL",           "disk_probe_kill.py",            [], "live"),
    ("NAME",           "disk_probe_name.py",            [], "live"),
    ("MAXFILES",       "disk_probe_maxfiles.py",        [], "live"),
    ("MERGE",          "disk_probe_merge.py",           [], "live"),
    ("FIELD/LSET/RSET","disk_probe_field.py",           [], "live"),
    ("GET/PUT",        "disk_probe_getput.py",          [], "live"),
    ("GET(RDBLK)",     "disk_probe_rdblk_roundtrip.py", [], "live"),
    ("PUT(WRBLK)",     "disk_probe_wrblk_roundtrip.py", [], "live"),
    ("MKI$/CVI",       "disk_probe_mkicvi.py",          [], "live"),
    ("EOF/LOF",        "disk_probe_eof.py",             [], "live"),
    ("DSKF",           "disk_probe_dskf.py",            [], "live"),
    ("PRINT#",         "disk_probe_filewrite.py",       [], "live"),
    ("PRINT#-append",  "disk_probe_append.py",          [], "live"),
    ("INPUT#",         "disk_probe_fileread.py",        [], "live"),
    ("PRINT#-USING",   "disk_probe_printusing_file.py", [], "live"),
    ("INPUT$",         "disk_probe_inputdollar.py",     [], "live"),
    # CALL FORMAT is a STRUCTURAL self-check (asserts the formatted BPB/FAT bytes vs
    # the FAT12 spec), not a live CF-3300 differential — hence "artifact", no ref marker.
    ("CALL FORMAT",    "disk_probe_format.py",          [], "artifact"),
    # --- read-only FAT12-artifact oracle ----------------------------------------
    ("SAVE/BSAVE",     "disk_probe_save.py",            [], "artifact"),
    ("LOAD",           "disk_probe_load_disk.py",       [], "artifact"),
    ("LOAD(NUL)",      "disk_probe_load_embedded_nul.py",[], "artifact"),
    ("RUN\"file\"",    "disk_probe_run_disk.py",        [], "artifact"),
    ("BLOAD",          "disk_probe_bload_disk.py",      [], "artifact"),
]


def _check_registry() -> None:
    """Vacuity guard 1: reject any entry that would skip the oracle."""
    for label, script, extra, _style in REGISTRY:
        if "--no-ref" in extra:
            sys.exit(f"registry error: {label} ({script}) carries --no-ref — a probe "
                     f"with no oracle cannot diverge (vacuity guard §3.1.1)")
        if not os.path.isfile(os.path.join(HERE, script)):
            sys.exit(f"registry error: {label}: missing probe {script}")


def run_probe(script: str, extra: list[str], env: dict, timeout: float) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["python3", os.path.join(HERE, script), *extra],
            cwd=ROOT, capture_output=True, text=True, env=env, timeout=timeout)
        return proc.returncode, proc.stdout + proc.stderr
    except subprocess.TimeoutExpired as e:
        return 124, (e.output or "") + f"\n[runner] TIMEOUT after {timeout:.0f}s"


def gate(style: str, rc: int, out: str) -> tuple[bool, str]:
    """Pass/fail for one probe. Exit code is the verdict; live probes also get the
    oracle-ran vacuity check (guard §3.1.2)."""
    if rc != 0:
        # surface the probe's own last verdict line if present
        fail = next((l for l in reversed(out.splitlines())
                     if "FAIL" in l or "DIVERG" in l or "TIMEOUT" in l), None)
        return False, (fail.strip() if fail else f"exit {rc}")
    if style == "live" and not any(mk in out.lower() for mk in REF_MARKERS):
        return False, ("VACUOUS — exit 0 but no oracle evidence in output "
                       "(reference/stock differential never ran)")
    return True, "converged"


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", action="append",
                    help="run only this verb label or probe stem (repeatable)")
    ap.add_argument("--list", action="store_true",
                    help="print the registry/plan without running any probe")
    ap.add_argument("--timeout", type=float, default=240.0,
                    help="per-probe timeout in seconds (default 240)")
    args = ap.parse_args()

    _check_registry()

    if args.list:
        print("Disk-BASIC acceptance registry:")
        for label, script, extra, style in REGISTRY:
            print(f"  [{style:8}] {label:16} -> {script} {' '.join(extra)}".rstrip())
        print(f"\n{len(REGISTRY)} probes (plan only — nothing run)")
        return 0

    # /tmp copy so the artifact probes can't mutate the committed seed image.
    env = dict(os.environ)
    if os.path.isfile(TEST_DSK):
        shutil.copyfile(TEST_DSK, DSK_COPY)
        env["DISK_DSK"] = DSK_COPY
    else:
        print(f"WARNING: seed image {TEST_DSK} missing (run `make test-dsk`) — "
              f"artifact probes may fail", file=sys.stderr)

    wanted = {w.upper() for w in args.only} if args.only else None
    passed = failed = 0
    failures = []

    for label, script, extra, style in REGISTRY:
        stem = script[:-3]
        if wanted and label.upper() not in wanted and stem.upper() not in wanted:
            continue
        rc, out = run_probe(script, extra, env, args.timeout)
        ok, why = gate(style, rc, out)
        print(f"  {'PASS' if ok else 'FAIL'}  [{style:8}] {label:16} {why}")
        if ok:
            passed += 1
        else:
            failed += 1
            failures.append(f"{label} ({script}): {why}")
            print("    --- probe tail ---\n" +
                  "\n".join("    " + l for l in out.splitlines()[-12:]))

    total = passed + failed
    # disk-mutation guard: the committed seed must be untouched (test-disk-mutation-gotcha).
    dirty = subprocess.run(["git", "status", "--porcelain", "disk/test720.dsk"],
                           cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if dirty:
        print(f"\nWARNING: {TEST_DSK} was modified by the run — restore with "
              f"`git checkout -- disk/test720.dsk`")

    print(f"\n===== Disk-BASIC acceptance: {passed}/{total} verbs converged =====")
    if failed:
        print("DIVERGENCE — the Disk-BASIC verb surface no longer matches the oracle:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL CONVERGED — the Disk-BASIC verb surface still matches the oracle.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
