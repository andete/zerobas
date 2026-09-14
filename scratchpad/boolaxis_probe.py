#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-KWBREADTH batch 8 — can the BOOLEAN rows carry a VALUE without diverging?

`varptr`, `fre` and `rnd` all score a half-plane (`>0`, `>1000`, `<1`) and never
the value. Their ABSOLUTE values are machine-dependent -- RAM layout differs, and
the CF-3300's disk ROM steals RAM the diskless VG-8020 keeps -- so a naive value
row would diverge for a reason that is not a defect. A DELTA cancels the base,
and this measures whether it really does before any row is written.

`rnd` is different in kind: its own note says the PRNG SEQUENCE question is "a
separate question this row does not ask, and filing it as answered here would be
the 'agrees for the wrong reason' trap". Asking it is worth doing -- but as a
MEASUREMENT reported to Joost, not as a sweep row dropped in overnight that might
turn the battery red on a scope decision that is his to make.

⚠️ Reuses basic_probe_kwsweep's own MACH_BOOT / MACH_RESET_PRE.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "probes", "lib"))
import omsx_repl                                                    # noqa: E402

CASES = {
    # array element STRIDE -- a delta, so the base address cancels
    "vstride": ['10 DIM Z(4)', '20 PRINT"[V";VARPTR(Z(1))-VARPTR(Z(0));"]"', 'RUN'],
    # what a 10-element single array COSTS -- again a delta
    "fredelta": ['10 A=FRE(0)', '20 DIM Z(9)', '30 B=FRE(0)',
                 '40 PRINT"[F";A-B;"]"', 'RUN'],
    # does RND(negative) reseed DETERMINISTICALLY? (boolean, but about the path)
    "rndrep": ['10 A=RND(-1)', '20 B=RND(-1)', '30 PRINT"[S";A=B;"]"', 'RUN'],
    # the open question: does the SEQUENCE after a reseed match the reference?
    "rndseq": ['10 A=RND(-1)', '20 PRINT"[R";INT(A*10000);"]"', 'RUN'],
}

MACHINES = [("Philips_VG_8020", 8.0, ("NEW", "CLS")),
            ("National_CF-3300", 14.0, ("", "SCREEN 0", "NEW", "CLS")),
            ("C-BIOS_MSX1_EU_REPACK_DISK", 8.0, ("NEW", "CLS"))]

for machine, boot, reset in MACHINES:
    print(f"=== {machine} ===", flush=True)
    for key, lines in CASES.items():
        caps = omsx_repl.run_cases(
            machine, [(key, list(reset) + lines)],
            batch=False, boot=boot, step=3.0, cap_gap=8.0, timeout=300.0)
        text = " ".join(str(caps[0]).split())
        print(f"  {key:9} {text[-60:]!r}", flush=True)
