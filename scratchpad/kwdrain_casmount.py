#!/usr/bin/env python3
"""D-CASORACLE: is the MOUNT FORM the reason no reference reads a tape?

Measured already (kwdrain_casoracle*.out): with a tape mounted from a Tcl
`prologue`, zerobas reads it and NEITHER reference does — VG-8020 and CF-3300,
`CLOAD` and `LOAD"CAS:"`, on a clean-room `.cas` AND on a WAV zerobas recorded.
Every cassette probe in this tree instead passes `-cassetteplayer` on the openMSX
COMMAND LINE, and every one of them runs on the repack machine only, so the two
forms had never been compared on a reference.

`omsx_repl.run_cases` now takes `cassette=`, which is that seam. Same tape, same
verbs, same machines — only the mount form changes.

⚠️ Boot per case with its own mount: the TAPE POSITION survives a case.
"""
import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "probes", "disk"))
import omsx_repl, probe_sides, cas_encode
from bas_tokenise import make_multiline_program

tmp = tempfile.mkdtemp(prefix="casmount_")
cas = os.path.join(tmp, "zq.cas")
open(cas, "wb").write(
    cas_encode.build_cas_basic("ZQ", make_multiline_program([(10, 'PRINT"[Z9]"')], 0x8001)))
print("clean-room .cas fixture: %d bytes" % os.path.getsize(cas))

def run(side, line, how):
    cfg = probe_sides.sides(side)[side]
    kw = {"cassette": cas} if how == "cmdline" else {"prologue": (f"cassetteplayer {{{cas}}}",)}
    caps = omsx_repl.run_cases(cfg["machine"], [("d", list(cfg["reset"]) + ["NEW", line])],
                               batch=False, reset=(), boot=cfg["boot"],
                               step=5.0, cap_gap=90.0, timeout=900.0, **kw)
    cap = caps[0]
    rows = [cap[r*40:(r+1)*40].rstrip() for r in range(24)] if cap else []
    return " | ".join(r.strip() for r in rows if r.strip())[-60:]

for side in ("vg8020", "cf3300", "zb"):
    for how in ("cmdline", "prologue"):
        print("%-7s %-9s CLOAD  %s" % (side, how, run(side, 'CLOAD"ZQ"', how)))
        sys.stdout.flush()
