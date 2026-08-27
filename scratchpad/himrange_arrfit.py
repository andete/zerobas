#!/usr/bin/env python3
"""Find the DIM Z(N) fit under CLEAR 200,50000 (empty program) and how many
string scalars OOM after a given N. Probe several N, report per-N."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT); sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl
ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

def run(lines):
    caps = omsx_repl.run_cases(ZB, [("direct", lines)], batch=True,
                               reset=("NEW","CLS"), boot=8.0, step=4.0, timeout=300.0)
    return "".join(caps[0] or [])

for N in (1700, 1750, 1780, 1800, 1820, 1840):
    # DIM then a run of 26 string scalars A$..Z$, count OOMs, mark DIM result
    lines = ['CLEAR 200,50000', f'DIM Z({N})', 'PRINT"<DIM:";FRE(0);">"'] \
            + [f'{c}$="1"' for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"] \
            + ['PRINT"<END>"']
    txt = run(lines)
    dimok = "DIM:" in txt and "Out of memory" not in txt.split("<DIM:")[0][-200:] if "<DIM:" in txt else False
    ooms = txt.count("Out of memory")
    # was Z$ (last) OOM? check tail after last Z$="1"
    print(f"N={N}: OOM_count={ooms}  hasDIMmark={'<DIM:' in txt}", flush=True)
