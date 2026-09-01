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
#
# 🔴 AND THEN NOBODY ASKED HOW MANY THERE WERE (D-GENFRESH, 2026-09-01). The
# subject of this file is not "patches" -- it is A GENERATED FILE THAT IS ALSO
# TRACKED, which can go stale in a commit while the build silently refreshes it
# for every reader. Enumerated from make's own database (a tracked path that is
# also a Makefile target, outside build/), the class has SIX members and this
# gate covered TWO:
#
#   zerobas-main-eu.{ips,bps}      covered  (deliverable "main")
#   tape/zerobas-tape-msx1.{ips,bps} covered  (deliverable "tape")
#   sub/basic-resident-abi.inc     NOT covered -- and STALE IN HEAD ACROSS 11
#                                  MAIN-ROM COMMITS when this was measured
#   sub/math-coeffs.inc            NOT covered (it happened to be fresh)
#
# The stale one is the sub-ROM's table of MAIN-ROM ADDRESSES. It self-heals on
# every build (its Makefile rule regenerates it from build/basic-reloc.sym), so
# nothing ever broke -- which is exactly why it went eleven commits: the only
# symptom is a working tree that is dirty the moment you build it, i.e. the
# noise that makes `git status` unreadable and `git add -A` tempting. The
# committed file meanwhile names wrong addresses to anyone who reads it.
# 🎯 THE FIX IS THE DENOMINATOR, NOT THE FILE. All four uncovered members are
# entered below; the class is now 6 of 6.
DELIVERABLES = [
    dict(name="main", needs_cbios=True, floor=20,
         make_target="build/zerobas-main-eu.rom",
         pair=["zerobas-main-eu.ips", "zerobas-main-eu.bps"],
         build=["--main"]),
    dict(name="tape", needs_cbios=False, floor=2,
         make_target="tape/zerobas-tape-msx1.ips",
         pair=["tape/zerobas-tape-msx1.ips", "tape/zerobas-tape-msx1.bps"],
         build=["--tape"]),
    # ⚠️ `make_target` IS THE STALENESS QUESTION, NOT THE SHIPPED FILE, and for
    # these two they are different files. `sub/basic-resident-abi.inc`'s own
    # prerequisites are just (the sym file, the generator) -- neither of which
    # is a tracked SOURCE, so a dirty check against them would be vacuous and
    # every mid-slice HEAD mismatch would read as a hard failure. The question
    # "may HEAD legitimately disagree right now?" is answered by the 61 tracked
    # sources of `build/basic-reloc.sym`, so that is what is asked.
    dict(name="abi", needs_cbios=False, floor=20,
         make_target="build/basic-reloc.sym",
         pair=["sub/basic-resident-abi.inc"],
         regen="abi", needs=["build/basic-reloc.sym"]),
    # The coefficients genuinely depend on nothing but their generator, so a
    # floor of 1 is the honest floor here rather than a weakened one -- and the
    # R != W clause catches an un-regenerated edit to it regardless.
    dict(name="coeffs", needs_cbios=False, floor=1,
         make_target="sub/math-coeffs.inc",
         pair=["sub/math-coeffs.inc"],
         regen="coeffs", subdir="sub"),
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
    for need in d.get("needs", []):
        if not (ROOT / need).exists():
            print(f"GATE-SKIPPED: {need} is not built, so the {label} artifact "
                  f"cannot be regenerated and its freshness is UNMEASURED. "
                  f"`make {need}` to measure it.")
            return 0
    if d["needs_cbios"] and cbios is None:
        print(f"GATE-SKIPPED: no C-BIOS checkout — the {label} artifact cannot "
              f"be regenerated, so its freshness is UNMEASURED. Point "
              f"CBIOS=<checkout> at one to measure it.")
        return 0
    for f in d["pair"]:
        if not (ROOT / f).exists():
            print(f"FAIL: {f} is missing from the tree. It is a generated "
                  f"deliverable; regenerate it with `make {f}`.")
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
        cwd = None
        if d.get("regen") == "abi":
            argv = [sys.executable, str(ROOT / "tools" / "gen_resident_abi.py"),
                    str(ROOT / "build" / "basic-reloc.sym"),
                    os.path.join(work, "basic-resident-abi.inc")]
        elif d.get("regen") == "coeffs":
            # 🎯 THE SHIPPED PATH, NOT THE DRY-RUN BRANCH. gen_math_coeffs.py
            # writes to the RELATIVE path `sub/math-coeffs.inc`, so running it
            # from `work` redirects `--emit` there and the gate scores the same
            # branch the Makefile does. Its dry run prints the same text and
            # would have been easier -- and would have left the only branch that
            # ever writes the tracked file unmeasured, on top of differing by a
            # trailing newline that a comparison would then have to forgive.
            os.makedirs(os.path.join(work, "sub"), exist_ok=True)
            argv, cwd = [sys.executable,
                         str(ROOT / "tools" / "gen_math_coeffs.py"), "--emit"], work
        else:
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
        p = subprocess.run(omsx_preflight.guarded(argv), cwd=cwd,
                           capture_output=True, text=True)
        if p.returncode != 0:
            print(f"INSTRUMENT: the {label} regeneration itself failed — nothing "
                  f"was measured:\n" + p.stdout[-3000:] + p.stderr[-3000:])
            return 2

        rc, notes = 0, []
        for f in d["pair"]:
            regen = (Path(work) / d.get("subdir", "") / Path(f).name).read_bytes()
            wc = (ROOT / f).read_bytes()
            head = head_blob(f)
            if regen != wc:
                # SIZES ARE NOT A DISCRIMINATOR HERE and the falsification is
                # what said so: both plants printed the same byte count on each
                # side. Ids are sha256[:8], the project's convention for a ROM.
                print(f"FAIL {f}: STALE IN YOUR TREE — the tracked file is "
                      f"{sid(wc)}, regenerating from the current sources gives "
                      f"{sid(regen)}. Run `make {f}` and commit it WITH "
                      f"the source change.")
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
                          f"clean, your working copy is fresh, and HEAD's copy is "
                          f"NOT — the build refreshed the file and the commit did "
                          f"not carry it. Stage and commit it.")
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
                    help="keep the regenerated file(s) for inspection")
    ap.add_argument("--only",
                    help="check just this one (" +
                         "|".join(d["name"] for d in DELIVERABLES) + ")")
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
