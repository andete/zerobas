#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-NODISK — a DISKLESS zerobas, scored against a diskless MSX.

🧭 STANDING DECISION (Joost, 2026-09-03): *"the diskless zerobas should be an
official build target and any disk related thing should be validated on both."*
`C-BIOS_MSX1_EU_REPACK_NODISK` is that target — the same merged main ROM and
sub-ROM with slot 3-1 empty, installed by `make repack-machine` alongside the
disk machine so neither can go stale against the other.

THE ORACLE IS THE PHILIPS VG-8020, and for once that needs no argument: it *is*
this configuration on real hardware — an MSX1 with no disk ROM. The disk machine
is carried in the table as a third column, for the record, so the two zerobas
builds can be read against each other in one place.

WHAT THIS MEASURES. On real MSX the MAIN ROM owns the keyword table (measured:
the diskless VG-8020 crunches `MKS$` to `FF AF`) and the DISK ROM supplies the
implementation through hooks — so a diskless machine tokenises a disk verb and
then raises `Illegal function call`. zerobas implements every disk verb
BASIC-side (`disk/disk.asm`: BASIC reaches files through the BDOS SYSTEM vector,
"NOT through the H.* / HPHYD chain"), so a diskless zerobas ANSWERS instead.

🔴 THE SUBJECT ROWS ARE PINNED TO THEIR EXACT CURRENT VALUES, NOT MERELY ALLOWED
TO DIVERGE. A gate that just tolerated them would stay green through a
regression AND through a fix, and this project has been bitten by both: a filed
row that quietly stopped diverging is the `CVI` shape (`tools/filed-row-known.txt`
opens on it). Pinning means the gate goes RED when the answer CHANGES in either
direction, which is what makes it a measurement rather than a permission slip.

🟢 CONTROLS, and they are what says the diskless machine is real: `c.print` /
`c.str` are plain BASIC and must be identical on all three; `v.eof` / `v.lof`
are disk verbs that ALREADY refuse correctly (ERR 59 everywhere), so they
separate "zerobas leaks every disk verb" from the true shape — it leaks exactly
the ones that need no medium.

⚠️ ROWS NEEDING A LIVE DISK ARE OUT BY CONSTRUCTION. `OPEN`/`FILES`/`KILL`/`NAME`
return the fixture's `load error` on a diskless machine — an UNREADABLE cell, not
a divergence. Scoring them would have inflated the finding by a third, and an
unreadable cell that reads as a defect is the failure this probe set exists to
avoid.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import omsx_repl                                                  # noqa: E402

SIDES = {
    "vg8020":    ("Philips_VG_8020", 8.0, ("NEW",)),          # THE ORACLE
    "zb-disk":   (os.environ.get("ZEROBAS_BASIC_MACHINE",
                                 "C-BIOS_MSX1_EU_REPACK_DISK"), 8.0, ("NEW",)),
    "zb-nodisk": ("C-BIOS_MSX1_EU_REPACK_NODISK", 8.0, ("NEW",)),
}

CASES = [
    ("c.print",  'PRINT 1+1'),
    ("c.str",    'PRINT LEN("ABC")'),
    ("k.mks",    'PRINT LEN(MKS$(1.5))'),
    ("k.mkd",    'PRINT LEN(MKD$(1.5))'),
    ("k.cvs",    'PRINT CVS(MKS$(1.5))'),
    ("k.mki",    'PRINT LEN(MKI$(258))'),
    ("k.cvi",    'PRINT CVI(MKI$(258))'),
    ("v.dskf",   'PRINT DSKF(0)'),
    ("v.eof",    'PRINT EOF(1)'),
    ("v.lof",    'PRINT LOF(1)'),
    ("v.cvistr", 'PRINT CVI("AB")'),
    ("v.mkifld", 'PRINT ASC(MKI$(1))'),
]

# Rows that MUST agree with the oracle. A red here is a plain defect.
CONTROLS = {"c.print", "c.str", "v.eof", "v.lof"}

# 🔴 THE KNOWN DIVERGENCES, PINNED. (vg8020, zb-nodisk) exactly as measured
# 2026-09-03. Owned by the TODO.md item "SHOULD THE DISK-BASIC VERBS LIVE IN
# disk.rom BEHIND A HOOK". A change in EITHER column is a gate failure.
PINNED = {
    "k.mks":    ("'ERR 5 '", "' 4 '"),
    "k.mkd":    ("'ERR 5 '", "' 8 '"),
    "k.cvs":    ("'ERR 5 '", "' 1.5 '"),
    "k.mki":    ("'ERR 5 '", "' 2 '"),
    "k.cvi":    ("'ERR 5 '", "' 258 '"),
    "v.dskf":   ("'ERR 5 '", "' 0 '"),
    "v.cvistr": ("'ERR 5 '", "' 16961 '"),
    "v.mkifld": ("'ERR 5 '", "' 1 '"),
}


def run(side, stmt):
    machine, boot, reset = SIDES[side]
    prog = ['10 ON ERROR GOTO 90', '20 PRINT"<";', f'30 {stmt};',
            '40 PRINT">":END', '90 PRINT"<ERR";ERR;">"', 'RUN']
    raw = omsx_repl.run_cases(machine, [("direct", list(reset) + prog)],
                              batch=False, reset=(), boot=boot, step=5.0,
                              cap_gap=10.0, timeout=300.0)[0] or ""
    m = re.findall(r"<([^<>]*)>", "".join(raw))
    return repr(m[-1]) if m else "<NO OUTPUT>"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", action="store_true", help="rc=1 on any red")
    ap.add_argument("--sides", default="vg8020,zb-disk,zb-nodisk")
    a = ap.parse_args()
    sides = a.sides.split(",")
    res = {s: {lab: run(s, st) for lab, st in CASES} for s in sides}
    w = max(len(l) for l, _ in CASES)
    print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>22}" for s in sides) + "   verdict")
    red_ctl, drift, blank = [], [], []
    for lab, _ in CASES:
        vals = [res[s][lab] for s in sides]
        ref, nod = res["vg8020"][lab], res["zb-nodisk"][lab]
        if any(v == "<NO OUTPUT>" or "load error" in v for v in vals):
            blank.append(lab); tag = "🔴 UNREADABLE"
        elif lab in CONTROLS:
            ok = ref == nod
            if not ok:
                red_ctl.append(lab)
            tag = "ok (control)" if ok else "🔴 CONTROL RED"
        elif lab in PINNED:
            want = PINNED[lab]
            if (ref, nod) == want:
                tag = "known-divergent, pinned"
            else:
                drift.append(lab)
                tag = f"🔴 DRIFT from pin {want}"
        else:
            ok = ref == nod
            tag = "ok" if ok else "🔴 UNPINNED DIVERGENCE"
            if not ok:
                drift.append(lab)
        print(f"{lab:<{w}}  " + "  ".join(f"{v:>22}" for v in vals) + f"   {tag}")
    print(f"\nrows {len(CASES)}  controls-red {len(red_ctl)}  "
          f"pin-drift {len(drift)}  unreadable {len(blank)}  "
          f"pinned-divergent {len(PINNED)}")
    if drift:
        print("  🔴 A PINNED ROW CHANGED. If a disk verb was FIXED, that is good "
              "news and the pin must move WITH the filing that owns it -- an "
              "un-updated pin is how a fixed row goes back to looking normal.")
    bad = red_ctl + drift + blank
    print("NODISK: PASS" if not bad else f"NODISK: RED ({len(bad)})")
    return 1 if (a.gate and bad) else 0


if __name__ == "__main__":
    sys.exit(main())
