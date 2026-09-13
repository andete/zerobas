#!/usr/bin/env python3
"""The harness is exonerated: the VG-8020 records 467 322 bytes and reads its own
tape back (`Found:ZQ`), so openMSX's record->play round trip works. zerobas records
124 486 bytes for the SAME one-line program — about a QUARTER — and the VG hangs
on it.

This completes the interop matrix in the other direction: can zerobas read the
REFERENCE's tape? If it can, zerobas's READER is fine and only its WRITER is off,
which is the sharpest statement the evidence supports.
"""
import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
tmp = tempfile.mkdtemp(prefix="wavinterop_")

def run(side, lines, gap=120.0, **kw):
    cfg = probe_sides.sides(side)[side]
    caps = omsx_repl.run_cases(cfg["machine"], [("d", list(cfg["reset"]) + lines)],
                               batch=False, reset=(), boot=cfg["boot"],
                               step=5.0, cap_gap=gap, timeout=1200.0, **kw)
    cap = caps[0]
    rows = [cap[r*40:(r+1)*40].rstrip() for r in range(24)] if cap else []
    return [r.strip() for r in rows if r.strip()]

tapes = {}
for side in ("vg8020", "zb"):
    wav = os.path.join(tmp, f"{side}.wav")
    run(side, ['10 PRINT"[Z9]"', 'CSAVE"ZQ"', '@WAIT30'],
        prologue=(f"cassetteplayer new {{{wav}}}",))
    tapes[side] = wav
    print("%-7s wrote %7d bytes" % (side, os.path.getsize(wav)))

print()
for reader in ("zb", "vg8020"):
    for writer in ("vg8020", "zb"):
        rows = run(reader, ["NEW", 'CLOAD"ZQ"', 'PRINT"[P9]"'], cassette=tapes[writer])
        got = " | ".join(rows[-3:])
        print("%-7s reads %-7s tape:  %s" % (reader, writer, got))
        sys.stdout.flush()
