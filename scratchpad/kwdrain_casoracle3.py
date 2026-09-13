#!/usr/bin/env python3
"""The VG-8020 cannot read a tape in this rig — not the fixture (zerobas's own tape
fails there too) and not CLOAD (`LOAD"CAS:"` fails identically). So the tape verbs
have NO ORACLE on the usual reference.

🎯 BUT THE OTHER REFERENCE HAS A CASSETTE PORT TOO. The CF-3300 is this tree's
oracle for everything Disk BASIC; nobody has asked whether it can read a TAPE. If
it can, `CLOAD`/`CSAVE` have an oracle after all and the words are not blocked on
apparatus at all — which is the same shape as D-KWORACLE, where the CF-3300 turned
out to read a screen everyone had written off.
"""
import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
tmp = tempfile.mkdtemp(prefix="kwcasor3_")
wav = os.path.join(tmp, "zbwrote.wav")

def run(side, lines, prologue, gap=90.0):
    cfg = probe_sides.sides(side)[side]
    caps = omsx_repl.run_cases(cfg["machine"], [("d", list(cfg["reset"]) + lines)],
                               batch=False, reset=(), boot=cfg["boot"],
                               step=5.0, cap_gap=gap, timeout=900.0,
                               prologue=prologue)
    cap = caps[0]
    rows = [cap[r*40:(r+1)*40].rstrip() for r in range(24)] if cap else []
    return " | ".join(r.strip() for r in rows if r.strip())

run("zb", ['10 PRINT"[Z9]"', 'CSAVE"ZQ"', '@WAIT30', 'PRINT"[W9]"'],
    (f"cassetteplayer new {{{wav}}}",))
print("tape written: %d bytes" % (os.path.getsize(wav) if os.path.exists(wav) else -1))
print("cf3300 <CassettePort/>? ", end="")
import subprocess
x = subprocess.run(["grep", "-c", "CassettePort",
                    os.path.expanduser("~/Downloads/openmsx-21/share/machines/National_CF-3300.xml")],
                   capture_output=True, text=True)
print((x.stdout or x.stderr).strip())
for side, lines, label in (
        ("cf3300", ['NEW', 'CLOAD"ZQ"'],    'cf3300 CLOAD"ZQ"'),
        ("cf3300", ['NEW', 'LOAD"CAS:ZQ"'], 'cf3300 LOAD"CAS:ZQ"'),
):
    print("%-22s %s" % (label, run(side, lines, (f"cassetteplayer {{{wav}}}",))[-85:]))
    sys.stdout.flush()
