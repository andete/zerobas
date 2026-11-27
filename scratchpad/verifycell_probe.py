#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-CLAIM473: which byte of the disk work area (read $8000-$F37F, RAM under MSX-DOS) holds VERIFY on a machine? Boots MSX-DOS to A>,
snapshots the area, types VERIFY ON, snapshots, VERIFY OFF, snapshots; prints the bytes that follow the switch
(changed by ON and back by OFF). RAM only -- no PC, no ROM byte.
    python3 -u scratchpad/verifycell_probe.py [MACHINE ...]
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_preflight  # noqa: E402

for m in sys.argv[1:] or ["National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"]:
    td = tempfile.mkdtemp()
    dsk = os.path.join(td, "d.dsk")
    subprocess.run(["cp", os.path.expanduser("~/Documents/msx/msx/disks/test.dsk"), dsk], check=True)
    log = os.path.join(td, "o.txt")
    tcl = "\n".join([
        "set throttle off",
        f"set f [open {{{log}}} w]",
        "proc snap {t} { global f; binary scan [debug read_block memory 0x8000 [expr {0xF380-0x8000}]] H* h; puts $f \"$t $h\"; flush $f }",
        "after time 18 { type \"\\r\" }",          # the date prompt (both machines are there well before 18 s)
        "after time 24 { snap OFF0 }",
        "after time 25 { type \"VERIFY ON\\r\" }",
        "after time 30 { snap ON }",
        "after time 31 { type \"VERIFY OFF\\r\" }",
        "after time 36 { snap OFF1; exit }", ""])
    sf = os.path.join(td, "s.tcl")
    open(sf, "w").write(tcl)
    subprocess.run(omsx_preflight.guarded(["openmsx", "-machine", m, "-diska", dsk, "-command",
                   "set renderer none; set sound_driver null", "-script", sf]),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
    s = {}
    for ln in open(log).read().splitlines():
        t, h = ln.split()
        s[t] = bytes.fromhex(h)
    hits = [i for i in range(len(s["ON"])) if s["OFF0"][i] != s["ON"][i] and s["OFF1"][i] == s["OFF0"][i]]
    print(f"{m:28s} bytes that follow VERIFY: " + (", ".join(
        f"${0x8000 + i:04X} ({s['OFF0'][i]:02X} -> {s['ON'][i]:02X} -> {s['OFF1'][i]:02X})" for i in hits) or "-"))
