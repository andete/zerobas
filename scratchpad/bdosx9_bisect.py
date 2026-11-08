#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Bisect bdosx9.asm: run it cut short before record K (a `jp done` planted in
front of `; --- record K` or, for K = 'unused', in front of the unused-number loop),
OURS only, and print the registers at `done` plus the first records.

    python3 -u scratchpad/bdosx9_bisect.py K [K ...]
"""
import os, re, subprocess, sys, shutil
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
import build_bdosx9_disk as B          # noqa: E402

SRC = open(os.path.join(REPO, "probes", "disk", "bdosx9.asm")).read()
TMP = "/tmp/zerobas"
os.makedirs(TMP, exist_ok=True)

for k in sys.argv[1:]:
    mark = "; --- records 11-17" if k == "unused" else f"; --- record {k}:"
    if SRC.count(mark) != 1:
        sys.exit(f"anchor {mark!r} not found exactly once")
    cut = SRC.replace(mark, "jp done\n                " + mark)
    asm = os.path.join(TMP, f"bdosx9_cut{k}.asm")
    open(asm, "w").write(cut)
    B.ASM = asm
    dsk = os.path.join(TMP, f"bdosx9_cut{k}.dsk")
    done, sig = B.build(os.path.expanduser("~/Documents/msx/msx/disks/test.dsk"), dsk, TMP)
    cmd = ["python3", "-u", os.path.join(REPO, "probes", "disk", "disk_probe_diff.py"),
           "capture", "--at", hex(done), "--arm-check-val", hex(sig), "--settle", "50",
           "--machine", "both", "--mem", "0x0400:0x60", "--diska", dsk]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    print(f"===== cut before record {k}")
    for line in out.splitlines():
        if re.match(r"\s*(>>)?(PC|SP|AF|BC|DE|HL)\s", line) or "differ" in line or "ALIGNED" in line \
                or "TIMEOUT" in line.upper() or re.match(r"\s+04[0-5][0-9A-F]:", line):
            print(line)
    sys.stdout.flush()
