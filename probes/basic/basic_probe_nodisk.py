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
    # --- the CHANNEL verbs -------------------------------------------------
    # 🔴 THESE WERE EXCLUDED AS "UNREADABLE" AND THAT WAS WRONG (corrected
    # 2026-09-03). The reasoning was that they "return the fixture's `load error`
    # on a diskless machine -- an UNREADABLE cell, not a divergence", and it was
    # even argued that counting them "would have inflated this finding by a
    # third". `load error` is not the fixture: it is ZEROBAS'S OWN MESSAGE,
    # printed by the machine, which then carries on -- a following `PRINT"C"`
    # still answers. So the cell was always readable and these were always
    # divergences: the oracle says `Illegal function call` (the verb does not
    # exist without a disk ROM) while zerobas RUNS the verb and fails on the
    # medium.
    ("h.files",  'FILES'),
    ("h.kill",   'KILL"NOSUCH.XXX"'),
    ("h.name",   'NAME"A"AS"B"'),
    ("h.open",   'OPEN"X"FOR OUTPUT AS#1'),
]

# Rows that MUST agree with the oracle. A red here is a plain defect.
CONTROLS = {"c.print", "c.str", "v.eof", "v.lof"}

# 🔴 THE KNOWN DIVERGENCES, PINNED. (vg8020, zb-nodisk) exactly as measured
# 2026-09-03. Owned by the TODO.md item "SHOULD THE DISK-BASIC VERBS LIVE IN
# disk.rom BEHIND A HOOK". A change in EITHER column is a gate failure.
# ✅ EMPTY SINCE 2026-09-03 (D-MKHOOK completed), AND THAT IS THE POINT OF THE
# WHOLE PROBE. It opened with EIGHT pinned divergences -- the disk verbs that need
# no medium, answering where a diskless MSX raises ERR 5. All seven are now routed
# through their own documented hook (H.DSKF/H.MKI$/H.MKS$/H.MKD$/H.CVI/H.CVS/
# H.CVD), so a diskless build REFUSES because the handler is not there, which is
# how the reference gets it right.
#
# 🔴 EMPTY IS NOT "NOTHING TO CHECK" -- IT IS THE STRICTEST STATE THIS GATE HAS.
# Every row is now scored against the oracle, so ANY of them regressing is a plain
# failure with no pin to hide behind. A new disk verb that answers on a diskless
# build lands here as a red row, not as an entry someone has to remember to add.
# 🔴 REFILLED 2026-09-03: the CHANNEL verbs, whose exclusion as "unreadable" was
# withdrawn the same day. zerobas RUNS them and fails on the MEDIUM (`load error`)
# where a diskless MSX refuses because the verb is not there. Their hooks are
# named and unclaimed: H.FILE $FE7B, H.KILL $FDFE, H.NAME $FDF9.
# ⚠️ `h.open` is a DIFFERENT CLASS and is pinned as characterisation, not as a
# hook candidate: the oracle answers ERR 2 (Syntax error), because `FOR OUTPUT`
# is not parseable without Disk BASIC at all. That is a keyword-surface question,
# not something a handler hook can fix.
PINNED: dict[str, tuple[str, str]] = {
    "h.files": ("'ERR 5 '", "'load error                             '"),
    "h.kill":  ("'ERR 5 '", "'load error                             '"),
    "h.name":  ("'ERR 5 '", "'load error                             '"),
    "h.open":  ("'ERR 2 '", "'load error                             '"),
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
        # 🔴 `load error` USED TO COUNT AS UNREADABLE HERE. It is not: it is
        # zerobas's own message, printed by a machine that then carries on. Only a
        # genuinely absent capture is unreadable.
        if any(v == "<NO OUTPUT>" for v in vals):
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
