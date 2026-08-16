#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CIRCDOM knives -- falsify the slice by reinstating the defect.

Discipline per docs/dev-workflow.md §Knives:
  * the SUBJECT is the probe invoked directly, never `make` (rc 2 vs rc 1)
  * restore from a scratchpad SNAPSHOT in a `finally`, never `git checkout --`
  * build BEFORE the baseline
  * every cut site must occur EXACTLY ONCE before it is applied
  * parse the probe's own rows AND require its footer -- a crashed probe prints
    a PREFIX and would otherwise read as a spectacular CUT
  * gate on the ROM hash so a stale build cannot be scored as a result

All four cuts are BYTE-NEUTRAL opcode swaps, so they reinstate the defect
without moving any code -- and K-CD1, which is the exact inverse of the slice's
only functional edit, must rebuild the PRE-SLICE sub.rom byte for byte.

    python3 -u scratchpad/circdom_knives.py
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBE = os.path.join(REPO, "probes", "basic", "basic_probe_graphics.py")

CIRCLEPARSE = os.path.join(REPO, "sub", "circleparse.asm")
GRAPHICS = os.path.join(REPO, "sub", "graphics.asm")

PRE_SLICE_SUB_SHA = "c2292117"     # sub.rom at 15b53bf, before this slice
POST_SLICE_SUB_SHA = "8161c1a2"    # sub.rom with the slice applied

ROW = re.compile(r"^\s*(PASS|FAIL)\s+(\S+)")
FOOTER = re.compile(r"^graphics-acceptance:\s+(PASS|FAIL \((\d+)\))\s*$", re.M)

def _aspect_rows() -> set:
    """Every CIRCLE_CASES row that carries an aspect field, read off the probe
    itself. Derived so that adding a row to the gate cannot silently leave a
    knife's prediction stale -- see the K-CD2 note below for the miss that
    motivated this."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("_gfxprobe", PROBE)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
    spec.loader.exec_module(mod)
    return {lbl for lbl, ops, _, _, _ in mod.CIRCLE_CASES
            if len(ops.split(",")) >= 7 and ops.split(",")[-1].strip()}


# label -> (file, find, replace, predicted FAIL labels, note)
KNIVES = {
    "K-CD1": (
        CIRCLEPARSE,
        "                call    flt_to_int16        ; DE := TRUNC(...) -- not cpt_round",
        "                call    cpt_round",
        {"ell_a03r128", "ell_a055r128", "ell_a01r255",
         "ell_a17r128", "ell_a13r128", "ell_a11r128"},
        "the exact inverse of the slice's only functional edit: ASPS rounds "
        "half-up again. Must also rebuild sub.rom to the PRE-SLICE hash. "
        "ROUND 3: now predicts SIX rows, three per branch of cpt_asp_scale256 "
        "-- and the three aspect>=1 rows going red is the MEASUREMENT that the "
        "pre-fix tree was wrong on that branch too, not an inference from it. "
        "The four controls (ell_a07r128, ell_a025r128, ell_a2r128, ell_a4r128) "
        "must stay GREEN: floor == round at their aspects.",
    ),
    "K-CD2": (
        CIRCLEPARSE,
        "                call    flt_to_int16        ; DE := TRUNC(...) -- not cpt_round",
        "                ld      de,256",
        # 🔴 DERIVED, NOT HAND-LISTED -- and that is a landed defect, not tidiness.
        # Round 3 scored this knife a MISS by exactly one row: the prediction was
        # a hand-typed set that I extended by hand when five rows were added, and
        # I dropped `ell_a2r128` while remembering `ell_a4r128`. The MODEL was
        # right -- "every row carrying an aspect field moves" -- and the measured
        # 16 is precisely the derived set below. A prediction set maintained by
        # hand is a transcription risk with no modelling content, and it fails
        # silently in the direction that looks like a real finding.
        _aspect_rows(),
        "pin ASPS at 256 (no scaling at all). Falsifies that these rows read "
        "GFX_ASPS: every aspect row in the gate, old and new, must move.",
    ),
    "K-CD3": (
        GRAPHICS,
        "                ld      de,128\n                add     hl,de\n"
        "                ld      l,h\n                ld      h,0                 "
        "; HL = (|v|*ASPS+128) >> 8",
        "                ld      de,0\n                add     hl,de\n"
        "                ld      l,h\n                ld      h,0                 "
        "; HL = (|v|*ASPS+128) >> 8",
        {"ell_a3", "ell_a05r15", "ell_a01r255", "ell_a07r128", "ell_r700a0137",
         "ell_a025", "ell_a025r128", "ell_a03r128", "ell_a05", "ell_a055r128",
         "ell_a2"},   # <- ROUND 2 MEASURED, not re-derived: see the note
        "gfx_circ_scale rounds down instead of half-up. ROUND 2 SCORED THIS A "
        "MISS: the hand-computed prediction was five rows and eleven moved, a "
        "strict superset, because it was computed from the BOUNDING BOX while "
        "the gate compares the whole 6144-byte plane. The set above is therefore "
        "the round-2 MEASUREMENT copied forward, NOT a re-derivation -- it is a "
        "regression check on a known answer, and it must not be read as a "
        "second successful prediction. The round-3 rows are deliberately left "
        "OUT of it, so they are the only genuinely predictive part: whatever "
        "they do is new information.",
    ),
    "K-CD4": (
        PROBE,
        "    rows = range(max(0, yr[0] >> 3), min(23, yr[1] >> 3) + 1)",
        "    rows = range(max(0, yr[0] >> 3), min(5, yr[1] >> 3) + 1)",
        set(),   # expected: the probe ABORTS in its own guard, before any row
        "cut the band clamp so it DOES move a pre-existing row. The subject here "
        "is the gate's own guard: _assert_band_clamp_is_noop must fire and abort "
        "with no footer at all. A knife that reddens nothing here means the guard "
        "is decorative.",
    ),
}


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, cwd=REPO, capture_output=True,
                          text=True, **kw)


def sub_sha() -> str:
    p = os.path.join(REPO, "build", "sub.rom")
    if not os.path.exists(p):
        return "MISSING"
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:8]


def build() -> tuple[bool, str]:
    r = sh("rm -rf build && make repack-machine")
    return r.returncode == 0, sub_sha()


def run_probe() -> tuple[int, dict, str | None, str]:
    r = subprocess.run([sys.executable, "-u", PROBE], cwd=REPO,
                       capture_output=True, text=True)
    rows = {}
    for line in r.stdout.splitlines():
        m = ROW.match(line)
        if m:
            rows[m.group(2)] = m.group(1)
    f = FOOTER.search(r.stdout)
    return r.returncode, rows, (f.group(1) if f else None), r.stdout + r.stderr


def main() -> int:
    snap = tempfile.mkdtemp(prefix="circdom-knife-")
    for p in (CIRCLEPARSE, GRAPHICS, PROBE):
        shutil.copy2(p, os.path.join(snap, os.path.basename(p)))
    print(f"snapshot: {snap}")

    try:
        print("=== building BEFORE the baseline ===")
        ok, sha = build()
        if not ok:
            print("ABORT: baseline build failed")
            return 2
        print(f"  sub.rom {sha}  (expected post-slice {POST_SLICE_SUB_SHA})")
        if sha != POST_SLICE_SUB_SHA:
            print("ABORT: baseline sub.rom is not the post-slice image")
            return 2

        rc, base_rows, base_footer, _ = run_probe()
        if base_footer is None:
            print("ABORT: baseline printed no footer -- the probe crashed")
            return 2
        if len(base_rows) < 250:
            print(f"ABORT: baseline is SHORT ({len(base_rows)} rows)")
            return 2
        base_fail = {k for k, v in base_rows.items() if v == "FAIL"}
        print(f"  baseline rc={rc} rows={len(base_rows)} footer={base_footer!r} "
              f"fails={sorted(base_fail) or 'none'}")
        if rc != 0 or base_fail:
            print("ABORT: baseline is not green")
            return 2

        results = []
        for name, (path, find, repl, predicted, note) in KNIVES.items():
            print(f"\n=== {name} === {note}")
            src = open(path).read()
            n = src.count(find)
            print(f"  cut site occurs {n}x in {os.path.relpath(path, REPO)}")
            if n != 1:
                print(f"  ABORT {name}: cut site must occur exactly once")
                results.append((name, "ABORT", set(), predicted))
                continue
            open(path, "w").write(src.replace(find, repl, 1))
            try:
                if path != PROBE:
                    okb, ksha = build()
                    if not okb:
                        print(f"  {name}: build FAILED under the cut")
                        results.append((name, "BUILD-FAIL", set(), predicted))
                        continue
                    print(f"  sub.rom under cut: {ksha}")
                    if name == "K-CD1":
                        exact = ksha == PRE_SLICE_SUB_SHA
                        print(f"  K-CD1 full-revert hash check: {ksha} vs "
                              f"pre-slice {PRE_SLICE_SUB_SHA} -> "
                              f"{'EXACT' if exact else 'MISMATCH'}")
                krc, krows, kfooter, kout = run_probe()
                if kfooter is None:
                    aborted = "AssertionError" in kout
                    print(f"  no footer; AssertionError in output: {aborted}; rc={krc}")
                    results.append((name, "NO-FOOTER" + ("/ASSERT" if aborted else ""),
                                    set(), predicted))
                    continue
                if len(krows) < 250:
                    print(f"  ABORT {name}: knifed run is SHORT ({len(krows)} rows)")
                    results.append((name, "SHORT", set(), predicted))
                    continue
                moved = {k for k, v in krows.items() if v == "FAIL"} - base_fail
                print(f"  rc={krc} footer={kfooter!r} moved={len(moved)}")
                results.append((name, "ran", moved, predicted))
            finally:
                shutil.copy2(os.path.join(snap, os.path.basename(path)), path)

        print("\n" + "=" * 74)
        print("KNIFE SCORECARD (predictions were written before the run)")
        print("=" * 74)
        for name, state, moved, predicted in results:
            if state != "ran":
                verdict = ("EXACT" if (name == "K-CD4" and "ASSERT" in state)
                           else state)
                print(f"  {name:7} {state:18} predicted={sorted(predicted) or 'abort-with-assert'}"
                      f"  -> {verdict}")
                continue
            if not moved:
                print(f"  {name:7} CUT NOTHING -- a missing row, not a passing knife")
            elif moved == predicted:
                print(f"  {name:7} EXACT   {len(moved)} rows: {sorted(moved)}")
            else:
                print(f"  {name:7} MISS")
                print(f"          predicted {sorted(predicted)}")
                print(f"          measured  {sorted(moved)}")
                print(f"          missing   {sorted(predicted - moved)}")
                print(f"          extra     {sorted(moved - predicted)}")
        return 0
    finally:
        for p in (CIRCLEPARSE, GRAPHICS, PROBE):
            shutil.copy2(os.path.join(snap, os.path.basename(p)), p)
        print(f"\nrestored all three files from {snap}")
        ok, sha = build()
        print(f"rebuilt after restore: sub.rom {sha} "
              f"({'OK' if sha == POST_SLICE_SUB_SHA else 'MISMATCH -- TREE IS DIRTY'})")


if __name__ == "__main__":
    sys.exit(main())
