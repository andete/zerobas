#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""check_patch_freshness.py — the shipped BASIC deliverable must match the
sources that are committed beside it.

`zerobas-main-eu.ips` / `.bps` ARE the shipped BASIC (Makefile header): the
merged repack main ROM diffed against the pristine stock C-BIOS from the pinned
tag. `make release` regenerates them, and the Makefile calls that "the
maintainer's step before committing a basic/ change". Nothing enforced it.

Filed 2026-08-26 by D-EVFERR, which shipped TWO ROM-moving commits without
regenerating the pair — and `make gates` went 38/38 green BOTH times. Getting it
wrong takes nothing more exotic than `git add <paths>` instead of `git add -A`.
🎯 THE OMISSION IS NOT WHAT NEEDS FIXING — THE BLINDNESS IS.

WHY IT REGENERATES INSTEAD OF LOOKING AT THE TREE. `build_patches.py --main`
writes the pair IN PLACE at the repo root, and `$(MAIN_ROM)` is a real file rule
every gate depends on — so by the time a battery finishes, the WORKING COPY of
the pair has already been refreshed. A check that compared the working copy
against the sources would therefore be structurally blind to the filed defect:
the defect lives in what was COMMITTED. So this regenerates hermetically (through
build_patches.py's own code path, into a temp dir, touching neither `build/` nor
the tracked files) and compares against BOTH the working copy and HEAD.

THE THREE STATES (R = regenerated, W = working copy, H = the blob at HEAD):

  R != W            STALE IN YOUR TREE. You changed a source and the pair was
                    never rebuilt. Always a finding. -> `make patches`
  R == W, W != H,
    sources CLEAN   STALE IN THE LAST COMMIT — the D-EVFERR shape exactly: the
                    build refreshed your working copy, the commit did not carry
                    it. -> stage the pair and amend/commit it
  R == W, W != H,
    sources DIRTY   DEFERRED, and said out loud. You are mid-slice with
                    uncommitted sources; HEAD is *expected* to disagree. The
                    working-copy clause above still ran.

"sources CLEAN" is asked of MAKE, not of a hand-written list: the prerequisites
of `$(MAIN_ROM)` come out of `make -pn`'s database, so the condition follows the
Makefile instead of rotting beside it.
⚠️ IT IS THEREFORE ONLY AS COMPLETE AS THAT PREREQUISITE LIST, WHICH HAS BEEN
WRONG BEFORE (basic/tokenise.inc and basic/detok.inc were missing from $(DEPS)
until the math-pack slice; str-engine.asm/input.asm before that). A source that
is missing from the list reads as "clean" — and the check then compares R
against H and goes RED, which points at the real gap. The failure direction is
loud, not silent.

SKIP, NEVER PASS. Regenerating needs a C-BIOS checkout (CBIOS=<path>), and
`patches` is deliberately NOT a prerequisite of `machines` so the build stays
usable without one (docs/spec-lean-retire-s2-switch.md §4.4). With no checkout
this prints `GATE-SKIPPED:` and exits 0 — and `tools/run_gates.py` reads that
sentinel and counts the unit as SKIPPED, not green. A check that silently passes
when it cannot run is the 0/0-ALL-CONVERGED shape and is worse than nothing.

Exit status: 0 = fresh (or skipped), 1 = stale, 2 = the INSTRUMENT is broken
(git unusable, the regeneration itself failed, the prerequisite query came back
empty).

Usage:  python3 tools/check_patch_freshness.py [--cbios PATH] [--keep]
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "probes" / "lib"))
import probe_tmp                       # noqa: E402,F401  (sets tempfile.tempdir)
import omsx_preflight                  # noqa: E402

# TWO shipped patch deliverables, not one. The tape pair was filed as "unguarded
# by the same rule": same three-way comparison, a different target and a
# different prerequisite list.
# 🎯 AND A DIFFERENT SKIP CONDITION, which is the part worth noticing: the MAIN
# pair needs a C-BIOS SOURCE CHECKOUT to regenerate, the TAPE pair only needs a
# stock ROM, which `resolve_stock()` finds inside openMSX. So the tape half is
# measurable on machines where the main half must skip -- folding them under one
# skip would have silently un-measured it.
DELIVERABLES = [
    dict(name="main", needs_cbios=True, floor=20,
         make_target="build/zerobas-main-eu.rom",
         pair=["zerobas-main-eu.ips", "zerobas-main-eu.bps"],
         build=["--main"]),
    dict(name="tape", needs_cbios=False, floor=2,
         make_target="tape/zerobas-tape-msx1.ips",
         pair=["tape/zerobas-tape-msx1.ips", "tape/zerobas-tape-msx1.bps"],
         build=["--tape"]),
]


def sid(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:8]


def git(*args, check=True):
    p = subprocess.run(["git", "-C", str(ROOT), *args],
                       capture_output=True, text=True)
    if check and p.returncode != 0:
        print(f"INSTRUMENT: git {' '.join(args)} failed:\n{p.stderr}")
        sys.exit(2)
    return p


def prereqs_of(target: str) -> list[str]:
    """A target's prerequisites, straight out of make's own database."""
    p = subprocess.run(["make", "-pn", target],
                       cwd=ROOT, capture_output=True, text=True)
    for line in p.stdout.splitlines():
        if line.startswith(target + ":"):
            rhs = line.split(":", 1)[1]
            rhs = rhs.split("|", 1)[0]          # drop order-only prerequisites
            return sorted(set(rhs.split()))
    return []


def dirty_tracked(paths: list[str]) -> list[str]:
    """Which of `paths` differ from HEAD (staged or not)."""
    if not paths:
        return []
    out = git("status", "--porcelain", "--untracked-files=no", "--", *paths).stdout
    return sorted(line[3:].strip() for line in out.splitlines() if line.strip())


def head_blob(path: str) -> bytes | None:
    p = subprocess.run(["git", "-C", str(ROOT), "show", f"HEAD:{path}"],
                       capture_output=True)
    return p.stdout if p.returncode == 0 else None


def check(d, cbios, keep) -> int:
    """One deliverable: regenerate hermetically, compare against tree AND HEAD."""
    label = d["name"]
    if d["needs_cbios"] and cbios is None:
        print(f"GATE-SKIPPED: no C-BIOS checkout — the {label} patch pair cannot "
              f"be regenerated, so its freshness is UNMEASURED. Point "
              f"CBIOS=<checkout> at one to measure it.")
        return 0
    for f in d["pair"]:
        if not (ROOT / f).exists():
            print(f"FAIL: {f} is missing from the tree. It is a shipped "
                  f"deliverable; regenerate it with `make patches`.")
            return 1
    prereqs = prereqs_of(d["make_target"])
    if len(prereqs) < d["floor"]:
        print(f"INSTRUMENT: make reported {len(prereqs)} prerequisite(s) for "
              f"{d['make_target']}, floor is {d['floor']}. The sources-clean "
              f"condition would be vacuously true.")
        return 2
    dirty = dirty_tracked(prereqs)

    work = tempfile.mkdtemp(prefix=f"patch-freshness-{label}-")
    try:
        print(f"[{label}] regenerating from {len(prereqs)} source(s) into {work} ...")
        argv = [sys.executable, str(ROOT / "tools" / "build_patches.py"),
                *d["build"], "--out-dir", work]
        if d["needs_cbios"]:
            argv += ["--cbios", str(cbios)]
        # 🔴 A LIST LITERAL IS EXEMPT BY CONSTRUCTION; A VARIABLE IS NOT.
        # Generalising the single hardcoded pair into a DELIVERABLES loop turned
        # this spawn from a literal into `argv`, and `make preflight-check` went
        # red -- it can no longer read the argv and prove it is not an emulator
        # launch. guarded() is a passthrough here, and it is what the rule
        # requires of every spawn site (docs/spec-probe-preflight.md §3.5).
        p = subprocess.run(omsx_preflight.guarded(argv),
                           capture_output=True, text=True)
        if p.returncode != 0:
            print(f"INSTRUMENT: the {label} regeneration itself failed — nothing "
                  f"was measured:\n" + p.stdout[-3000:] + p.stderr[-3000:])
            return 2

        rc, notes = 0, []
        for f in d["pair"]:
            regen = (Path(work) / Path(f).name).read_bytes()
            wc = (ROOT / f).read_bytes()
            head = head_blob(f)
            if regen != wc:
                # SIZES ARE NOT A DISCRIMINATOR HERE and the falsification is
                # what said so: both plants printed the same byte count on each
                # side. Ids are sha256[:8], the project's convention for a ROM.
                print(f"FAIL {f}: STALE IN YOUR TREE — the tracked file is "
                      f"{sid(wc)}, regenerating from the current sources gives "
                      f"{sid(regen)}. Run `make patches` and commit the pair "
                      f"WITH the source change.")
                rc = 1
            elif head is None:
                notes.append(f"{f}: not in HEAD (new file) — working copy fresh.")
            elif regen != head:
                if dirty:
                    notes.append(f"{f}: working copy fresh; the HEAD comparison "
                                 f"is DEFERRED — {len(dirty)} source(s) are "
                                 f"uncommitted ({', '.join(dirty[:4])}"
                                 f"{' …' if len(dirty) > 4 else ''}).")
                else:
                    print(f"FAIL {f}: STALE IN THE LAST COMMIT. Every source is "
                          f"clean, your working copy of the pair is fresh, and "
                          f"HEAD's copy is NOT — the build refreshed the file and "
                          f"the commit did not carry it. Stage and commit it.")
                    rc = 1
            else:
                notes.append(f"{f}: fresh in the tree and at HEAD "
                             f"({sid(regen)}, {len(regen)} B).")
        for n in notes:
            print("  " + n)
        return rc
    finally:
        if keep:
            print(f"  (kept: {work})")
        else:
            shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cbios", default=os.environ.get("CBIOS", "~/projects/cbios"),
                    help="C-BIOS checkout (default $CBIOS or ~/projects/cbios)")
    ap.add_argument("--keep", action="store_true",
                    help="keep the regenerated pair for inspection")
    ap.add_argument("--only", help="check just this deliverable (main|tape)")
    a = ap.parse_args()

    c = Path(os.path.expanduser(a.cbios))
    cbios = c if ((c / ".git").exists() or (c / "src").exists()) else None

    ds = [d for d in DELIVERABLES if not a.only or d["name"] == a.only]
    if not ds:
        sys.exit(f"no such deliverable: {a.only}")
    worst = 0
    for d in ds:
        rc = check(d, cbios, a.keep)
        worst = 2 if 2 in (worst, rc) else max(worst, rc)
    if worst == 0:
        names = "/".join(d["name"] for d in ds)
        print(f"patch-freshness: the shipped {names} deliverable(s) match their "
              f"sources.")
    return worst


if __name__ == "__main__":
    sys.exit(main())
