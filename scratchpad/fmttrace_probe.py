#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DOSFORMAT: which of OUR disk-ROM entries MSX-DOS's `format` calls (ours only:
our own ROM may be traced; the reference's never is). Boots the DOS disk copy,
answers the date, types `format` at T_FMT, and logs each hit of a published entry
($4010..$4025) or a `k_XXXX` canonical entry, while the PC is in slot 3-1 (the disk
ROM: under MSX-DOS page 1 is TPA RAM, so an address alone would also catch RAM).

    python3 scratchpad/fmttrace_probe.py --disk DOSDISK [--settle 40]
"""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
from omsx_session import OmsxRun, OURS_MACHINE  # noqa: E402
import probe_tmp  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--disk", required=True)
ap.add_argument("--settle", type=float, default=40.0)
ap.add_argument("--fmt-at", type=float, default=24.0)
a = ap.parse_args()
entries = {0x4010 + 3 * i: f"${0x4010 + 3 * i:04X}" for i in range(6)}
for line in open(os.path.join(REPO, "build", "disk.sym")):
    p = line.split()
    if len(p) >= 3 and p[0].startswith("k_") and p[1] == "EQU":
        entries[int(p[2].rstrip("H"), 16)] = p[0]
work = probe_tmp.tmp("fmttrace")
os.makedirs(work, exist_ok=True)
dsk = os.path.join(work, "dos.dsk")
shutil.copyfile(a.disk, dsk)
arm = f'set ::armed 0\nafter time {a.fmt_at - 0.5:.4f} {{ set ::armed 1 }}\n'
arm += 'after time 21 { type "\\r" }\n'
arm += f'after time {a.fmt_at:.4f} {{ type "format\\r" }}\n'
for ad, name in entries.items():
    arm += (f'debug set_bp {ad:#06x} {{[pc_in_slot 3 1]}} {{ if {{$::armed}} '
            f'{{ emit "HIT {name} [format %.4f [machine_info time]] '
            f'SP=[format %04X [reg SP]] A=[format %02X [reg A]] C=[format %02X [reg C]]" }} }}\n')
# ...and every READ of our ROM's header / entry area, by whom (D-DOSFORMAT: no entry
# was called -- does COMMAND.COM judge from bytes it reads, through RDSLT?)
arm += ('debug set_watchpoint read_mem {0x4000 0x407F} {[watch_in_slot 3 1]} '
        '{ if {$::armed} { emit "READ [format %04X $::wp_last_address] '
        'PC=[format %04X [reg PC]] [format %.4f [machine_info time]]" } }\n')
run = OmsxRun(machine=OURS_MACHINE, diska=dsk, allow_disasm=False)
lines = run.run_job_raw('emit "END"; exit', settle=a.settle, arm=arm, timeout=a.settle * 4 + 120)
seen = []
for ln in lines:
    if ln.startswith(("HIT ", "READ ")):
        print(ln)
print("END" if any(l.startswith("END") for l in lines) else "\n".join(lines[-5:]))
