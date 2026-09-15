#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CHANHOOKID -- WHICH claimed hook cell does a CHANNEL verb arrive through?

D-CHANPRICE stopped phase 3 on a fact: this ROM claims fourteen hook cells and
not one is OPEN, CLOSE, INPUT, MERGE or MAXFILES -- so those verbs have no cell
to point at a disk-ROM body. The CF-3300's census is 35 (D-CFARCH) against our
fifteen named, leaving twenty unidentified. This asks the reference which of them
belongs to which verb.

THE METHOD, inherited from scratchpad/hookid_probe.py (D-NODISKGAP): a CLAIMED
cell holds `F7 <slot> <lo> <hi> C9`; an UNCLAIMED one is a bare `RET`. So
`POKE <cell>,201` un-claims it live on the reference, and the verb that then stops
being handled owns that cell. Black-box: a POKE and a reading, no disassembly.

🔴 THREE CONTROLS, AND EACH CAN FAIL INDEPENDENTLY:
  ctrl.none   poke NOTHING. The verb must read its BASELINE. If merely running
              the program changes the answer, nothing below counts.
  ctrl.named  poke H_FILE ($FE7B), a cell we have ALREADY named, and run FILES.
              It must flip. This is the one that proves the METHOD -- without it
              a flip in an unnamed cell proves nothing.
  ctrl.cross  poke that same H_FILE and run the SUBJECT verb. It must NOT flip.
              If un-claiming any hook broke every verb, a hit would be vacuous.

⚠️ A POKE IS STICKY FOR THE WHOLE BOOT, so every case gets its own machine
(batch=False) and no set is reused.
⚠️ AND A CELL THAT DOES NOT FLIP IS NOT EVIDENCE OF ABSENCE -- it may be a hook
for a verb this sweep does not run. Only a FLIP names anything.
"""
from __future__ import annotations
import os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = "National_CF-3300"
REF_KW = dict(boot=14.0, reset=("", "SCREEN 0"))
H_FILE = 0xFE7B

# the twenty claimed cells basic/sysvars.inc does not name, from the LIVE 35-cell
# census (scratchpad/cf3300_arch_probe.py), not from the superseded 27-cell scan
UNNAMED = [0xFE21, 0xFE26, 0xFE2B, 0xFE4E, 0xFE58, 0xFE5D, 0xFE62, 0xFE71,
           0xFE76, 0xFE80, 0xFE85, 0xFE8A, 0xFE99, 0xFE9E, 0xFEA3, 0xFEAD,
           0xFEB2, 0xFEB7, 0xFFA7, 0xFFAC]

# 🔴 A SUBJECT STATEMENT MUST BE ABLE TO REACH THE HOOK, and the first cut's
# CLOSE and MAXFILES could not. `CLOSE#1` on a channel that was never opened is a
# NO-OP in both implementations and `MAXFILES=2` simply succeeds, so both read
# baseline ERR 0 and nothing could ever flip -- a row made vacuous by the probe's
# own shape, not evidence that the verb has no hook. The close form below opens a
# real channel first, which needs a DISK: pass --diska.
# ⚠️ A SUBJECT IS A LIST OF LINES, NOT ONE LINE, because a typed line past ~38
# columns does not survive this harness -- the second cut put CLOSE's open+close
# on one 42-column line and every case came back with NO READING, which the
# instrument correctly refused to score rather than reporting as "no flip".
SUBJECT = {
    "open":     ['OPEN"NOSUCH.DAT"FOR INPUT AS#1'],
    "close":    ['OPEN"HOOKID.DAT"FOR OUTPUT AS#1', "CLOSE#1"],
    "maxfiles": ["MAXFILES=2", 'OPEN"HOOKID.DAT"FOR OUTPUT AS#1', "CLOSE#1"],
    "merge":    ['MERGE"NOSUCH.BAS"'],
}


def prog(poke, stmt):
    lines = []
    if poke is not None:
        lines.append("10 POKE %d,201" % poke)
    # 🔴 BOTH PATHS PRINT THROUGH THE SAME `PRINT"[";v;"]"` SHAPE, and that is
    # not cosmetic. The first cut wrote the no-error path as `PRINT"[0]"`, whose
    # ECHOED SOURCE LINE contains the literal `[0]` -- so the reader matched the
    # echo of line 40 and every case read 0, including the control that must
    # fail. [[trapsvc-echo-fence]]: a probe's fence is also in the source it
    # echoes. Written this way the echo reads `[";0;"]`, which the reader's
    # digit pattern cannot match, while the OUTPUT reads `[ 0 ]`, which it can.
    lines += ["20 ON ERROR GOTO 100"]
    lines += [f"{30 + i} {t}" for i, t in enumerate(stmt if isinstance(stmt, list)
                                                    else [stmt])]
    lines += [
              '40 PRINT"[";0;"]":END',
              '100 PRINT"[";ERR;"]":END',
              "RUN"]
    for ln in lines:
        if len(ln) > 38:
            raise SystemExit(f"REFUSE: typed line is {len(ln)} cols: {ln!r} -- "
                             "past ~38 it does not survive the harness and every "
                             "case comes back unreadable")
    return lines


def read(cap):
    m = re.search(r"\[\s*(\d+)\s*\]", cap or "")
    return int(m.group(1)) if m else None


def main() -> int:
    verb = sys.argv[1] if len(sys.argv) > 1 else "open"
    if verb not in SUBJECT:
        print(f"usage: {sys.argv[0]} [{'|'.join(SUBJECT)}]")
        return 2
    stmt = SUBJECT[verb]

    cases = [("ctrl.none", prog(None, stmt)),
             ("ctrl.named", prog(H_FILE, "FILES")),
             ("ctrl.cross", prog(H_FILE, stmt))]
    cases += [(f"${c:04X}", prog(c, stmt)) for c in UNNAMED]

    kw = dict(REF_KW)
    if "--diska" in sys.argv:
        import shutil, tempfile
        src = os.path.join(REPO, "disk", "test720.dsk")
        tmp = tempfile.mkstemp(suffix=".dsk")[1]
        shutil.copyfile(src, tmp)      # openMSX writes back; never the committed one
        kw["diska"] = tmp
    # ⚠️ A DISK-WRITING SUBJECT NEEDS A WIDER WINDOW. At cap_gap=30 the close and
    # maxfiles sweeps read NOTHING while the very same program answered fine
    # standalone at 60 -- `OPEN ... FOR OUTPUT` writes directory and FAT sectors.
    # The window is part of the measurement, and a too-small one looks exactly
    # like a verb that never answers.
    gap = 60.0 if "--diska" in sys.argv else 30.0
    caps = omsx_repl.run_cases(REF, cases, batch=False, cap_gap=gap,
                               timeout=5400.0, **kw)
    got = {n: read(c) for (n, _), c in zip(cases, caps)}

    base = got.get("ctrl.none")
    named, cross = got.get("ctrl.named"), got.get("ctrl.cross")
    print(f"subject: {verb}   {stmt}")
    print(f"  ctrl.none  baseline ERR {base}")
    print(f"  ctrl.named FILES with H_FILE un-claimed -> ERR {named}")
    print(f"  ctrl.cross subject with H_FILE un-claimed -> ERR {cross}")
    if base is None:
        print("\nINSTRUMENT FAULT (rc 2): no baseline; nothing below is readable.")
        return 2
    if named != 5:
        print("\n🔴 INSTRUMENT FAULT (rc 2): un-claiming a cell we have NAMED did "
              "not make FILES answer ERR 5, so the METHOD is not working here and "
              "a flip anywhere else would prove nothing.")
        return 2
    if cross != base:
        print("\n🔴 INSTRUMENT FAULT (rc 2): un-claiming H_FILE changed the SUBJECT "
              "too, so a flip does not identify a cell -- it just means some hook "
              "is gone.")
        return 2

    print()
    hits = []
    for c in UNNAMED:
        v = got.get(f"${c:04X}")
        flag = ""
        if v is None:
            flag = "  <NO READING>"
        elif v != base:
            flag = f"  🎯 FLIPPED {base} -> {v}"
            hits.append((c, v))
        print(f"  ${c:04X}  ERR {v}{flag}")
    print()
    if hits:
        print(f"{verb.upper()} arrives through: " +
              ", ".join(f"${c:04X}" for c, _ in hits))
    else:
        print(f"No cell flipped {verb.upper()}. That is NOT proof it has no hook: "
              "a cell can belong to a verb this run does not exercise, and the "
              "statement above may not reach the hook at all.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
