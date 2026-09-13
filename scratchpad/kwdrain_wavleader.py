#!/usr/bin/env python3
"""WHY does a real BIOS hang on a tape zerobas wrote? The emulator runs said the
recording is ~1/4 the length of the reference's for the SAME one-line program
(124 486 vs 467 322 bytes). This asks the WAVs themselves — no emulator, just
probes/lib/cas_decode.py, which is the tree's own decoder.

If the BYTES agree and only the LEADER differs, the defect is the sync tone: an
MSX BIOS locks onto a long header tone before each block, and zerobas's own reader
evidently needs less of it than a real one does.
"""
import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides, cas_decode
tmp = tempfile.mkdtemp(prefix="wavleader_")
for side in ("vg8020", "zb"):
    cfg = probe_sides.sides(side)[side]
    wav = os.path.join(tmp, f"{side}.wav")
    omsx_repl.run_cases(cfg["machine"],
                        [("d", list(cfg["reset"]) + ['10 PRINT"[Z9]"', 'CSAVE"ZQ"', '@WAIT30'])],
                        batch=False, reset=(), boot=cfg["boot"], step=5.0,
                        cap_gap=120.0, timeout=1200.0,
                        prologue=(f"cassetteplayer new {{{wav}}}",))
    data, info = cas_decode.decode_file(wav)
    secs = os.path.getsize(wav) / info["framerate"] if info.get("framerate") else 0
    print("%-7s %7d B  %5.2fs  halfperiods=%-7s short=%sHz long=%sHz  decoded %d bytes"
          % (side, os.path.getsize(wav), secs, info.get("halfperiods"),
             info.get("short_freq_hz"), info.get("long_freq_hz"), len(data)))
    print("        first 24 decoded bytes: %s" % bytes(data[:24]).hex())
    sys.stdout.flush()
