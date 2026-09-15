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
    ("k.dski",   'PRINT LEN(DSKI$(0,0))'),      # D-DSKIO: ERR 5 on both, before any parse
    ("h.dsko",   'DSKO$ 0,0'),
    ("h.copy",   'COPY"A"TO"B"'),            # D-COPY: ERR 5 on both diskless sides
    # 🔴 D-NODISKGAP (2026-09-15): TWO VERBS THIS SET NEVER ASKED ABOUT.
    # `LFILES` shares `do_files` with `FILES` -- a shared TAIL WITH TWO HEADS --
    # and D-CHANHOOK gated only the first head, so a diskless build RAN it while
    # `h.files` beside it refused correctly. Fixed in the same slice (the selector
    # goes in first and the gate is shared, so there is nowhere left to enter that
    # skips it); the row is here so nothing can quietly un-gate it again.
    ("h.lfiles", 'LFILES'),
    # ✅ `FIELD` IS GATED SINCE D-FLDGATE (2026-09-15) and this row now AGREES;
    # it was pinned at ('ERR 5 ', 'ERR 59 ') and is unpinned below. Asked in its
    # ARGUMENT form: a bare `FIELD` could be refused for its syntax rather than
    # by the disk gate, and both forms diverged the same way, which is what said
    # the finding was the GATE and not the parse.
    ("h.field",  'FIELD#1,2 AS A$'),
    # 🔴 LSET AND RSET HAD NO ROW AT ALL until D-FLDGATE, which is the same gap
    # that let LFILES run wrong for as long as it existed. D-NODISKGAP measured
    # both: the diskless VG-8020 answers ERR 5 where this tree simply RAN them.
    # They are gated now, so these rows agree -- and an agreeing row is what
    # makes the next regression loud.
    # ⚠️ THEIR CF-3300 COLUMN READS `ERR 2` AND THAT IS THIS PROBE'S OWN SHAPE,
    # not a finding about LSET. The template appends `;` to line 30, and on a
    # machine WITH a disk these two SUCCEED -- so the trailing `;` is then a
    # syntax error. The scored comparison is vg8020 vs zb-nodisk (`ref == nod`),
    # which both answer ERR 5, so the row is sound; the middle column is not a
    # statement about the reference's LSET.
    ("h.lset",   'LSET A$="X"'),
    ("h.rset",   'RSET A$="X"'),
    # 🔴 D-NODISKDEN (2026-09-15) — JOOST'S DENOMINATOR. He ruled that *"every
    # hook claimed on 3300 we don't presumably is a sign of a defect or
    # divergence"*, and the second half of that is this row set: it asked about 17
    # words where `basic/kwtable.inc`'s Disk-BASIC surface is ~37. `LFILES` ran
    # wrong for as long as it existed because it had no row while `FILES` beside it
    # was green, so EVERY verb measured now earns a row — INCLUDING the ones that
    # agree. An agreeing row is what makes the next regression loud.
    # 🟢 ALL EIGHT AGREE WITH THE DISKLESS ORACLE (measured on three sides,
    # scratchpad/nodiskden_probe.py). That is a real answer, not an absence: most
    # claimed hooks do NOT correspond to a divergence here, which is the same
    # lesson `GET`/`PUT` taught — a claimed hook marks a CANDIDATE, not a defect.
    # 🔴 THE `:PRINT""` TAIL IS NOT DECORATION. `run()` appends `;` to the
    # statement, which is fine after a `PRINT` and a SYNTAX ERROR after a bare
    # verb -- so `CLOSE;`, `CLOSE#1;` and `MAXFILES=2;` first read ERR 2 on all
    # three sides and scored as agreement. They agreed on an error THE PROBE
    # ITSELF CAUSED, which is a vacuous row wearing coverage's clothes; the
    # existing rows only escape it because their gate fires before the syntax
    # check. With a `PRINT` to absorb the `;` the verb decides the reading.
    # ⚠️ AND IT PRINTS `K`, NOT `""`. An empty cell is an UNNAMED OUTCOME --
    # it reads like nothing happened, and "nothing happened" is also what a
    # capture failure looks like. `K` says out loud that the statement RAN.
    ("h.close",  'CLOSE:PRINT"K"'),
    ("h.closen", 'CLOSE#1:PRINT"K"'),
    ("v.loc",    'PRINT LOC(1)'),
    ("h.maxf",   'MAXFILES=2:PRINT"K"'),
    ("k.cvd",    'PRINT CVD("ABCDEFGH")'),
    ("h.inputn", 'INPUT#1,A$'),
    ("h.lineinp", 'LINE INPUT#1,A$'),
    ("h.printn", 'PRINT#1,"X"'),
    # 🔴 SIX VERBS CANNOT BE ASKED IN THIS SHAPE AT ALL, and that is recorded
    # rather than left as an empty space:
    #   `SAVE` / `BLOAD` / `BSAVE` — with NO DISK ROM a bare `SAVE"X"` is a
    #     CASSETTE save and WAITS ON THE TAPE MOTOR. The first cut of the scout put
    #     them in a batch, the VG-8020 never came back, and every case after them
    #     read no fence at all — which the scout then flagged as nine divergences.
    #     They need the tape rig or boot-per-case.
    #   `LOAD` / `RUN"<file>"` / `MERGE` — they REPLACE OR MERGE INTO the running
    #     program, so they destroy the probe that asks the question.
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
# ✅ FILES / KILL / NAME LEFT THIS SET 2026-09-03 (D-CHANHOOK): they are routed
# through H.FILE / H.KILL / H.NAME and a diskless build now answers ERR 5, like
# the oracle. They are scored as ordinary agreeing rows, so the gate enforces it.
# ⚠️ `h.open` STAYS, and is characterisation rather than a hook candidate: the
# oracle answers ERR 2 (Syntax error) because `FOR OUTPUT` is not parseable at
# all without Disk BASIC -- a keyword-surface question no handler hook fixes.
# 🔴 REFILLED AGAIN 2026-09-15 (D-NODISKGAP) BY `h.field`, AND THAT IS THIS
# SET DOING ITS JOB rather than a regression: the row is NEW, not newly broken.
# `ex_field` (basic/field.asm:257) has NO disk-presence gate at all -- it goes
# straight to `fch_check`/`fch_mode_class` -- so a diskless build answers the
# CHANNEL's error (59, `File not open`) where the oracle answers 5 because the
# verb is not there. Measured on four sides (scratchpad/nodiskgap_probe.py); the
# BARE form diverges the same way (24 against 5), which is what says this is the
# GATE and not the parse.
# 🔭 Unlike FILES/KILL/NAME/COPY there is NO `H_FIELD` equate to gate with --
# basic/sysvars.inc:3139-3144 has no slot for it -- so fixing this needs a
# decision about WHAT the presence test should be, not just a call. Filed in
# TODO.md; borrowing `H_FILE` would work mechanically and would be a lie.
# ✅ `h.field` LEFT THIS SET on 2026-09-15 (D-FLDGATE). It was pinned at
# ("'ERR 5 '", "'ERR 59 '") -- the VG-8020's ERR 5 against our channel's own
# ERR 59 -- because `FIELD` had no disk-presence gate and main page 1 had 3 B
# free to build one in. The hook re-architecture paid for the bytes, the hook
# address was already measured ($FE2B), and the row now AGREES. A pin is a
# record of a divergence, so removing one is what FIXING it looks like.
PINNED: dict[str, tuple[str, str]] = {
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
