#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-GETREC — GET/PUT's record number is capped at 1..255 here. Is that faithful?

`ex_get` came bottom of the substantial handlers when all 135 were ranked by
COMMENT DENSITY. Reading it end to end:

    call skip_comma / inc hl / call eval     ; DE = record number
    ld (GP_RECNO),de                          ; stored RAW -- no domain check

\U0001f7e2 AND THEN THE CONSUMER WAS READ, which is D-VDPDOM's lesson from an hour
ago -- an unchecked parse is only a defect if nothing downstream checks either.
Here something does: `fat_rand_get` (basic/randio-body.inc) rejects a nonzero HIGH
byte and a zero low byte. So the enforced domain is **1..255**.

\U0001f3af THAT IS THE QUESTION, AND IT IS NOT THE USUAL ONE. The usual finding is
a missing check; this is a check that may be TOO TIGHT. A random file can have far
more than 255 records, so `GET #1,256` is an ordinary thing to write, and if the
reference performs it, the cap is a defect that no "add validation" instinct would
have found.

\U0001f534 NEEDS-DISK: the VG-8020 has NO DRIVE, so the CF-3300 is the oracle here
and the VG is not scored -- the trap D-BAREFORM fell into. Each side gets its OWN
copy of the fixture, because the setup must PUT a record to have anything to GET.
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
    ("g.ctl",  "1",   "CONTROL: the record just written"),
    ("g.zero", "0",   "record 0 -- below the base"),
    ("g.neg",  "-1",  "record -1"),
    ("g.256",  "256", "the FIRST record past this tree's 1..255 cap"),
    ("g.300",  "300", "well past the cap"),
    # \U0001f534 THE SEPARATING ROW. `PUT#1,256` is ERR 0 on the reference -- it
    # PERFORMS the write -- while `GET#1,256` is ERR 55. So two rules fit the GET
    # rows: a 1..255 CAP, or "past END OF FILE" (only record 1 was ever written).
    # Record 2 is inside any cap and past EOF, so it tells them apart, and a fix
    # written against the rows above alone could implement either
    # [[two-rules-that-coincide-on-every-row-you-have]].
    ("g.two",  "2",   "inside the cap, PAST EOF -- the separator"),
]
# gp_common is SHARED by GET and PUT, so a fix sited there serves both — which
# means both must be measured before it is written [[a-shared-tail-is-not-a-decision]].
PUT_CASES = [
    ("p.ctl",  "1",   "CONTROL: PUT to the record just written"),
    ("p.zero", "0",   "PUT record 0"),
    ("p.256",  "256", "PUT past the cap"),
]


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="getrec-")
    out = {}
    for tag, rec, note in CASES + PUT_CASES:
        row = {}
        for side, c in SIDES.items():
            img = os.path.join(tmp, f"{tag}-{side}.dsk")
            shutil.copyfile(FIXTURE, img)
            p = ["10 ON ERROR GOTO 900", '20 OPEN"A:R.DAT"AS#1',
                 "30 FIELD#1,10 AS A$", '40 LSET A$="HELLO"', "50 PUT#1,1",
                 "60 E=0",
                 f"70 {'PUT' if tag.startswith('p.') else 'GET'}#1,{rec}",
                 "80 GOTO 300",
                 # \U0001f534 `RESUME 300`, NOT a bare `E=ERR`. The first run of this
                 # probe ended the handler without one, so the CF-3300 fell off the
                 # end of it with `No RESUME in 900`, the program stopped, and every
                 # reference row came back <none> -- which the summary then printed
                 # as "4 divergences". A missing outcome is not a divergence; the
                 # raw screen is what said so [[an-unnamed-outcome-reads-as-no-outcome]].
                 "900 E=ERR:RESUME 300",
                 '300 CLOSE#1:PRINT"ZQ";E;"QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=14.0,
                cap_gap=4.0, timeout=420.0, diska=img)[0] or "")
            v = [g for g in re.findall(r'ZQ\s*([0-9]+)\s*QZ', raw)
                 if '"' not in g and ';' not in g]
            row[side] = v[-1] if v else None
        out[tag] = row
        f = {s_: ("<none>" if row[s_] is None else f"ERR={row[s_]}")
             for s_ in SIDES}
        same = f["cf3300"] == f["zb"]
        verb = "PUT" if tag.startswith("p.") else "GET"
        print(f"  {tag:7s} {verb}#1,{rec:5s} cf={f['cf3300']:10s} zb={f['zb']:10s}"
              f"{'' if same else '   \U0001f534 DIFF'}   {note}", flush=True)

    for cn in ("g.ctl", "p.ctl"):
        c_ = out.get(cn, {})
        if any(c_.get(s_) != "0" for s_ in SIDES):
            print(f"\n\U0001f534 CONTROL {cn} DID NOT READ ERR 0 ({c_}).")
            return 2
    ctl = out.get("g.ctl", {})
    if any(ctl.get(s_) != "0" for s_ in SIDES):
        print(f"\n\U0001f534 THE CONTROL DID NOT READ ERR 0 ({ctl}) -- the random "
              f"file is not being opened, written or read, and no row above means "
              f"anything.")
        return 2
    dis = [t for t in out if out[t]["cf3300"] != out[t]["zb"]]
    print(f"\n=== {len(dis)} divergence(s) against the CF-3300: {dis or 'none'} ===")
    # \U0001f534 THIS SUMMARY USED TO READ "`GET #1,256` refuses too, so the 1..255
    # cap is faithful" -- and that was FALSE. `GET#1,2` is ERR 55 as well, and 2 is
    # inside any cap; `PUT#1,256` is ERR 0, so the cap is not a PUT rule either.
    # The reference's rule is END OF FILE for GET and unbounded for PUT. A summary
    # line that names the wrong rule is worse than none, because the next reader
    # inherits it as a measurement.
    g2 = out.get("g.two", {}).get("cf3300")
    p256 = out.get("p.256", {}).get("cf3300")
    if g2 is not None and p256 is not None:
        print(f"  \U0001f3af THE RULE, SEPARATED: `GET#1,2` (inside any cap, past "
              f"EOF) = ERR {g2}; `PUT#1,256` (past any cap) = ERR {p256}. So the "
              f"reference bounds GET by END OF FILE, not by a record cap, and does "
              f"not bound PUT at all. zerobas's 1..255 test in fat_rand_get is a "
              f"DIFFERENT RULE that happens to agree on three of these rows.")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
