#!/usr/bin/env python3
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT); sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl
ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
def run(lines):
    caps = omsx_repl.run_cases(ZB, [("direct", lines)], batch=True,
                               reset=("NEW","CLS"), boot=8.0, step=4.0, timeout=300.0)
    return "".join(caps[0] or [])
for N in (1848, 1852, 1856, 1860, 1862, 1864):
    # DIM Z(N); mark whether DIM OOMs (X after), then 26 scalars, count OOM,
    # and check Z$ (last) specifically via a trailing marker.
    lines = ['CLEAR 200,50000', f'DIM Z({N})', 'PRINT"<AD>"'] \
            + [f'{c}$="1"' for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"] \
            + ['PRINT"<ZLAST>"']
    txt = run(lines)
    # DIM OOM => "Out of memory" appears BEFORE "<AD>"
    pre = txt.split("<AD>")[0] if "<AD>" in txt else txt
    dim_oom = "Out of memory" in pre
    ooms = txt.count("Out of memory")
    print(f"N={N}: dim_oom={dim_oom} total_oom={ooms} sawAD={'<AD>' in txt}", flush=True)
