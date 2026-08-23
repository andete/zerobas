#!/usr/bin/env python3
"""Why did K-FE1 redden nothing? — and what row WOULD score raise_error's reset.

K-FE1 disabled `raise_error`'s `ld (FN_FEND),a` (basic/interp.asm) and
`make deffn-strict` stayed 0 of 69 divergent. `o.errrestore` is the row that
file's own comment names as "the row that says so", and it did not move.

THE HYPOTHESIS, read out of basic/interp.asm's own headers: `X/0` is a DEFERRED
error. `fp_runtime_error`'s header says the float ops "have no mid-expression
unwind, only SET FPERR and yield a defined value (0)", and the abort is
"realized at the statement boundary by the driver that checks FPERR right after
its eval()". So in `Y=FNA(2)` with body `X/0` the FN call RETURNS NORMALLY,
fn_leave restores the frame in the ordinary way, and only THEN does ex_let's
FPERR check funnel into raise_error. There is no stale frame at that point, so
the reset is a no-op on this row and o.errrestore cannot see it either way.

If that is right, the row that scores the reset needs a fault raised IMMEDIATELY
inside the body -- one that reaches `jp raise_error` while the servicer's frame
is live and the trap path resets SP, so fn_leave never runs at all. An undefined
inner function is exactly that: the tenant answers request 0 and the servicer
does `ld a,(FN_TYP) / jp raise_error`.

    20 X=5:DEF FNA(X)=FNZ(0)
    30 ON ERROR GOTO 800
    40 Y=FNA(2)
    60 CLS:PRINT"[";X;E;"]":END
   800 E=ERR:RESUME 60

🔴 THE WANT COLUMN IS MEASURED HERE, NOT PREDICTED. This runs the candidate on
BOTH references and on zerobas through the probe's OWN `build()`/`face()`, so
the fixture is identical to the 69 rows'. `err.deferred` (o.errrestore's program,
verbatim) rides along as the separating control: the two rows differ only in
which error the body raises, so if they answer differently it is the DEFERRAL
that separates them and nothing else.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
import basic_probe_deffn as P                                     # noqa: E402

NEW = {
    # the candidate: an IMMEDIATE raise inside the body (ERR 18, from the tenant)
    "err.immediate": (["X=5:DEF FNA(X)=FNZ(0)", "ON ERROR GOTO 800",
                       "Y=FNA(2)"], "X;E", ["800 E=ERR:RESUME 60"]),
    # the separating control: o.errrestore's program, verbatim (DEFERRED FPERR)
    "err.deferred": (["X=5:DEF FNA(X)=X/0", "ON ERROR GOTO 800",
                      "Y=FNA(2)"], "X;E", ["800 E=ERR:RESUME 60"]),
    # ...and a second immediate one, from the OTHER disposition the tenant owns:
    # a string body in a numeric function is ERR 13, raised at dfn_bodydone with
    # the frame still live.
    "err.immediate13": (["X=5:DEF FNA(X)=A$", "ON ERROR GOTO 800",
                         "Y=FNA(2)"], "X;E", ["800 E=ERR:RESUME 60"]),
}

P.CASES.update(NEW)
labels = sorted(NEW)
sides = sys.argv[1].split(",") if len(sys.argv) > 1 else ["vg8020", "cf3300", "zb"]

print("program shape (err.immediate):")
for l in P.build("err.immediate")[0]:
    print(f"    {l}")
print()

faces = {s: P.run_side(s, labels) for s in sides}
W = max(len(l) for l in labels)
for l in labels:
    vals = {s: faces[s][l] for s in sides}
    agree = len({v for s, v in vals.items() if s != "zb"}) == 1
    print(P.row_or_print(l, W, vals) if hasattr(P, "row_or_print") else
          f"  {l:<{W}}  " + "  ".join(f"{s}={v!r}" for s, v in vals.items())
          + ("" if agree else "   ⚠️ THE REFERENCES DISAGREE — not a want"))
