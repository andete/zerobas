#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""TODO sweep 2026-08-26, tranche 65 — the NAME verb, the one D-FNEXPR2 skipped.

T-B42E11 closed "the face for a non-string filename" by measuring SIX verbs
(OPEN/KILL/SAVE/LOAD/BLOAD/FILES). Its own plan named THREE — OPEN, KILL and
**NAME** — and NAME is not among the six. `ex_name` calls `fname_expr` twice
(basic/files.asm:1567, 1586), so it inherits the fix structurally; what is
unmeasured is whether it SAYS so.

🔴 AND THE COMMENT ABOVE THE SECOND CALL STILL NAMES THE PRE-FIX FACE:
`NAME"x.dat"AS 5` is documented in basic/files.asm as "still `Syntax error`".
After D-FNEXPR2, `fname_expr` sends a non-string to `els_tc_common`, i.e.
ERR 13. This asks the machine which one it is.

ROUND 1 was zerobas-only (the claim under test was a comment about THIS
tree). It answered **24 `Missing operand`** at the new-name position -- a
THIRD face, neither the comment's ERR 2 nor the fix's ERR 13 -- so round 2
adds the CF-3300, which is the only machine that can say whether 24 is right.
ONE REFERENCE: `NAME` is Disk BASIC; a diskless VG-8020 cannot express it.

⚠️ ERR CODES, NOT MESSAGE TEXT — a code survives message drift and reads
unambiguously off a SCREEN-0 scrape.
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ⚠️ A COPY, NOT THE TRACKED IMAGE. `NAME"HI.TXT"AS 5` asks the machine to
# RENAME a real directory entry; if any side gets further than expected it
# would mutate a tracked build input. Both sides drive the same scratch copy
# under /tmp/zerobas (`make temp-root-check`).
_SRC_DSK = os.path.join(REPO, "disk", "test720.dsk")   # `diska` is a PATH, not a flag
TEST_DSK = os.path.join(tempfile.mkdtemp(prefix="t65-"), "test720.dsk")
shutil.copyfile(_SRC_DSK, TEST_DSK)

# label, statement, what is expected and why
CASES = [
    ("name.as5",  'NAME"X.DAT"AS 5',  "THE SUBJECT. comment says ERR 2 Syntax; fix implies ERR 13"),
    ("name.old5", 'NAME 5 AS"X.DAT"', "the OLD-name position, fname_expr's first call"),
    ("ctl.kill5", 'KILL 5',           "CONTROL: D-FNEXPR2 measured ERR 13 vs the CF-3300"),
    ("ctl.open5", 'OPEN 5 AS #1',     "CONTROL: D-FNEXPR2 measured ERR 13 vs the CF-3300"),
    ("ctl.div0",  'KILL 1/0',         "CONTROL: the operand's own fault wins -> ERR 11, NOT 13"),
    ("ctl.wf",    'NAME"NOSUCH.DAT"AS"Y.DAT"', "CONTROL: well formed -> a FILE error (53), not a type one"),
    # 🎯 THE DISCRIMINATOR. `name.as5` uses an ABSENT old file, so a reference
    # answer of 53 has TWO sufficient causes: "the reference looks the old file
    # up BEFORE evaluating the new name", or "the reference never faults on the
    # new-name operand at all". `HI.TXT` EXISTS on test720.dsk, so the lookup
    # succeeds and only the second cause can still produce a non-type face.
    ("name.ex5",  'NAME"HI.TXT"AS 5', "DISCRIMINATOR: old file EXISTS -- separates lookup-first from never-faults"),
]


def main():
    cases = [(lab, ["10 ON ERROR GOTO 100",
                    f"20 {stmt}",
                    '30 PRINT"[";0;"]":END',
                    '100 PRINT"[";ERR;"]":END',
                    "RUN"])
             for lab, stmt, _ in CASES]
    sides = {"zb": dict(machine=ZB, boot=8.0, step=2.5, reset=("NEW", "CLS")),
             "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                            reset=("", "SCREEN 0", "NEW", "CLS"))}
    reads = {}
    for side, kw in sides.items():
        m = kw.pop("machine")
        reads[side] = omsx_repl.run_cases(m, cases, diska=TEST_DSK, **kw)
    raw = reads["zb"]
    # 🔴 READ THE SPAN **AFTER THE `RUN` ECHO**. The first cut of this probe
    # looked for its own marker anywhere on the screen and found it in the
    # ECHO OF LINE 30 -- so every row read the same literal and the run
    # reported six-way agreement on a value no case had produced. That is the
    # fail-by-agreeing shape, and it passed rc=0.
    bad = []
    got = {}
    for (lab, stmt, exp), r in zip(CASES, raw):
        got[lab] = (omsx_repl.result_span_after_echo(r, "RUN") or "<none>").strip()
    ref = {}
    for (lab, stmt, exp), r in zip(CASES, reads["cf3300"]):
        ref[lab] = (omsx_repl.result_span_after_echo(r, "RUN") or "<none>").strip()
    print(f"{'row':10s} {'cf3300':>8s} {'zb':>8s}  {'':4s} statement   -- expectation")
    for lab, stmt, exp in CASES:
        mark = "DIFF" if ref[lab] != got[lab] else "  ok"
        print(f"{lab:10s} {ref[lab]:>8s} {got[lab]:>8s}  {mark}  {stmt}   -- {exp}")
    bad += [l for l in ref if ref[l] in ("<none>", "")]
    if bad:
        print(f"\nINSTRUMENT FAULT: no reading on {sorted(set(bad))} -- no verdict.")
        return 2
    bad += [l for l in got if got[l] in ("<none>", "")]
    if bad:
        print(f"\nINSTRUMENT FAULT: no reading on {bad} -- no verdict.")
        return 2
    # THE INSTRUMENT'S OWN RED ARM: two controls that MUST disagree. If ERR 11
    # and ERR 13 read the same, the readout cannot separate error codes and
    # every agreement above is worthless.
    if got["ctl.div0"] == got["ctl.kill5"]:
        print(f"\nINSTRUMENT FAULT: `KILL 1/0` and `KILL 5` both read "
              f"{got['ctl.div0']!r}. The readout cannot tell two error codes "
              f"apart, so nothing above is a reading.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
