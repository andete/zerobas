#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Re-measure the real CF-3300's `FILES` listing at WIDTH 29.

disk_probe_files.py carries that listing as a FROZEN CONSTANT, and its own
comment records the procedure: boot the CF-3300, CLEAR THE DATE PROMPT FIRST,
WIDTH 29, FILES. Its `run()` entry point does NOT answer that prompt, so the
constant cannot be refreshed through the probe itself -- this does it with the
reset the kwsweep already uses for that machine (an empty first line answers the
date prompt, then SCREEN 0).

Run it when `disk/test720.dsk` legitimately changes. It was written when
`PROG3.BAS` joined the image (D-KWRUNFILE, 2026-09-15) and the constant had to
move from five files to six -- MEASURED, not predicted from the wrap width.
"""
import sys, os, shutil, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl
DSK = os.path.join(REPO, "disk", "test720.dsk")
fh = tempfile.NamedTemporaryFile(suffix=".dsk", delete=False); fh.close()
shutil.copy(DSK, fh.name)
raws = omsx_repl.run_cases("National_CF-3300", [("stored", ["WIDTH 29", "FILES"])],
                           batch=False, boot=14.0,
                           reset=("", "SCREEN 0", "CLS"), diska=fh.name,
                           step=5.0, cap_gap=20.0, timeout=600.0)
s = "".join(raws[0] or "")
for r in range(0, len(s), 40):
    line = s[r:r+40].rstrip()
    if line: print("%2d |%s|" % (r//40, line))
os.unlink(fh.name)
