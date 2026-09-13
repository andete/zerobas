#!/usr/bin/env python3
"""D-CASORACLE round 2: the references DO read a tape, so "no oracle" was wrong.
What varied between the runs that failed and the one that worked?

Three candidates, and only a matrix separates them:
  * the FIXTURE   -- a clean-room `.cas` (cas_encode) vs a WAV zerobas RECORDED
  * the MODE      -- direct-typed vs `stored` (numbered line + RUN)
  * the MOUNT     -- already refuted: cmdline and prologue agree on all machines

⚠️ IF THE `.cas` READS AND THE ZEROBAS-WRITTEN WAV DOES NOT, that is not an
apparatus fact at all — it is a FINDING about what zerobas WRITES to tape, and it
is worth more than either keyword.
"""
import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "probes", "disk"))
import omsx_repl, probe_sides, cas_encode
from bas_tokenise import make_multiline_program

tmp = tempfile.mkdtemp(prefix="casmatrix_")
cas = os.path.join(tmp, "zq.cas")
open(cas, "wb").write(
    cas_encode.build_cas_basic("ZQ", make_multiline_program([(10, 'PRINT"[Z9]"')], 0x8001)))
wav = os.path.join(tmp, "zbwrote.wav")

def run(side, case, **kw):
    cfg = probe_sides.sides(side)[side]
    caps = omsx_repl.run_cases(cfg["machine"], [case], batch=False, reset=(),
                               boot=cfg["boot"], step=5.0, cap_gap=90.0,
                               timeout=900.0, **kw)
    cap = caps[0]
    rows = [cap[r*40:(r+1)*40].rstrip() for r in range(24)] if cap else []
    return " | ".join(r.strip() for r in rows if r.strip())[-46:]

# zerobas records the WAV once
cfg = probe_sides.sides("zb")["zb"]
run("zb", ("d", list(cfg["reset"]) + ['10 PRINT"[Z9]"', 'CSAVE"ZQ"', '@WAIT30']),
    prologue=(f"cassetteplayer new {{{wav}}}",))
print("zerobas-written WAV: %d bytes\n" % (os.path.getsize(wav) if os.path.exists(wav) else -1))

for side in ("vg8020", "zb"):
    c = probe_sides.sides(side)[side]
    for tape, label in ((cas, "cas "), (wav, "wav ")):
        direct = ("d", list(c["reset"]) + ["NEW", 'CLOAD"ZQ"'])
        stored = ("stored", omsx_repl.as_stored('CLOAD"ZQ"'))
        print("%-7s %s direct  %s" % (side, label, run(side, direct, cassette=tape)))
        print("%-7s %s stored  %s" % (side, label, run(side, stored, cassette=tape)))
        sys.stdout.flush()
