#!/usr/bin/env python3
"""D-CASLEAD: how long must ZEROBAS'S OWN leader be for a real BIOS to lock onto it?

🔴 CLEAN-ROOM NOTE, AND IT SHAPES THE METHOD. tape/PROVENANCE.md marks
CAS_LONGLEN/CAS_SHORTLEN QUARANTINED: "our own choice ... deliberately *not* the
original's HEADER value ... confirmed by round-trip". So this does NOT measure the
reference's leader and copy it. It raises OUR value until the reference can read
what WE write — a black-box requirement on our own output, which is the same kind
of claim the quarantine already allows, and it replaces a round-trip validation
that could only ever test our reader against our writer.

Per candidate: patch the two constants, rebuild, have zerobas RECORD a tape, and
ask the VG-8020 to read it. `PRINT"[P9]"` after the CLOAD is the prompt witness —
without it a hang and a silent completion look identical.

    python3 scratchpad/kwdrain_leaderfix.py 4000 8000 16000
"""
import os, re, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
TAPE = os.path.join(ROOT, "tape", "tape.asm")
orig = open(TAPE, encoding="utf-8").read()

def set_leader(longlen):
    s = re.sub(r"(CAS_LONGLEN:\s+equ\s+)\d+", r"\g<1>%d" % longlen, orig)
    s = re.sub(r"(CAS_SHORTLEN:\s+equ\s+)\d+", r"\g<1>%d" % (longlen // 2), s)
    open(TAPE, "w", encoding="utf-8").write(s)
    r = subprocess.run(["make", "repack-machine"], cwd=ROOT,
                       capture_output=True, text=True)
    return r.returncode

def run(side, lines, gap=150.0, **kw):
    cfg = probe_sides.sides(side)[side]
    caps = omsx_repl.run_cases(cfg["machine"], [("d", list(cfg["reset"]) + lines)],
                               batch=False, reset=(), boot=cfg["boot"], step=5.0,
                               cap_gap=gap, timeout=1800.0, **kw)
    cap = caps[0]
    rows = [cap[r*40:(r+1)*40].rstrip() for r in range(24)] if cap else []
    return [r.strip() for r in rows if r.strip()]

try:
    for val in [int(a) for a in sys.argv[1:]] or [4000]:
        if set_leader(val) != 0:
            print("%6d  BUILD FAILED" % val); continue
        tmp = tempfile.mkdtemp(prefix="lead_")
        wav = os.path.join(tmp, "t.wav")
        run("zb", ['10 PRINT"[Z9]"', 'CSAVE"ZQ"', '@WAIT30'],
            prologue=(f"cassetteplayer new {{{wav}}}",))
        size = os.path.getsize(wav) if os.path.exists(wav) else -1
        rows = run("vg8020", ["NEW", 'CLOAD"ZQ"', 'PRINT"[P9]"'], cassette=wav)
        tail = " | ".join(rows[-3:])
        ok = "[P9]" in tail and "Found:ZQ" in " | ".join(rows)
        print("long=%-6d short=%-6d  wav=%7d B  VG %s  %s"
              % (val, val // 2, size, "READS" if ok else "HANGS", tail[-52:]))
        sys.stdout.flush()
finally:
    open(TAPE, "w", encoding="utf-8").write(orig)
    subprocess.run(["make", "repack-machine"], cwd=ROOT, capture_output=True)
    print("tape.asm restored to its committed value and rebuilt")
