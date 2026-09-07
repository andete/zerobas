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


def report(tag: str, moved: bool, before: str, after: str,
           rc: int | None = None, log: str | None = None) -> str:
    """`rc`/`log` are the build's own return code and log path, from build().

    🔴 PASS THEM. An unchanged ROM has TWO causes and they need different
    words. 2026-09-07 (D-CTRLC/D-FILESGUARD): K-FG1 reported `KNIFE INERT`, which
    is true and reads as "the cut is stale" — the actual cause was that the cut
    ADDS 6 bytes and D-CTRLC had just left **2 B free in page 1**, so pasmo died
    on `BASIC_IMAGE_OVERRAN_8000_CEILING` and the old ROM stayed on disk. Nothing
    in the runner's output said so; the cause was only in the build log, because
    the caller had discarded rc as `_rc`.
    🎯 A BYTE-ADDING CUT IS WALL-DEPENDENT, AND NOTHING DECLARES THAT.
    An unrelated commit five bytes wide can silently disarm a knife that has
    worked for weeks, and the knife will still print a sentence about its own
    arm. Without `rc` this function cannot tell you which happened.
    """
    if moved:
        return f"  ROM {before}  ->  {after}"
    if rc:
        why = ""
        if log and os.path.exists(log):
            for ln in open(log, errors="replace"):
                if "ERROR:" in ln:
                    why = f"\n     {ln.strip()}"
                    break
        return (f"  🔴 {tag}: THE BUILD FAILED (rc={rc}) — the cut never "
                f"reached the assembler's output, so the ROM on disk is the UNCUT "
                f"one. This is NOT 'the arm found nothing' and NOT a stale anchor: "
                f"a byte-ADDING cut is wall-dependent, and the wall moves under it "
                f"between runs.{why}")
    return (f"  🔴 {tag}: KNIFE INERT — the ROM did not change ({after}); the "
            f"probe would measure the UNCUT machine, and any 'moved 0 rows' "
            f"below would be meaningless. The build SUCCEEDED (rc=0), so this is "
            f"a stale anchor or a cut with no effect — not a space failure; pass "
            f"`rc=` to keep those two apart")


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
class CutError(RuntimeError):
    """The cut is not uniquely placed -- refuse, never patch the wrong copy."""


def _region(text, routine):
    """The source span of `routine`: its label line to the next column-0 label.

    Assembly labels here start at column 0 and end in `:`; everything indented
    belongs to the label above it."""
    lines = text.split("\n")
    start = None
    for i, ln in enumerate(lines):
        if ln.split(";")[0].strip() == f"{routine}:" and ln[:1] not in (" ", "\t"):
            start = i
            break
    if start is None:
        raise CutError(f"`{routine}` is not a column-0 label in this file")
    for j in range(start + 1, len(lines)):
        ln = lines[j]
        if ln[:1] not in (" ", "\t", "", ";") and ln.split(";")[0].strip().endswith(":"):
            return start, j
    return start, len(lines)


def cut(text, anchor, repl, *, routine=None):
    r"""Replace `anchor` with `repl`, refusing unless it occurs EXACTLY ONCE.

    🔴 WHY THIS EXISTS (filed 2026-08-11 by D-PAINTSEED, spec-basic-lineerr.md
    §9.6). K-PS1's first runner did
    `src.replace("call gfx_point_gate  ; BC/DE/HL preserved", ..., 1)` -- a line
    that occurs THREE times in `basic/graphics.asm` -- and so cut
    `gfx_plot_stmt`'s copy: **the probe's own `PSET(7,4)` seed**. `.replace(...,
    1)` takes the FIRST occurrence, which is a position, not a decision. It was
    caught only because the runner happened to read the report TAG.

    🎯 `routine=` SCOPES THE SEARCH TO ONE LABEL'S REGION, which is what makes a
    repeated line cuttable at the copy you mean. Without it the anchor must be
    unique in the whole file -- the stricter rule, and the right default, because
    a runner that has not thought about which copy it wants should not get one.

    ⚠️ THE REFUSAL IS THE POINT, not the convenience: a knife that cuts the wrong
    copy still builds, still runs, and still prints rows, so nothing downstream
    can tell you it happened.

    `dev-workflow.md` §Knives has eight rules about how a runner reads a report
    and none about how it makes a cut; this is that rule, and it lives here for
    the same reason the ROM hash does -- runners are throwaway, so the machinery
    they share cannot be.
    """
    if routine is None:
        n = text.count(anchor)
        if n != 1:
            raise CutError(
                f"anchor occurs {n} time(s) in the file, not once -- pass "
                f"routine=<label> to scope it, or make the anchor unique. "
                f"`.replace(x, y, 1)` would have taken the FIRST, which is a "
                f"position and not a decision.")
        return text.replace(anchor, repl, 1)
    lo, hi = _region(text, routine)
    lines = text.split("\n")
    body = "\n".join(lines[lo:hi])
    n = body.count(anchor)
    if n != 1:
        raise CutError(
            f"anchor occurs {n} time(s) inside `{routine}` (and "
            f"{text.count(anchor)} in the file), not once -- the cut is not "
            f"uniquely placed.")
    patched = body.replace(anchor, repl, 1)
    return "\n".join(lines[:lo] + patched.split("\n") + lines[hi:])


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

    # --- cut(): the D-PAINTSEED shape, which is a POSITION mistaken for a
    # --- DECISION. The fixture repeats one anchor in three routines, exactly as
    # --- basic/graphics.asm does with `call gfx_point_gate`.
    FIX = ("one:\n                call    gate\n                ret\n"
           "two:\n                call    gate\n                ret\n"
           "three:\n                call    gate\n                ret\n")
    ANCH = "                call    gate\n"
    try:
        cut(FIX, ANCH, "                CUT\n")
        arm("cut refuses a repeated anchor when unscoped", False)
    except CutError as e:
        arm("cut refuses a repeated anchor when unscoped", "3 time(s)" in str(e))
    got = cut(FIX, ANCH, "                CUT\n", routine="two")
    # the cut must land in `two` and NOWHERE else -- the whole point
    arm("cut scoped to a routine hits THAT copy",
        got.split("two:")[1].split("three:")[0].count("CUT") == 1
        and got.split("two:")[0].count("CUT") == 0
        and got.split("three:")[1].count("CUT") == 0)
    try:
        cut(FIX, ANCH, "x", routine="nosuch")
        arm("cut refuses an unknown routine", False)
    except CutError:
        arm("cut refuses an unknown routine", True)
    try:
        cut(FIX, "                call    absent\n", "x", routine="two")
        arm("cut refuses an anchor absent from the routine", False)
    except CutError as e:
        arm("cut refuses an anchor absent from the routine", "0 time(s)" in str(e))
    # ...and a UNIQUE unscoped anchor must still work, or every existing runner
    # would have to be rewritten to use routine=
    arm("cut still takes a unique unscoped anchor",
        cut("a:\n  x\nb:\n  y\n", "  x\n", "  Z\n") == "a:\n  Z\nb:\n  y\n")

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
