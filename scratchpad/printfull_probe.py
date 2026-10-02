# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DISKFULL's PRINT# face: PRINT# past one record on a disk with no free
cluster, on both machines. The CF-3300 stops with Disk full (ERR 66) at I=12 --
264 bytes, its first 256 B record flush. Ours HANGS: no [L], no prompt, even with
a 60 s run window."""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib")); sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl, probe_tmp                         # noqa: E402
import closefull_probe as C                         # noqa: E402
dsk = probe_tmp.tmp("pf_template.dsk")
shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
C.full_disk(dsk)
prog = ['OPEN"PF.TXT"FOR OUTPUT AS#1:PRINT"[O]"',
        'FOR I=1TO40:PRINT#1,STRING$(20,65):NEXT:PRINT"[L]"', 'PRINT"E=";ERR;I']
for tag, machine in (("CF-3300", "National_CF-3300"), ("OURS", "C-BIOS_MSX1_EU_REPACK_DISK")):
    d = probe_tmp.tmp(f"pf_{tag}.dsk")
    shutil.copyfile(dsk, d)
    raw = omsx_repl.run_cases(machine, [("direct", prog)], batch=False,
                              reset=("", "SCREEN 0"), boot=14.0, step=4.0, run_gap=60.0,
                              diska=d)[0] or ""
    print(f"== {tag}: " + re.sub(r"\s+", " ", raw)[-300:])
