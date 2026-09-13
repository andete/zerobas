#!/usr/bin/env python3
"""THE CONTROL THAT DECIDES WHETHER THE LAST FINDING IS ABOUT ZEROBAS OR ABOUT THE
HARNESS.

The VG-8020 HANGS on a WAV zerobas recorded and reads a clean-room `.cas` fine.
Two readings of that:
  (a) zerobas's cassette OUTPUT is off-spec -> a faithfulness defect
  (b) openMSX's record->play round trip is lossy for ANY machine -> apparatus

So: let the VG-8020 record its OWN tape and read it back. If it can, (a). If it
cannot, (b), and zerobas is exonerated.
"""
import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
tmp = tempfile.mkdtemp(prefix="wavctl_")

def run(side, lines, gap=120.0, **kw):
    cfg = probe_sides.sides(side)[side]
    caps = omsx_repl.run_cases(cfg["machine"], [("d", list(cfg["reset"]) + lines)],
                               batch=False, reset=(), boot=cfg["boot"],
                               step=5.0, cap_gap=gap, timeout=1200.0, **kw)
    cap = caps[0]
    rows = [cap[r*40:(r+1)*40].rstrip() for r in range(24)] if cap else []
    return [r.strip() for r in rows if r.strip()]

for side in ("vg8020", "zb"):
    wav = os.path.join(tmp, f"{side}.wav")
    rows = run(side, ['10 PRINT"[Z9]"', 'CSAVE"ZQ"', '@WAIT30', 'PRINT"[W9]"'],
               prologue=(f"cassetteplayer new {{{wav}}}",))
    size = os.path.getsize(wav) if os.path.exists(wav) else -1
    print("%-7s recorded %7d bytes   %s" % (side, size, " | ".join(rows[-3:])))
    rows = run(side, ["NEW", 'CLOAD"ZQ"', 'PRINT"[P9]"'], cassette=wav)
    print("%-7s reads its OWN tape:  %s" % (side, " | ".join(rows[-4:])))
    sys.stdout.flush()
