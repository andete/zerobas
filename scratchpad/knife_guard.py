#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-KNIFEROM — a knife that did not reach the ROM must say so, not say "0 rows".

🔴 THE FAILURE THIS EXISTS TO MAKE LOUD. A knife writes a source file and invokes
`make`; if the rebuild does not actually happen, the probe measures the PREVIOUS
machine and the runner reports **"moved 0 row(s)"** -- which is exactly what an
arm that legitimately found nothing looks like. That verdict is the one that gets
written into a spec as evidence. Measured on 2026-08-28: running one runner twice
on an unchanged tree gave TWO DIFFERENT ANSWERS, and the wrong run's output was
byte-identical to the PREVIOUS knife's (docs/spec-basic-ngram2.md §3). Build
non-determinism was excluded first -- three consecutive builds are byte-identical
and converge in one pass.

🎯 THE CONVENTION ALREADY EXISTED AND I DID NOT INHERIT IT. This module is not a
new idea: 36 of 41 knife runners in `scratchpad/` already hash the built images,
and the established shape (`circmiss_knives.py`) also does `rm -rf build` first so
the rebuild cannot be skipped. Several specs already distinguish *"the cut reached
the artifact and reddened nothing"* -- a finding -- from *"the cut never
happened"*. What this module adds is ONE implementation for the five runners that
had none, and a gate so the next runner cannot quietly omit it.

Usage in a runner:

    import knife_guard
    ...
    before = knife_guard.hashes()
    ok, after, rc = knife_guard.build(f"{TMP}/mk_{tag}.log", before)
    if rc:        -> the build FAILED
    if not ok:    -> the cut is INERT; do not score it
"""
from __future__ import annotations

import hashlib
import os
import subprocess

# The images a `repack-machine` produces. build/disk.rom is included on purpose:
# the machine config names FOUR ROMs and the battery's own list omitted it until
# 2026-08-28 (docs/spec-gateskip.md §4).
IMAGES = ("build/zerobas-main-eu.rom", "build/sub.rom", "build/disk.rom",
          "build/basic-reloc.rom")


def hashes(images=IMAGES) -> str:
    return " ".join(
        (hashlib.sha256(open(p, "rb").read()).hexdigest()[:8]
         if os.path.exists(p) else "ABSENT") for p in images)


def build(log: str, before: str | None = None, *, clean: bool = False):
    """Rebuild; report whether the ROM actually MOVED. -> (moved, after, rc)

    `clean=True` does `rm -rf build` first, the belt-and-braces the established
    runners use. It is off by default because it costs a full rebuild per knife
    and the hash comparison already CATCHES the failure it prevents -- but a
    runner that would rather not think about it can just pass clean=True.
    """
    os.makedirs(os.path.dirname(log) or ".", exist_ok=True)
    if clean:
        subprocess.call("rm -rf build", shell=True)
    with open(log, "w") as fh:
        rc = subprocess.call("make repack-machine", shell=True,
                             stdout=fh, stderr=subprocess.STDOUT)
    after = hashes()
    return moved(before, after), after, rc


def moved(before: str | None, after: str) -> bool:
    """🔴 `before is None` MUST NOT COUNT AS "moved". A caller that forgets to
    take a baseline gets False, not a free pass: the absence of evidence is not
    evidence. Split out from `build` so the selftest can EXERCISE the decision
    instead of asserting that the function exists -- the first cut of K4 checked
    `build.__defaults__ is not None`, which is a vacuous pass of exactly the kind
    this whole module is about."""
    return before is not None and after != before


def report(tag: str, moved: bool, before: str, after: str) -> str:
    if moved:
        return f"  ROM {before}  ->  {after}"
    return (f"  🔴 {tag}: KNIFE INERT — the ROM did not change ({after}); the "
            f"probe would measure the UNCUT machine, and any 'moved 0 rows' "
            f"below would be meaningless")


# --------------------------------------------------------------------------
# --- pattern_alive: the control an "expect 0" S1 arm cannot do without ------
# 🔴 FOUND 2026-08-29 (D-N8ARM): 2 of 7 ngram S1 arms carried a STALE pattern
# element -- a form that no longer occurs anywhere in the tree. What that costs
# depends entirely on which way the arm's expected count points, and the two
# cases here landed on opposite sides:
#   ngram8  expects **0** open-coded runs -> VACUOUS. `jp nc,str_eval_no` was
#           replaced by `jp nc,sas_decline` when the `pop af` fix landed after
#           the arm was written; the pattern then matched nothing, reported 0,
#           and read exactly like a clean tree.
#   ngram7  expects **1** (the body itself is the surviving copy) -> RED, and
#           loudly so -- but nobody had run the file since. Its element
#           `ld ix,... + 3*...` was written to match the OUTPUT OF A BUGGY
#           NORMALISER: `ngram_sweep.py`'s key normalisation had a doubled
#           backslash (`r'\\s+'`) and never stripped whitespace, so fixing that
#           regex on 2026-08-28 invalidated the pattern. A REPAIR TO THE
#           INSTRUMENT BROKE A GATE THAT READ IT.
# 🎯 So the hazard is not "stale patterns pass" -- it is that a stale pattern's
# verdict is decided by an unrelated design choice (which way the count points)
# instead of by the tree. This control removes that coupling.
# ⚠️ D-NGRAM7 already added a control for this class -- but it checked only
# PAT[0], so a stale element ANYWHERE ELSE still passed. Check every element.
# 🟢 Element-presence is NECESSARY, not sufficient: the elements can each exist
# while the SEQUENCE does not. It is the cheap half, and it is the half that was
# missing. [[a-case-that-agrees-can-agree-for-the-wrong-reason]]
def pattern_alive(pat, forms):
    """-> (ok, missing) — every element of `pat` occurs in the tree's `forms`."""
    forms = set(forms)
    missing = [e for e in pat if e not in forms]
    return (not missing), missing


def _selftest() -> int:
    r"""The arms that matter: a real change must read as MOVED, and everything
    else -- no change, a missing baseline, an absent image -- must NOT."""
    import tempfile
    fails = []

    def arm(name, cond, detail=""):
        print(f"{'PASS' if cond else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")
        if not cond:
            fails.append(name)

    d = tempfile.mkdtemp(prefix="knifeguard-")
    a, b = os.path.join(d, "a.rom"), os.path.join(d, "b.rom")
    open(a, "wb").write(b"\x00" * 64)
    open(b, "wb").write(b"\x11" * 64)
    imgs = (a, b)
    h0 = hashes(imgs)
    arm("K1 identical bytes hash identically (green control)", hashes(imgs) == h0, h0)
    open(b, "wb").write(b"\x11" * 63 + b"\x12")          # ONE byte
    arm("K2 one byte of one image -> a different reading", hashes(imgs) != h0)
    open(b, "wb").write(b"\x11" * 64)
    arm("K2b restoring it restores the reading (control)", hashes(imgs) == h0)
    os.unlink(b)
    arm("K3 a MISSING image reads ABSENT, never a silent match",
        "ABSENT" in hashes(imgs) and hashes(imgs) != h0)
    # the decision function itself
    arm("K4 no baseline -> NOT moved (absence of evidence is not evidence)",
        moved(None, "aa") is False)
    arm("K4b a changed reading -> moved", moved("aa", "bb") is True)
    arm("K4c an unchanged reading -> NOT moved", moved("aa", "aa") is False)
    arm("K5 equal before/after -> INERT wording names the risk",
        "INERT" in report("t", False, "aa", "aa")
        and "UNCUT" in report("t", False, "aa", "aa"))
    arm("K6 moved -> the transition is PRINTED, not just asserted",
        "->" in report("t", True, "aa", "bb"))
    forms = {"call foo", "jp nz,bar"}
    arm("K7 a pattern whose elements all exist is alive",
        pattern_alive(["call foo", "jp nz,bar"], forms) == (True, []))
    arm("K8 a STALE element is named, not silently tolerated",
        pattern_alive(["call foo", "jp nc,gone"], forms) == (False, ["jp nc,gone"]))
    arm("K9 a stale element in a LATER position is caught too (the D-NGRAM7 hole)",
        pattern_alive(["call foo", "jp nz,bar", "ld a,gone"], forms)[0] is False)
    import shutil
    shutil.rmtree(d, ignore_errors=True)
    print()
    print("ALL PASS — knife_guard" if not fails else f"🔴 {len(fails)} FAILED: {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_selftest())
