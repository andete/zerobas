#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G4 host-fit: derive an own-design integer rasteriser that reproduces the
captured VG-8020 CIRCLE/ellipse/arc point-sets EXACTLY, before any asm is written
(the recurring arc lesson -- de-risk the crux, don't guess). Loads
g4_pointsets.json (from g4_circle_char3.py). Prints per-case match / first-diff."""
from __future__ import annotations
import os, json, math

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, "g4_pointsets.json")))


# ---------- candidate integer midpoint circle (own design) ----------
def midpoint_circle_octants(r):
    """classic integer midpoint; returns set of (dx,dy) offsets from centre."""
    pts = set()
    x, y = 0, r
    d = 1 - r
    while x <= y:
        for sx in (1, -1):
            for sy in (1, -1):
                pts.add((sx * x, sy * y))
                pts.add((sx * y, sy * x))
        if d < 0:
            d += 2 * x + 3
        else:
            d += 2 * (x - y) + 5
            y -= 1
        x += 1
    return pts


def circle_points(cx, cy, r):
    return {(cx + dx, cy + dy) for (dx, dy) in midpoint_circle_octants(r)}


def fit_circles():
    print("=== fit pure circles (aspect=1) ===")
    ok = True
    for label, d in DATA.items():
        if not label.startswith("circ_"):
            continue
        r = int(''.join(c for c in label if c.isdigit()))
        got = circle_points(d["cx"], d["cy"], r)
        ref = {(x, y) for x, y in d["pts"]}
        extra = got - ref
        missing = ref - got
        status = "MATCH" if not extra and not missing else f"DIFF +{len(extra)} -{len(missing)}"
        if extra or missing:
            ok = False
            ex = sorted(extra)[:4]; mi = sorted(missing)[:4]
            print(f"  {label:10s} r={r:2d} n_ref={d['n']:3d} -> {status}  extra{ex} miss{mi}")
        else:
            print(f"  {label:10s} r={r:2d} n_ref={d['n']:3d} -> {status}")
    print("  ALL CIRCLES MATCH" if ok else "  *** circle mismatch ***")
    return ok


# ---------- ellipse: single circle of major radius, minor scaled per point ----------
def ellipse_points_scaled(cx, cy, r, aspect):
    """Model A: run circle of radius = MAJOR; scale the MINOR offset per octant point.
    aspect<=1: major axis = x (=r), minor = y scaled by aspect.
    aspect >1: major axis = y (=r), minor = x scaled by 1/aspect."""
    base = midpoint_circle_octants(r)
    pts = set()
    if aspect <= 1.0:
        for dx, dy in base:
            pts.add((cx + dx, cy + int(dy * aspect)))
    else:
        for dx, dy in base:
            pts.add((cx + int(dx / aspect), cy + dy))
    return pts


def fit_ellipses():
    print("\n=== fit ellipses (per-point minor scaling, trunc) ===")
    # aspect parsed from ops
    for label, d in DATA.items():
        if not label.startswith("ell_"):
            continue
        ops = d["ops"]
        a = float(ops.split(",,,")[1])
        r = int(ops.split(")")[1].split(",")[1])
        for rounder, name in [(lambda v: int(v), "trunc"),
                              (lambda v: int(v + 0.5) if v >= 0 else -int(-v + 0.5), "round"),
                              (lambda v: math.floor(v), "floor")]:
            base = midpoint_circle_octants(r)
            pts = set()
            if a <= 1.0:
                for dx, dy in base:
                    pts.add((d["cx"] + dx, d["cy"] + rounder(dy * a)))
            else:
                for dx, dy in base:
                    pts.add((d["cx"] + rounder(dx / a), d["cy"] + dy))
            ref = {(x, y) for x, y in d["pts"]}
            extra = pts - ref; missing = ref - pts
            if not extra and not missing:
                print(f"  {label:12s} a={a:5.3g} r={r:2d} -> MATCH ({name})")
                break
        else:
            # report best (trunc) diff
            print(f"  {label:12s} a={a:5.3g} r={r:2d} -> NO EXACT MATCH; "
                  f"trunc diff +{len(pts-ref)} -{len(ref-pts)}")


# ---------- arc masking: keep octant points whose CCW angle in [|s|,|e|] ----------
def arc_points(cx, cy, r, s, e):
    """CCW arc from |s| to |e| (mod 2pi). angle 0=+x, CCW=+ (screen: -y up).
    We test each full-circle point's angle; keep if in the CCW sweep."""
    base = midpoint_circle_octants(r)
    a0 = abs(s) % (2 * math.pi)
    a1 = abs(e) % (2 * math.pi)
    if a1 == 0 and e != 0:
        a1 = 2 * math.pi
    sweep = (a1 - a0) % (2 * math.pi)
    if sweep == 0:
        sweep = 2 * math.pi  # full
    pts = set()
    for dx, dy in base:
        # screen y grows down; CCW positive angle = -dy up. math angle = atan2(-dy, dx)
        ang = math.atan2(-dy, dx) % (2 * math.pi)
        rel = (ang - a0) % (2 * math.pi)
        if rel <= sweep + 1e-9:
            pts.add((cx + dx, cy + dy))
    return pts


def fit_arcs():
    print("\n=== fit arcs (angle-mask, no spokes) ===")
    ARC = {"arc_0_hpi": (0, 1.57), "arc_hpi_pi": (1.57, 3.14),
           "arc_wrap": (3, 1), "arc_full628": (0, 6.28)}
    for label, (s, e) in ARC.items():
        if label not in DATA:
            continue
        d = DATA[label]
        r = int(d["ops"].split(")")[1].split(",")[1])
        got = arc_points(d["cx"], d["cy"], r, s, e)
        ref = {(x, y) for x, y in d["pts"]}
        extra = got - ref; missing = ref - got
        status = "MATCH" if not extra and not missing else f"DIFF +{len(extra)} -{len(missing)}"
        print(f"  {label:14s} s={s} e={e} n_ref={d['n']:3d} got={len(got):3d} -> {status}")
        if extra or missing:
            print(f"       extra{sorted(extra)[:5]} miss{sorted(missing)[:5]}")


if __name__ == "__main__":
    fit_circles()
    fit_ellipses()
    fit_arcs()


# ---------- verify 8.8 fixed-point per-point scaling (what the asm will do) ----------
def ellipse_points_fixed(cx, cy, r, aspect):
    base = midpoint_circle_octants(r)
    pts = set()
    if aspect <= 1.0:
        S = int(aspect * 256 + 0.5)                 # 8.8 scale for minor (y)
        for dx, dy in base:
            sgn = 1 if dy >= 0 else -1
            sv = (abs(dy) * S + 128) >> 8
            pts.add((cx + dx, cy + sgn * sv))
    else:
        S = int((1.0 / aspect) * 256 + 0.5)         # 8.8 scale for minor (x)
        for dx, dy in base:
            sgn = 1 if dx >= 0 else -1
            sv = (abs(dx) * S + 128) >> 8
            pts.add((cx + sgn * sv, cy + dy))
    return pts


def fit_ellipses_fixed():
    print("\n=== verify 8.8 fixed-point minor scaling (asm-faithful) ===")
    for label, d in DATA.items():
        if not label.startswith("ell_"):
            continue
        a = float(d["ops"].split(",,,")[1]); r = int(d["ops"].split(")")[1].split(",")[1])
        got = ellipse_points_fixed(d["cx"], d["cy"], r, a)
        ref = {(x, y) for x, y in d["pts"]}
        e = got - ref; m = ref - got
        S = int((a if a <= 1 else 1/a) * 256 + 0.5)
        print(f"  {label:12s} a={a:5.3g} S={S:3d}/256 -> "
              f"{'MATCH' if not e and not m else f'DIFF +{len(e)} -{len(m)}'}")


# ---------- rule out true midpoint ellipse (two integer semi-axes) ----------
def midpoint_ellipse(cx, cy, a, b):
    pts = set()
    if a == 0 or b == 0:
        return pts
    a2, b2 = a * a, b * b
    x, y = 0, b
    d1 = b2 - a2 * b + a2 / 4
    dx, dy = 0, 2 * a2 * b
    while dx < dy:
        for sx in (1, -1):
            for sy in (1, -1):
                pts.add((cx + sx * x, cy + sy * y))
        if d1 < 0:
            x += 1; dx += 2 * b2; d1 += dx + b2
        else:
            x += 1; y -= 1; dx += 2 * b2; dy -= 2 * a2; d1 += dx - dy + b2
    d2 = b2 * (x + 0.5) ** 2 + a2 * (y - 1) ** 2 - a2 * b2
    while y >= 0:
        for sx in (1, -1):
            for sy in (1, -1):
                pts.add((cx + sx * x, cy + sy * y))
        if d2 > 0:
            y -= 1; dy -= 2 * a2; d2 += a2 - dy
        else:
            y -= 1; x += 1; dx += 2 * b2; dy -= 2 * a2; d2 += dx - dy + a2
    return pts


def fit_ellipses_modelB():
    print("\n=== rule out two-semi-axis midpoint ellipse (Model B) ===")
    for label, d in DATA.items():
        if not label.startswith("ell_"):
            continue
        a = float(d["ops"].split(",,,")[1]); r = int(d["ops"].split(")")[1].split(",")[1])
        rx = r if a <= 1 else int(round(r / a))
        ry = int(round(r * a)) if a <= 1 else r
        got = midpoint_ellipse(d["cx"], d["cy"], rx, ry)
        ref = {(x, y) for x, y in d["pts"]}
        e = got - ref; m = ref - got
        print(f"  {label:12s} (rx={rx},ry={ry}) -> "
              f"{'MATCH' if not e and not m else f'DIFF +{len(e)} -{len(m)}'}")


if __name__ != "__main__x":
    fit_ellipses_fixed()
    fit_ellipses_modelB()
