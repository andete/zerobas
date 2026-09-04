#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RECLENDOM — the OPEN-time domain of `LEN=r`, which the filed item calls unscouted.

`oo_parse_reclen` (basic/files.asm) refuses anything that is not a power of two
in 1..256, "so records tile the 512-byte sector with no straddle". The CF-3300
accepts `LEN=100` and only fails later, at FIELD. So the reference does not
validate tiling at OPEN at all -- but WHAT it validates is unmeasured, and a fix
cannot be priced against "not a power of two" without knowing the real bounds.

This reads the ACCEPT/REJECT boundary only: one OPEN per value, no FIELD, no
GET/PUT. That keeps it a parse question, which the entry is explicit it must
remain -- it "is an OPEN parse question, not a FIELD one".

⚠️ Reuses tranche 65's scratch-disk fixture. Every row OPENs and CLOSEs the same
file, so no row leaves state for the next.

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
TEST_DSK = os.path.join(tempfile.mkdtemp(prefix="reclen-"), "test720.dsk")
shutil.copyfile(_SRC_DSK, TEST_DSK)

# label, statement, what is expected and why
CASES = [
    ("r.0", 'OPEN"TS.DAT"AS #1 LEN=0:CLOSE', 'LEN=0'),
    ("r.1", 'OPEN"TS.DAT"AS #1 LEN=1:CLOSE', 'LEN=1'),
    ("r.2", 'OPEN"TS.DAT"AS #1 LEN=2:CLOSE', 'LEN=2'),
    ("r.3", 'OPEN"TS.DAT"AS #1 LEN=3:CLOSE', 'LEN=3'),
    ("r.7", 'OPEN"TS.DAT"AS #1 LEN=7:CLOSE', 'LEN=7'),
    ("r.100", 'OPEN"TS.DAT"AS #1 LEN=100:CLOSE', 'LEN=100'),
    ("r.127", 'OPEN"TS.DAT"AS #1 LEN=127:CLOSE', 'LEN=127'),
    ("r.128", 'OPEN"TS.DAT"AS #1 LEN=128:CLOSE', 'LEN=128'),
    ("r.255", 'OPEN"TS.DAT"AS #1 LEN=255:CLOSE', 'LEN=255'),
    ("r.256", 'OPEN"TS.DAT"AS #1 LEN=256:CLOSE', 'LEN=256'),
    ("r.257", 'OPEN"TS.DAT"AS #1 LEN=257:CLOSE', 'LEN=257'),
    ("r.300", 'OPEN"TS.DAT"AS #1 LEN=300:CLOSE', 'LEN=300'),
    ("r.512", 'OPEN"TS.DAT"AS #1 LEN=512:CLOSE', 'LEN=512'),
    ("r.1000", 'OPEN"TS.DAT"AS #1 LEN=1000:CLOSE', 'LEN=1000'),
    ("r.32767", 'OPEN"TS.DAT"AS #1 LEN=32767:CLOSE', 'LEN=32767'),
    ("r.neg",  'OPEN"TS.DAT"AS #1 LEN=-1:CLOSE', 'negative'),
    ("c.plain",'OPEN"TS.DAT"AS #1:CLOSE',        'CONTROL: no LEN at all -> must be 0'),
    # ⚠️ ACCEPTING AT OPEN IS ONLY SAFE IF WHAT FOLLOWS SURVIVES IT. A non-tiling
    # record does not divide the 512-byte sector, and this tree's GET/PUT
    # geometry is built on recPerSec = 512/r. These ask what the REFERENCE does
    # after it accepts one -- the entry reports a `FIELD overflow` behind LEN=100
    # and that is worth reading directly rather than inheriting.
    ("f.100",  'OPEN"TS.DAT"AS #1 LEN=100:FIELD #1,100 AS A$:CLOSE', 'FIELD the whole record'),
    ("f.128",  'OPEN"TS.DAT"AS #1 LEN=128:FIELD #1,128 AS A$:CLOSE', 'the tiling twin of f.100'),
    ("f.over", 'OPEN"TS.DAT"AS #1 LEN=100:FIELD #1,101 AS A$:CLOSE', 'one byte past the record'),
    ("p.100",  'OPEN"TS.DAT"AS #1 LEN=100:FIELD #1,100 AS A$:LSET A$="x":PUT #1,1:CLOSE', 'and actually WRITE one'),
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
