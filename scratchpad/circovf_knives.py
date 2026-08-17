#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CIRCOVF knives -- falsify the slice by reinstating the defect.

Descends from scratchpad/circdom_knives.py with BOTH of the defects TODO.md
filed against it fixed (search "TWO KNIFE-RUNNER DEFECTS"):

 (a) ROWS ARE KEYED ON (phase, index, label), NOT ON label. The old runner
     keyed a dict on the label alone and reported rows=289 where the probe
     printed 296 PASS lines, because five labels repeat across phases. A move
     confined to ONE instance of a duplicated label was silently swallowed and
     read as "the knife cut nothing" -- i.e. as a missing row, the one verdict
     that is supposed to mean something. The count is now asserted against the
     probe's own PASS/FAIL line count, so the two can never drift again.

 (b) A KNIFE CAN DECLARE ITS KIND. Round 3 of D-CIRCDOM scored K-CD3 a MISS
     because its "prediction" was a measurement copied forward from round 2 --
     a regression check being graded as a forecast. `kind` now says which it is:
       "predict" -- a genuine forecast; EXACT/MISS are meaningful
       "regress" -- a known answer copied forward; HOLD/BROKEN, never "EXACT"
       "nothing" -- predicted to redden NOTHING, with the reason stated. This
                    is normally the failure verdict ("a knife that reddens
                    nothing means a missing row") and is only ever legitimate
                    when the missing row is the FINDING, which is exactly the
                    case for K-CO3 below.

Everything else is inherited because it was sound: the SUBJECT is the probe
invoked directly (never `make` -- rc 2 vs rc 1), snapshot restore in a
`finally`, build BEFORE the baseline, each cut site asserted to occur exactly
once, the probe's footer required on every run, and the baseline refused unless
it is green with >= 250 rows at the expected ROM hash.

    python3 -u scratchpad/circovf_knives.py
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
GRAPHICS = os.path.join(REPO, "sub", "graphics.asm")

PRE_SLICE_SUB_SHA = "8161c1a2"     # sub.rom at b602eac, before this slice
POST_SLICE_SUB_SHA = "bc7573df"    # sub.rom with the slice applied

ROW = re.compile(r"^\s*(PASS|FAIL)\s+(\S+)")
PHASE = re.compile(r"^===\s*PHASE\s+(\S+)")
FOOTER = re.compile(r"^graphics-acceptance:\s+(PASS|FAIL \((\d+)\))\s*$", re.M)


def _circle_rows(pred):
    """CIRCLE_CASES labels matching `pred`, read off the PROBE ITSELF.

    🔴 DERIVED, NEVER HAND-TYPED. D-CIRCDOM's K-CD2 was scored a MISS by exactly
    one row because a hand-maintained set lost `ell_a2r128` when five rows were
    added -- a transcription risk with zero modelling content, failing silently
    in the direction that looks like a real finding."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("_gfxprobe", PROBE)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
    spec.loader.exec_module(mod)
    return {lbl for lbl, ops, _, _, _ in mod.CIRCLE_CASES if pred(lbl, ops)}


def _aspect_of(ops):
    """The aspect field of a CIRCLE statement, positionally ('' if omitted).
    CIRCLE(x,y),r,c,start,end,aspect -> the 7th comma-separated field."""
    f = ops.split(",")
    return f[6].strip() if len(f) >= 7 else ""


def _asps(ops):
    """GFX_ASPS the tenant will compute: trunc(minor_ratio*256), 0..256."""
    a = _aspect_of(ops)
    if not a:
        return 256
    v = float(a)
    r = v if v < 1 else 1.0 / v
    return int(r * 256)


def _radius(ops):
    """CIRCLE(x,y),r,... -> r, positionally."""
    return int(ops.split(",")[2])


def _scale_max(ops):
    """The largest value gfx_circ_scale can return for this row."""
    return (_radius(ops) * _asps(ops) + 128) >> 8


def _has_arc(ops):
    """True iff the row passes a start or end angle, so the arc mask runs."""
    f = ops.split(",")
    return len(f) >= 6 and (f[4].strip() or f[5].strip())


def _centre(ops):
    x, y = ops.split(")")[0].split("(")[1].split(",")
    return int(x), int(y)


def _draws(ops):
    """Pixels the SHIPPED build puts on screen for this row's full circle --
    a superset of any arc masked out of it. A row that draws nothing cannot be
    reddened by a cut that only changes which points are KEPT."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from circovf_calib import pixels, scale_exact
    cx, cy = _centre(ops)
    a = _aspect_of(ops)
    maj = 1 if (a and float(a) >= 1) else 0
    return bool(pixels(cx, cy, _radius(ops), _asps(ops), maj, scale_exact)[0])


# Rows whose sweep is the WHOLE circle, where the mask keeps every point no
# matter which way the boundary vectors point -- so K-CO4 cannot move them. A
# modelling exclusion, stated, not a transcription of a measured result.
_FULL_SWEEP = {"arc_full628"}

# --- the cuts. All BYTE-NEUTRAL opcode swaps: they reinstate a defect without
# --- moving any code, so a knifed build differs from the shipped one only in
# --- the bytes under test.
KNIVES = {
    "K-CO1": dict(
        path=GRAPHICS, kind="predict",
        find="                ld      h,c                 ; HL = (product + 128) >> 8",
        repl="                ld      h,b                 ; HL = (product + 128) >> 8",
        # B is 0 after djnz, so this narrows gfx_mul16r's result to its low byte
        # -- the exact `ld l,h / ld h,0` defect the slice removed, byte for byte.
        pred=lambda: _circle_rows(
            lambda lbl, ops: _asps(ops) != 256 and _scale_max(ops) > 255),
        note="narrow gfx_mul16r's result to a byte (B=0 after djnz). Only rows "
             "that TAKE the multiply arm can move -- ASPS=256 goes through the "
             "identity arm and never reaches this instruction -- and of those, "
             "only ones whose largest scaled offset exceeds 255. Both halves "
             "of that are computed from the row's own ops, not listed.",
    ),
    "K-CO2": dict(
        path=GRAPHICS, kind="predict",
        find="                ld      a,d\n                or      a\n"
             "                jr      nz,gcs_signed",
        repl="                ld      a,d\n                xor     a\n"
             "                jr      nz,gcs_signed",
        # `xor a` always sets Z, so the ASPS=256 identity arm is never taken and
        # those rows fall into the multiply with A = ASPS low byte = 0.
        pred=lambda: _circle_rows(
            lambda lbl, ops: _asps(ops) == 256 and _radius(ops) > 0),
        note="kill the ASPS=256 identity arm. Falsifies that the arm is "
             "load-bearing AND that it is the thing keeping the result below "
             "$8000: every default-aspect row must move, and NO row with an "
             "explicit aspect < 1 or > 1 may, because those took the multiply "
             "path already.",
    ),
    "K-CO3": dict(
        path=GRAPHICS, kind="nothing",
        find="                ld      b,4\n                or      a                   ; CF = 0 going in",
        repl="                ld      b,2\n                or      a                   ; CF = 0 going in",
        pred=lambda: set(),
        note="compare only the low 16 bits of the cross products -- i.e. undo "
             "the 32-bit widening at gfx_cross_ge0. 🔴 PREDICTED TO REDDEN "
             "NOTHING, AND THAT IS THE FINDING: no GREEN gate row can see this "
             "compare. The rows that would (an arc, at a radius where the "
             "products pass 16 bits, with pixels on screen) are ALREADY RED for "
             "a separate pre-existing reason -- measured, arcctl_r200 is "
             "byte-identical pre- and post-slice and red on both. The widening "
             "is forced by arithmetic, not by a row, and this knife is how that "
             "gap gets a number instead of a sentence.",
    ),
    "K-CO4": dict(
        path=GRAPHICS, kind="predict",
        find="                ld      de,(GFX_R)\n                jp      gfx_mul16r",
        repl="                ld      de,(GFX_R)\n                jp      gfx_mul16u32",
        pred=lambda: _circle_rows(
            lambda lbl, ops: _has_arc(ops) and lbl not in _FULL_SWEEP
            and _draws(ops)),
        note="send gfx_circ_bvec_mag to the WRONG multiply: the raw 32-bit "
             "product's low word instead of the rounded 8.8 scale, so every "
             "boundary vector comes back ~256x too long. ONLY arc rows read "
             "boundary vectors, so every full circle must stay green -- that "
             "half is the control. ⚠️ The prediction is a real forecast and may "
             "well miss: the mask tests the SIGN of a cross product, which is "
             "invariant under a positive rescale, so a row moves only where the "
             "rounding difference flips an edge point.",
    ),
    "K-CO5": dict(
        path=PROBE, kind="predict",
        find="    rows = range(max(0, yr[0] >> 3), min(23, yr[1] >> 3) + 1)",
        repl="    rows = range(max(0, yr[0] >> 3), min(5, yr[1] >> 3) + 1)",
        pred=lambda: set(),      # expected: the probe ABORTS in its own guard
        note="cut the band clamp so it DOES move a pre-existing row. The "
             "subject is the gate's OWN guard: _assert_band_clamp_is_noop must "
             "fire and abort with no footer at all. Inherited from K-CD4, and "
             "it now also covers this slice's ten new wide rows, which are "
             "off-centre as well as oversized.",
    ),
}


def sh(cmd):
    return subprocess.run(cmd, shell=True, cwd=REPO, capture_output=True,
                          text=True)


def sub_sha():
    p = os.path.join(REPO, "build", "sub.rom")
    if not os.path.exists(p):
        return "MISSING"
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:8]


def build():
    r = sh("rm -rf build && make repack-machine")
    return r.returncode == 0, sub_sha()


def run_probe():
    """Return (rc, rows, footer, raw). `rows` maps (phase, index, label) ->
    PASS/FAIL -- the fix for defect (a). `printed` is the probe's own count of
    PASS/FAIL lines, asserted equal to len(rows) so the two cannot drift."""
    r = subprocess.run([sys.executable, "-u", PROBE], cwd=REPO,
                       capture_output=True, text=True)
    rows, phase, idx, printed = {}, "?", 0, 0
    for line in r.stdout.splitlines():
        p = PHASE.match(line)
        if p:
            phase, idx = p.group(1), 0
            continue
        m = ROW.match(line)
        if m:
            printed += 1
            rows[(phase, idx, m.group(2))] = m.group(1)
            idx += 1
    assert len(rows) == printed, (
        f"row key collision: {printed} printed, {len(rows)} keyed")
    f = FOOTER.search(r.stdout)
    return r.returncode, rows, (f.group(1) if f else None), r.stdout + r.stderr


def main():
    snap = tempfile.mkdtemp(prefix="circovf-knife-")
    for p in (GRAPHICS, PROBE):
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

        # predictions are resolved AFTER the baseline proves the probe imports
        for name, k in KNIVES.items():
            k["predicted"] = k["pred"]()

        results = []
        for name, k in KNIVES.items():
            path, find, repl = k["path"], k["find"], k["repl"]
            print(f"\n=== {name} [{k['kind']}] === {k['note']}")
            src = open(path).read()
            n = src.count(find)
            print(f"  cut site occurs {n}x in {os.path.relpath(path, REPO)}")
            if n != 1:
                print(f"  ABORT {name}: cut site must occur exactly once")
                results.append((name, k, "ABORT", set()))
                continue
            open(path, "w").write(src.replace(find, repl, 1))
            try:
                if path != PROBE:
                    okb, ksha = build()
                    if not okb:
                        print(f"  {name}: build FAILED under the cut")
                        results.append((name, k, "BUILD-FAIL", set()))
                        continue
                    print(f"  sub.rom under cut: {ksha}")
                    if ksha == POST_SLICE_SUB_SHA:
                        print(f"  🔴 {name}: the cut did NOT change the ROM -- "
                              f"it is not reaching the shipped image")
                krc, krows, kfooter, kout = run_probe()
                if kfooter is None:
                    aborted = "AssertionError" in kout
                    print(f"  no footer; AssertionError in output: {aborted}; "
                          f"rc={krc}")
                    results.append((name, k, "NO-FOOTER" +
                                    ("/ASSERT" if aborted else ""), set()))
                    continue
                if len(krows) < 250:
                    print(f"  ABORT {name}: knifed run is SHORT ({len(krows)})")
                    results.append((name, k, "SHORT", set()))
                    continue
                moved = {key for key, v in krows.items() if v == "FAIL"} - base_fail
                print(f"  rc={krc} footer={kfooter!r} moved={len(moved)}")
                results.append((name, k, "ran", {key[2] for key in moved}))
            finally:
                shutil.copy2(os.path.join(snap, os.path.basename(path)), path)

        print("\n" + "=" * 74)
        print("KNIFE SCORECARD (predictions were written before the run)")
        print("=" * 74)
        for name, k, state, moved in results:
            predicted, kind = k["predicted"], k["kind"]
            if state != "ran":
                ok = (name == "K-CO5" and "ASSERT" in state)
                print(f"  {name:7} [{kind:7}] {state:18} -> "
                      f"{'EXACT (the guard fired)' if ok else state}")
                continue
            if kind == "nothing":
                if not moved:
                    print(f"  {name:7} [nothing] CUT NOTHING -- AS PREDICTED. "
                          f"The gap is real: no green row sees this code.")
                else:
                    print(f"  {name:7} [nothing] 🔴 REDDENED {len(moved)} rows "
                          f"that were predicted invisible: {sorted(moved)}")
                continue
            if kind == "regress":
                print(f"  {name:7} [regress] "
                      f"{'HOLD' if moved == predicted else 'BROKEN'} "
                      f"{len(moved)} rows (a copied-forward measurement, NOT a "
                      f"forecast -- never scored EXACT)")
                continue
            if not moved:
                print(f"  {name:7} [predict] CUT NOTHING -- a missing row, "
                      f"not a passing knife")
            elif moved == predicted:
                print(f"  {name:7} [predict] EXACT   {len(moved)} rows: "
                      f"{sorted(moved)}")
            else:
                print(f"  {name:7} [predict] MISS")
                print(f"          predicted {sorted(predicted)}")
                print(f"          measured  {sorted(moved)}")
                print(f"          missing   {sorted(predicted - moved)}")
                print(f"          extra     {sorted(moved - predicted)}")
        return 0
    finally:
        for p in (GRAPHICS, PROBE):
            shutil.copy2(os.path.join(snap, os.path.basename(p)), p)
        print(f"\nrestored both files from {snap}")
        ok, sha = build()
        print(f"rebuilt after restore: sub.rom {sha} "
              f"({'OK' if sha == POST_SLICE_SUB_SHA else 'MISMATCH -- DIRTY'})")


if __name__ == "__main__":
    sys.exit(main())
