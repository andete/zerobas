#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-KWREST — the surface of the remaining five of D-KWPIN's eight, in one pass.

D-KWPIN pinned eight keywords the reference tokenises and zerobas does not.
`DSKI$` (D-DSKI/D-DSKIWHERE/D-DSKIBYTES/D-DSKIFORM) and `COPY` (D-COPYVERB) are
characterised. This is the other five, so the class stops being a list of names.

⚠️ `DSKO$`, `SET` AND `IPL` WRITE TO THE DISK, AND `kwsweep` NEVER EXECUTES THEM
FOR THAT REASON ("DESTRUCTIVE, never executed"). They are safe here because every
row mounts its OWN COPY of `disk/test720.dsk` — the same rule D-COPYVERB and
`basic_probe_lptverb.py` follow. The shared fixture is never opened for writing.

\U0001f3af THE QUESTION IS THE SURFACE, NOT THE SEMANTICS: which forms run, and with
what error faces. Doing more than that per verb is how a mechanism gets inferred
from one observation, and `DSKI$` already showed what that costs. `DSKO$` gets
BOTH forms because D-DSKIFORM found `DSKI$` to be a function ONLY, and the
asymmetry in `kwsweep`'s own bodies (`a$=dski$(0,0)` vs `dsko$0,0`) is unexplained.

A row reads 7 if it ran clean, the NEGATED error code if it trapped, or `<none>`
if it never came back — which for these verbs is a reading too: a prompt that
blocks (`DSKI$(2,0)` did exactly that) or a machine left waiting.
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

SRC = os.path.join(ROOT, "disk", "test720.dsk")
CF = "National_CF-3300"

CASES = [
    ("k.ctl",     "",                  "CONTROL: no new verb at all -- must read 7"),
    ("k.dskostm", "DSKO$0,0",          "DSKO$ statement form, as kwsweep writes it"),
    ("k.dskofun", "A$=DSKO$(0,0)",     "DSKO$ function form -- the shape DSKI$ turned out to need"),
    ("k.attr",    "A$=ATTR$(0)",       "ATTR$ -- kwsweep calls it MSX-DOS2-era"),
    ("k.cmd",     'CMD"X"',            "CMD -- kwsweep calls it a vendor hook, side effects unknown"),
    ("k.setpw",   'SET PASSWORD "X"',  "SET with an argument"),
    ("k.setbare", "SET",               "SET bare -- is the keyword itself enough to parse?"),
    ("k.ipl",     "IPL",               "IPL -- writes a boot sector, hence the private image"),
    # 🎯 IS THE TAIL PARSED, OR IS THE VERB REJECTED ON SIGHT? Every word
    # above answers ERR 5, never ERR 2, so its arguments are at least accepted.
    # These two ask whether they are LOOKED AT: junk after the keyword reading
    # ERR 5 means the handler raises before parsing (an implementation is a
    # kwtable entry plus one `jp` to Illegal function call); ERR 2 means the tail
    # is parsed first and an implementation owes that parser too.
    ("k.setjunk", "SET ZZZ QQQ",       "junk after SET -- ERR 5 = tail never parsed, ERR 2 = it is"),
    ("k.ipljunk", "IPL ZZZ QQQ",       "junk after IPL -- same question"),
]


def main() -> int:
    out = {}
    for label, verb, note in CASES:
        dsk = os.path.join(tempfile.gettempdir(), f"zb_kwrest_{label}.dsk")
        shutil.copy(SRC, dsk)                      # a PRIVATE image per row
        p = ['10 ON ERROR GOTO 900']
        p.append(f'20 {verb}' if verb else '20 REM no new verb')
        p += ['30 PRINT"ZQ";7;"QZ":END',
              '900 PRINT"ZQ";-ERR;"QZ":END']
        raw = "".join(omsx_repl.run_cases(
            CF, [("direct", ["NEW"] + p + ["RUN"])], batch=False,
            reset=("", "SCREEN 0", "NEW"), boot=14.0, step=5.0,
            run_gap=30.0, cap_gap=5.0, timeout=600.0, diska=dsk)[0] or "")
        v = [g for g in re.findall(r"ZQ\s*(-?\s*[0-9]+)\s*QZ", raw)
             if not any(c in g for c in '"$;')]
        out[label] = int(v[-1].replace(" ", "")) if v else None
        n = out[label]
        face = ("<none: never came back>" if n is None else
                ("ran clean" if n == 7 else f"ERR {-n}"))
        print(f"  {label:10s} {face:24s} {note}", flush=True)

    if out.get("k.ctl") != 7:
        print(f"\n\U0001f534 THE CONTROL DID NOT READ 7 ({out.get('k.ctl')}) -- the "
              f"readout is broken and no row above is a reading.")
        return 2
    ran = [k for k, v in out.items() if k != "k.ctl" and v == 7]
    syn = [k for k, v in out.items() if v == -2]
    other = [f"{k}=ERR{-v}" for k, v in out.items()
             if v is not None and v not in (7, -2)]
    none = [k for k, v in out.items() if v is None]
    print(f"\n\U0001f3af RAN CLEAN: {ran or 'NONE'}")
    print(f"   SYNTAX ERROR (the form does not exist): {syn or 'NONE'}")
    print(f"   OTHER ERROR FACES: {other or 'NONE'}")
    print(f"   NEVER CAME BACK: {none or 'NONE'}")
    print("\nThis probe CHARACTERISES the reference's surface. It does not score "
          "zerobas,\nwhich has none of these keywords (D-KWPIN), and it does not "
          "claim to know what\nany of them DOES.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
