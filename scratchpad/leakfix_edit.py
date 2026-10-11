#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Remove the four session-path leaks session-path-check found (2026-10-11),
point two stale machine names at today's machines, and wire the gate.
Anchored on text; refuses on a missing or non-unique anchor."""
import sys

SESSION = "/" + "private/tmp/" + "claude-501/-Users-joost-projects-zerobas/"
NOTES = "../../." + "claude/" + "projects/-Users-joost-projects-zerobas/memory/"

EDITS = [
    ("scratchpad/anchor_audit.py",
     "json.dump(rows, open('/" + "tmp/" + "claude-501/-Users-joost-projects-zerobas/"
     "caf279e5-e405-446f-b919-bce8acf752f8/scratchpad/anchor_rows.json','w'))",
     "json.dump(rows, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"
     " 'anchor_rows.json'), 'w'))  # was a session temp path (session-path-check)"),
    ("scratchpad/anchor_audit.py",
     "import re, subprocess, json, sys\n",
     "import os, re, subprocess, json, sys\n"),
    ("scratchpad/twofile_orig.out",
     SESSION + "7a73d35b-d2cc-4d27-94b6-763e774091f8/scratchpad/orig.py:18:",
     "<session scratchpad>/orig.py:18:"),
    ("docs/chancost-cf3300-characterization.md",
     "measurement ([`arrdim-c-slice`](" + NOTES + "arrdim-c-slice.md)).",
     "measurement (the maintainer's working note `arrdim-c-slice`, not in the repo)."),
    ("docs/spec-basic-arrays-slice4b-scalar-reloc.md",
     "([`charter-faithful-full-msx1-basic`](" + NOTES + "charter-faithful-full-msx1-basic.md)).",
     "(the maintainer's working note `charter-faithful-full-msx1-basic`, not in the repo;\n"
     "[MISSION.md](../MISSION.md) states the charter)."),
    ("probes/disk/disk_probe_lstout_cbios.py",
     "--machine C-BIOS_MSX1_JP_BASIC_DISK",
     "--machine C-BIOS_MSX1_EU_BASIC_DISK"),
    ("scratchpad/nodisk_probe.py",
     '    "zb-nodisk": ("ZB_REPACK_NODISK", 8.0, ("NEW",)),',
     '    "zb-nodisk": ("C-BIOS_MSX1_EU_REPACK_NODISK", 8.0, ("NEW",)),'),
    ("scratchpad/nodisk_probe.py",
     "This probe boots `ZB_REPACK_NODISK` --",
     "This probe boots `C-BIOS_MSX1_EU_REPACK_NODISK` (2026-10-11; it was the\n"
     "retired `ZB_REPACK_NODISK`) --"),
    ("Makefile",
     "hostkill-check:\n",
     "# --- session-path-check: no tracked file points into an assistant session's\n"
     "# private space -- zerobas is PUBLIC; four such paths were found 2026-10-11.\n"
     "session-path-check:\n"
     "\tpython3 tools/check_session_paths.py --selftest\n"
     "\tpython3 tools/check_session_paths.py\n"
     "\n"
     "hostkill-check:\n"),
    ("tools/run_gates.py",
     "dead-alias-check alias-order-check hostkill-check\n",
     "dead-alias-check alias-order-check hostkill-check session-path-check\n"),
]

texts = {}
for path, old, new in EDITS:
    s = texts.get(path) or open(path, encoding="utf-8").read()
    n = s.count(old)
    if n != 1:
        sys.exit(f"REFUSED: {path}: anchor count {n}: {old[:70]!r}")
    texts[path] = s.replace(old, new)
for path, s in texts.items():
    open(path, "w", encoding="utf-8").write(s)
    print("edited", path)
