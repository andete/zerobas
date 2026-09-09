#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-PUTEXTEND — does `PUT` past the end EXTEND the file? Read LOF, not ERR.

D-GETREC closed its GET half 6 DIFF -> 0, and left one thing said out loud: the
`p.256` row (`PUT#1,256`) AGREES at ERR 0 on both machines **for different
reasons**. The reference extends the file and succeeds; zerobas refuses and
reports through `gp_fin`'s `jp c,load_error`, which PRINTS without raising, so
`ERR` stays 0 there too. An ERR column structurally cannot separate "did it" from
"declined to do it quietly" [[two-rules-that-coincide-on-every-row-you-have]].

\U0001f3af THE WITNESS IS THE FILE'S LENGTH, WHICH IS WHY THIS PROBE READS `LOF`.
A `PUT` to record N at reclen R grows the file to N*R bytes if it happened. So:

    p.ctl    PUT#1,1    -> LOF 256 on both -- the control that says the fixture
                          wrote anything at all
    p.three  PUT#1,3    -> 768 if it extends; 256 if it refused
    p.256    PUT#1,256  -> 65536 if it extends; 256 if it refused

\U0001f534 AND THE CONTROL CAUGHT *ME*, NOT THE FIXTURE, ON THE FIRST RUN. It was
written expecting LOF 10, because the program says `FIELD#1,10 AS A$` -- but
`FIELD` defines the LAYOUT, not the record length, and `OPEN ... AS#1` with no
`LEN=` defaults to **reclen 256**. Both machines answered 256 and the probe
correctly refused to score anything. A control whose only job is to be boring is
worth writing precisely because it fails first when the reader is wrong
[[a-case-that-agrees-can-agree-for-the-wrong-reason]].

⚠️ NEEDS-DISK: the VG-8020 has no drive, so the CF-3300 is the oracle and the VG
is not scored. Each side gets its OWN copy of the fixture, because every row
writes to it.
⚠️ AND `E` IS STILL READ BESIDE `L`, because a row where the ERR moved AND the
length did not would mean something different again -- reporting one number when
two are available is how `p.256` came to look like agreement in the first place.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_sides                                                # noqa: E402

probe_sides.require_disk("cf3300", "zb")
SIDES = probe_sides.sides("cf3300", "zb")
FIXTURE = os.path.join(ROOT, "disk", "test720.dsk")

CASES = [
    ("p.ctl",   "1",   "CONTROL: the record just written -- LOF must be 256 on both"),
    ("p.three", "3",   "three records in: extends to 768, or refuses and stays 256"),
    ("p.256",   "256", "past this tree's 1..255 cap -- the row that read as agreement"),
]


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="putextend-")
    out = {}
    for tag, rec, note in CASES:
        row = {}
        for side, c in SIDES.items():
            img = os.path.join(tmp, f"{tag}-{side}.dsk")
            shutil.copyfile(FIXTURE, img)
            p = ["10 ON ERROR GOTO 900", '20 OPEN"A:P.DAT"AS#1',
                 "30 FIELD#1,10 AS A$", '40 LSET A$="HELLO"', "50 PUT#1,1",
                 "60 E=0",
                 f"70 PUT#1,{rec}",
                 "80 GOTO 300",
                 "900 E=ERR:RESUME 300",
                 # \U0001f534 LOF BEFORE CLOSE. Reading it after would ask a closed
                 # channel, and the answer to that is a different question.
                 '300 L=LOF(1):CLOSE#1:PRINT"ZQ";E;L;"QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=16.0,
                cap_gap=4.0, timeout=420.0, diska=img)[0] or "")
            v = [g for g in re.findall(r'ZQ\s*([-0-9 ]+?)\s*QZ', raw)
                 if '"' not in g and ';' not in g]
            row[side] = " ".join(v[-1].split()) if v else None
        out[tag] = row
        f = {s: (row[s] if row[s] else "<none>") for s in SIDES}
        print(f"  {tag:8s} PUT#1,{rec:4s}  cf=[E L]={f['cf3300']:10s} "
              f"zb=[E L]={f['zb']:10s}   {note}", flush=True)

    if any(v is None for r in out.values() for v in r.values()):
        print("\n  \U0001f534 A ROW HAS NO READING -- nothing is concluded.")
        return 2

    def lof(tag, side):
        try:
            return int(out[tag][side].split()[1])
        except (ValueError, IndexError):
            return None

    if lof("p.ctl", "cf3300") != 256 or lof("p.ctl", "zb") != 256:
        print(f"\n  \U0001f534 THE CONTROL DID NOT WRITE ONE 256-BYTE RECORD "
              f"(cf={lof('p.ctl','cf3300')}, zb={lof('p.ctl','zb')}) -- either the "
              f"default record length moved or the fixture is not what this probe "
              f"thinks it is, so no row below is readable.")
        return 2

    print()
    for tag in ("p.three", "p.256"):
        a, b = lof(tag, "cf3300"), lof(tag, "zb")
        if a == b:
            print(f"  {tag}: LOF agrees at {a} -- no extension divergence here.")
        else:
            print(f"  \U0001f534 {tag}: the reference grew the file to {a}; zerobas left "
                  f"it at {b}. The ERR columns were EQUAL -- only LOF separates "
                  f"them, which is the whole point of this probe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
