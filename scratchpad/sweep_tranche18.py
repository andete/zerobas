#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""TODO sweep 2026-08-26, tranche 18 — the arc cluster, on the WHOLE PLANE.

These three items were measured as `ref N px <hash> / zb M px <hash>` over the
whole pattern plane. POINT sampling cannot reproduce that (tranches 16-17 showed
why: a sampled pixel can be painted by either writer). `omsx_repl` can capture
raw VRAM, so this counts the plane the way the items did.

⚠️ THEIR HASHES ARE THEIR OWN FUNCTION AND ARE NOT REPRODUCED HERE. What IS
reproduced is the PIXEL COUNT, and something stronger than a hash comparison:
the two planes are compared BYTE FOR BYTE, so "same count, different pixels" --
which is exactly what the third row of the arc-mask item reported -- is visible.
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_tmp                                                  # noqa: E402

REF = "Philips_VG_8020"
ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
PATTERN, PLEN = 0x0000, 6144            # SCREEN 2 pattern table

CASES = [
    ("arcmask.r200", "CIRCLE(128,352),200,15,1.1,2.04", "ref 170 px / zb 181 px"),
    ("arcmask.r700", "CIRCLE(128,96),700,15,0,1.57,.137", "ref 127 px / zb 126 px"),
    ("arcmask.r400", "CIRCLE(128,96),400,15,-1.57,0", "ref 97 px / zb 97 px, DIFFERENT bbox"),
    ("arcangle.pi2", "CIRCLE(128,96),95,15,0,1.5707963", "ref 135 px / zb 134 px"),
    ("control.r95", "CIRCLE(128,96),95,15", "a plain full circle -- must agree"),
]


def plane(machine, stmt):
    out = omsx_repl.run_cases(
        # 🔴 `SCREEN 2` DOES NOT CLEAR THE PATTERN TABLE ON THE REFERENCE. Without the
        # CLS the VG-8020 plane came back ~5000 px on EVERY case, including a plain
        # circle, and near-constant regardless of the figure -- it was counting
        # leftover content, not the drawing. zerobas's SCREEN 2 init zeroes the
        # plane, so only ONE SIDE was wrong, which is the shape that reads as a
        # divergence.
        machine, [("direct", [f"SCREEN 2:CLS:{stmt}"])], batch=False,
        reset=("NEW",), capture=("vram", PATTERN, PLEN),
        boot=14.0 if "CF" in machine else 8.0, step=20.0, cap_gap=4.0)[0]
    if not out:
        return None
    return bytes.fromhex(out.strip())


def main():
    for label, stmt, filed in CASES:
        print(f"\n=== {label}  {stmt}")
        print(f"    filed: {filed}")
        r, z = plane(REF, stmt), plane(ZB, stmt)
        if r is None or z is None:
            print(f"    <NO CAPTURE>  ref={r is not None} zb={z is not None}")
            continue
        rc = sum(bin(b).count("1") for b in r)
        zc = sum(bin(b).count("1") for b in z)
        same = r == z
        diff = sum(bin(a ^ b).count("1") for a, b in zip(r, z))
        print(f"    ref {rc:6d} px  sha {hashlib.sha256(r).hexdigest()[:8]}")
        print(f"    zb  {zc:6d} px  sha {hashlib.sha256(z).hexdigest()[:8]}")
        print(f"    planes {'IDENTICAL' if same else 'DIFFER'}"
              f"   pixels differing: {diff}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
