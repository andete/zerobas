#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Falsification for tools/check_patch_freshness.py (docs/spec-patch-freshness-gate.md).

⚠️ EVERY ARM RUNS IN A THROWAWAY `git clone --local` UNDER /tmp/zerobas, never in
the working tree: two of the arms have to COMMIT (the filed defect is a property
of what was committed, not of the worktree), and a falsification may not leave
commits behind. The clone is seeded with the working tree's copy of the tools so
an uncommitted fix can be scored.

THE ARMS — the subject has four states and each one is planted:

  G1  clean, pair fresh                        -> green
  P1  a byte flipped in the tracked .ips       -> RED  "STALE IN YOUR TREE"
  P2  a source edited, pair NOT rebuilt        -> RED  "STALE IN YOUR TREE"
  P3  D-EVFERR: source COMMITTED, pair rebuilt
      but NOT committed                        -> RED  "STALE IN THE LAST COMMIT"
  P3b the same, after committing the pair      -> green   (a red that cannot be
                                                           cleared is not a gate)
  G2  a source DIRTY, pair rebuilt             -> green + DEFERRED, said out loud
  S1  no C-BIOS checkout                       -> GATE-SKIPPED, rc 0
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "probes" / "lib"))
import probe_tmp                        # noqa: E402,F401

CLONE = Path("/tmp/zerobas/patchfresh_falsify_clone")
CBIOS = os.environ.get("CBIOS", os.path.expanduser("~/projects/cbios"))
SEED = ["tools/check_patch_freshness.py", "tools/build_patches.py", "Makefile"]
# A one-byte data-table plant: it moves the merged ROM without moving any label
# the assembler will refuse. `stmt_table`'s first entry is stable ground.
ANCHOR = "stmt_table:\n                db      COLON\n"


def sh(argv, cwd=CLONE, **kw):
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, **kw)


def git(*args, cwd=CLONE):
    p = sh(["git", "-c", "user.email=falsify@zerobas", "-c", "user.name=falsify",
            *args], cwd=cwd)
    if p.returncode != 0:
        sys.exit(f"clone git {' '.join(args)} failed:\n{p.stderr}")
    return p


def check(cbios=CBIOS):
    p = sh([sys.executable, "tools/check_patch_freshness.py", "--cbios", cbios])
    return p.returncode, p.stdout + p.stderr


def regenerate():
    p = sh([sys.executable, "tools/build_patches.py", "--main", "--cbios", CBIOS])
    if p.returncode != 0:
        sys.exit(f"clone regeneration failed:\n{p.stdout[-2000:]}{p.stderr[-2000:]}")


def arm(label, want_rc, want_in, cbios=CBIOS):
    rc, out = check(cbios)
    ok = rc == want_rc and (want_in in out)
    print(f"  {'PASS' if ok else 'FAIL'}  {label}: rc={rc} (want {want_rc}), "
          f"{'found' if want_in in out else 'MISSING'} {want_in!r}")
    if not ok:
        print("    " + "\n    ".join(out.splitlines()[-12:]))
    return ok


def main():
    if not Path(CBIOS).exists():
        sys.exit(f"no C-BIOS checkout at {CBIOS}; the RED arms cannot run.")
    shutil.rmtree(CLONE, ignore_errors=True)
    CLONE.parent.mkdir(parents=True, exist_ok=True)
    p = sh(["git", "clone", "--quiet", "--local", "--no-hardlinks",
            str(ROOT), str(CLONE)], cwd=str(ROOT))
    if p.returncode != 0:
        sys.exit(f"clone failed:\n{p.stderr}")
    for f in SEED:                       # score the WORKING TREE's tools
        shutil.copy2(ROOT / f, CLONE / f)
    git("add", "-A"); git("commit", "-q", "-m", "seed: the tools under test")

    r = []
    print("=== G1: clean tree, pair fresh ===")
    r.append(arm("green control", 0, "fresh in the tree and at HEAD"))

    print("=== P1: a byte flipped in the tracked .ips ===")
    ips = CLONE / "zerobas-main-eu.ips"
    keep = ips.read_bytes()
    b = bytearray(keep); b[len(b) // 2] ^= 0xFF; ips.write_bytes(bytes(b))
    r.append(arm("stale in tree (file corrupted)", 1, "STALE IN YOUR TREE"))
    ips.write_bytes(keep)

    print("=== P2: a source edited, the pair never rebuilt ===")
    src = CLONE / "basic" / "interp.asm"
    pristine = src.read_text()
    assert ANCHOR in pristine, "anchor moved — the plant would not cut"
    src.write_text(pristine.replace(ANCHOR, ANCHOR + "                db      0\n"))
    r.append(arm("stale in tree (source ahead)", 1, "STALE IN YOUR TREE"))

    print("=== P3: D-EVFERR — source committed, pair regenerated but not ===")
    regenerate()
    git("add", "basic/interp.asm")
    git("commit", "-q", "-m", "plant: a ROM-moving change, pair not carried")
    r.append(arm("stale in the last commit", 1, "STALE IN THE LAST COMMIT"))

    print("=== P3b: the same red, cleared the documented way ===")
    git("add", "zerobas-main-eu.ips", "zerobas-main-eu.bps")
    git("commit", "-q", "-m", "plant: carry the pair")
    r.append(arm("red clears when the pair is committed", 0,
                 "fresh in the tree and at HEAD"))

    print("=== G2: a source DIRTY, pair rebuilt -> deferred, said out loud ===")
    src.write_text(src.read_text().replace("                db      0\n",
                                           "                db      1\n"))
    regenerate()
    r.append(arm("HEAD comparison deferred", 0, "DEFERRED"))

    print("=== S1: no C-BIOS checkout -> SKIPPED, never a silent pass ===")
    git("checkout", "-q", ".")
    r.append(arm("skip sentinel", 0, "GATE-SKIPPED:",
                 cbios="/tmp/zerobas/no-such-cbios"))

    print(f"\n{sum(r)}/{len(r)} arms as predicted")
    shutil.rmtree(CLONE, ignore_errors=True)
    return 0 if all(r) else 1


if __name__ == "__main__":
    sys.exit(main())
