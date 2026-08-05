#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-PINDATA: the dexp==5 bound tables — the only gate that reads them.

docs/spec-rom-region-promote-input.md §5.

`basic/float.asm`'s `tkf_ref32767` / `tkf_ref65535` / `tkf_ref32768` are three
5-byte unpacked-digit bound tables. `domain_convert_core`'s dexp==5 arm loads
their ADDRESS (`ld de,tkf_ref32768`, basic/float-arith.asm:1182) -- a DATA
reference, never a call -- and `dcc_bound5` reads the bytes there. The arm is
entered only for `|value|+0.5` in 10000..99999.

⚠️ **NOTHING IN THE TREE EXERCISED THIS BEFORE.** basic_probe_graphics.py's CIRCLE
corpus tops out at coordinate 80 (dexp 2), and basic_probe_intarg.py covers the
POKE/VPOKE/OUT domains but never the graphics reader. Fifteen bytes of
oracle-pinned constants had no gate at all.

WHO ACTUALLY READS THEM, measured (spec §5.3), not assumed:

  * the CIRCLE **coordinate/radius** conversion, from MAIN with page 1 mapped --
    established by the K1/K1e knife PAIR: raising the bound in place moved four
    `circ_*` rows (so the arm is reached), while relocating the tables into main
    page 1 moved none (so the reader sees main page 1, i.e. is not a tenant).
  * POKE / VPOKE / OUT, from MAIN, address domain (`tkf_ref65535`).
  * ⚠️ NOT the page-1 tenant. `sub/circleparse.asm`'s `cpt_round` does call
    `flt_to_int16`, but only on `minor_ratio*256` where the ratio is `aspect` or
    `1/aspect`, whichever is <= 1 -- so <= 256.5, dexp <= 3. **The dexp==5 arm is
    unreachable from the only tenant caller.** The `asp_*` rows below hold that
    down: they are the tenant path, and they must stay in the shallow arms.

So the pin D-PINDATA put on these 15 bytes is a CLOSURE-CONTRACT pin -- the same
standard check_tenant_closure.py applies to every callee, without asking whether
the arguments that reach it exist -- and NOT a demonstrated live fault. Recorded
that way on purpose: the knife came back green and the green was the finding.

FALSIFICATION (spec §5.4): this gate has been shown to MOVE. Changing
`tkf_ref32767` from 3,2,7,6,7 to 9,9,9,9,9 -- a five-byte edit -- moves
`circ_x40000`, `circ_y40000`, `circ_x99999`, `circ_r40000` and `vpoke_40000`.
A gate never shown to move is not a gate.
"""
from __future__ import annotations
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import omsx_repl  # noqa: E402

REF_MACHINE = "Philips_VG_8020"
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

# (label, statement, reader) -- `reader` is the MEASURED attribution above, not a
# reading of the source.
#   gfx    -- CIRCLE coordinate/radius, main-side, dexp==5 arm
#   stmt   -- POKE/VPOKE/OUT, main-side, dexp==5 arm (address domain)
#   tenant -- sub/circleparse.asm cpt_round; reaches flt_to_int16, dexp <= 3
CASES = [
    # --- dexp==5 arm, strict int16 domain (tkf_ref32767 / tkf_ref32768) -------
    ("circ_x40000", "CIRCLE(40000,100),10", "gfx"),
    ("circ_y40000", "CIRCLE(100,40000),10", "gfx"),
    ("circ_x10000", "CIRCLE(10000,100),10", "gfx"),
    ("circ_x99999", "CIRCLE(99999,100),10", "gfx"),
    ("circ_xneg40000", "CIRCLE(-40000,100),10", "gfx"),
    ("circ_r40000", "CIRCLE(100,100),40000", "gfx"),
    # --- dexp != 5: the arm must NOT be entered -------------------------------
    ("circ_ok", "CIRCLE(80,80),20,15", "gfx"),
    ("circ_x300", "CIRCLE(300,100),10", "gfx"),
    # --- dexp==5 arm, ADDRESS domain (tkf_ref65535 + the wrap path) -----------
    ("poke_40000", "POKE 40000,0", "stmt"),
    ("poke_99999", "POKE 99999,0", "stmt"),
    ("poke_neg40000", "POKE -40000,0", "stmt"),
    ("vpoke_40000", "VPOKE 40000,0", "stmt"),
    ("out_40000", "OUT 40000,0", "stmt"),
    # --- the TENANT path into flt_to_int16: ratio*256, so dexp <= 3. These pin
    #     the tenant call itself, and pin that it stays OUT of the dexp==5 arm.
    ("asp_100", "CIRCLE(80,80),20,15,,,100", "tenant"),
    ("asp_p01", "CIRCLE(80,80),20,15,,,.01", "tenant"),
    ("asp_1", "CIRCLE(80,80),20,15,,,1", "tenant"),
]


def run(machine, stmt):
    prog = ["10 ON ERROR GOTO 100", "15 SCREEN2", f"20 {stmt}",
            "30 SCREEN0:PRINTCHR$(67);CHR$(35):END",
            "100 SCREEN0:PRINTCHR$(35);ERR;CHR$(35)", "RUN"]
    raw = omsx_repl.run_case(machine, "direct", prog) or ""
    e = re.findall(r"#([^#]*)#", raw)
    if e:
        return f"ERR{e[-1].strip()}"
    if "C#" in raw:
        return "cont"
    return f"?({re.sub(r'\s+', ' ', raw).strip()[-30:]!r})"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--machine", default=REF_MACHINE)
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE)
    ap.add_argument("--expect", help="baseline file; report which rows MOVED")
    ap.add_argument("--record", help="write the zb readings to this path")
    ap.add_argument("--no-ref", action="store_true",
                    help="skip the VG-8020 oracle (for knife runs, where the "
                         "baseline IS the comparison)")
    args = ap.parse_args()

    want = {}
    if args.expect:
        for line in open(args.expect):
            line = line.split("#", 1)[0].strip()
            if line:
                k, v = line.split()
                want[k] = v

    rows, ok = [], True
    for label, stmt, reader in CASES:
        zb = run(args.zb_machine, stmt)
        ref = None if args.no_ref else run(args.machine, stmt)
        rows.append((label, zb))
        verdict = ""
        if want:
            same = (zb == want.get(label, "?"))
            verdict = "SAME " if same else "MOVED"
            ok = ok and same
        elif ref is not None:
            # No baseline: the VG-8020 IS the expectation. This is the form the
            # make target runs -- a differential, not a self-comparison.
            same = (zb == ref)
            verdict = "PASS " if same else "FAIL "
            ok = ok and same
        print(f"{verdict:6}{reader:7} {label:16} {stmt:26} "
              f"zb={zb:8} ref={ref if ref is not None else '-'}")

    if args.record:
        with open(args.record, "w") as fh:
            fh.write("# D-PINDATA dexp==5 baseline, zb readings\n")
            for label, zb in rows:
                fh.write(f"{label} {zb}\n")
        print(f"\nrecorded {len(rows)} rows -> {args.record}")
        return 0

    if want:
        moved = [r for r, v in rows if want.get(r) != v]
        print(f"\n{len(rows) - len(moved)}/{len(rows)} unchanged; "
              f"MOVED: {moved if moved else 'none'}")
        return 0 if ok else 1
    n = len(rows)
    print(f"\n{'ALL PASS' if ok else 'SOME FAILED'} ({n} rows vs {args.machine})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
