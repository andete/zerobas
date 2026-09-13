#!/usr/bin/env python3
"""🔬 CSAVE HAS NO SCREEN-OBSERVABLE CONSEQUENCE (D-KWTAPE2), so its kwsweep row
needs the tape read back. The expensive answer is a capture that decodes the
recording; the cheap one is a question about the apparatus:

    does openMSX REWIND a freshly recorded tape when the machine starts reading?

If it does, the row is `CSAVE"ZQ"` followed by `CLOAD"ZQ"` on the same mounted
tape and the witness is the machine's own `Found:ZQ` -- no new plumbing at all.
If it does not, the capture has to be built. Measured before either is written.
"""
import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides

tmp = tempfile.mkdtemp(prefix="taperew_")
wav = os.path.join(tmp, "rw.wav")

for side in ("zb", "vg8020"):
    cfg = probe_sides.sides(side)[side]
    path = os.path.join(tmp, side + ".wav")
    caps = omsx_repl.run_cases(
        cfg["machine"],
        [("d", list(cfg["reset"]) + ['10 PRINT"[Z9]"', 'CSAVE"ZQ"', '@WAIT30',
                                     'NEW', 'CLOAD"ZQ"', 'PRINT"[P9]"'])],
        batch=False, reset=(), boot=cfg["boot"], step=5.0, cap_gap=150.0,
        timeout=1800.0, prologue=(f"cassetteplayer new {{{path}}}",))
    cap = caps[0]
    rows = [cap[r*40:(r+1)*40].rstrip() for r in range(24)] if cap else []
    rows = [r.strip() for r in rows if r.strip()]
    size = os.path.getsize(path) if os.path.exists(path) else -1
    print("%-8s recorded %8d B | %s" % (side, size, " | ".join(rows[-6:])))
    sys.stdout.flush()
print()
print("READ IT AS: `Found:ZQ` AND `[P9]` => the player rewound and the row is")
print("cheap. No `Found:` => it kept the write position and CSAVE needs a capture.")
