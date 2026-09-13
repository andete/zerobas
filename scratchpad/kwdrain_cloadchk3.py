#!/usr/bin/env python3
"""Round 3. The VG-8020 printed NOTHING for `CLOAD"ZQ"` where zerobas printed
`Found:ZQ`. Before that is called a divergence, D-KWDISK's lesson applies: a
capture that fires before the machine finishes looks EXACTLY like a refusal, and
a tape leader is long. Same case, a much larger capture window.

⚠️ AND A SECOND CANDIDATE CAUSE, checked in the same run: every cassette probe in
this tree runs on the REPACK machine only ("its own <CassettePort/>"), so whether
the VG-8020 config here has a working cassette at all has never been asked.
"""
import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "probes", "disk"))
import omsx_repl, probe_sides, cas_encode
from bas_tokenise import make_multiline_program
prog = make_multiline_program([(10, 'PRINT"[Z9]"')], 0x8001)
tmp = tempfile.mkdtemp(prefix="kwcload3_")
for gap in (60.0, 150.0):
    cas = os.path.join(tmp, f"vg{int(gap)}.cas")
    open(cas, "wb").write(cas_encode.build_cas_basic("ZQ", prog))
    cfg = probe_sides.sides("vg8020")["vg8020"]
    caps = omsx_repl.run_cases(cfg["machine"],
                               [("stored", omsx_repl.as_stored('CLOAD"ZQ"'))],
                               batch=False, reset=cfg["reset"], boot=cfg["boot"],
                               step=5.0, cap_gap=gap, timeout=900.0,
                               prologue=(f"cassetteplayer {{{cas}}}",))
    cap = caps[0]
    rows = [cap[r*40:(r+1)*40].rstrip() for r in range(24)] if cap else []
    print("vg8020 cap_gap=%-6s tail=%r" % (gap, omsx_repl.screen_tail(cap, "RUN")))
    print("      screen=%s" % " | ".join(r.strip() for r in rows if r.strip())[-95:])
    sys.stdout.flush()
