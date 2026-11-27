#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""How long a COPY at MSX-DOS's A> takes, in emulated seconds, on each machine. It drives the session with
disk_probe_dossession's own Tcl (boot, the date prompt, MODE 40 -- the driver the gate trusts), with its snapshots
stamped by machine time and the per-row wait raised for a long copy. Screen / RAM only.
    python3 -u scratchpad/copytime_probe.py SRC [MACHINE ...]
(The first version typed into the date prompt at a fixed time and waited forever on the CF-3300; its own prompt
detector then saw nothing on either machine -- 2026-11-27. Reusing the gated driver instead.)
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "disk"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import disk_probe_dossession as D  # noqa: E402
import omsx_preflight  # noqa: E402

src = sys.argv[1]
machines = sys.argv[2:] or ["National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"]
D.SESSION = [("boot", None, 14), ("date", "", 5), ("mode", "MODE 40", 4), ("copy", f"COPY {src} BIG.ROM", 1)]
for m in machines:
    td = tempfile.mkdtemp()
    dsk = os.path.join(td, "d.dsk")
    subprocess.run(["cp", os.path.expanduser("~/Documents/msx/msx/disks/test.dsk"), dsk], check=True)
    out = os.path.join(td, "o.txt")
    tcl = D.tcl(out)
    for a, b in (('puts $f "$tag W=$w', 'puts $f "$tag T=[format %.2f [machine_info time]] W=$w'),
                 ("$::tries > 240", "$::tries > 12000")):
        assert tcl.count(a) == 1, a
        tcl = tcl.replace(a, b)
    sf = os.path.join(td, "s.tcl")
    open(sf, "w").write(tcl)
    subprocess.run(omsx_preflight.guarded(["openmsx", "-machine", m, "-diska", dsk, "-command",
                                           "set renderer none; set sound_driver null", "-script", sf]),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2400)
    t = {}
    for ln in (open(out).read().splitlines() if os.path.exists(out) else []):
        p = ln.split()
        if len(p) > 1 and p[1].startswith("T="):
            t[p[0]] = float(p[1][2:])
    took = f"{t['copy'] - t['mode']:.1f} s" if "copy" in t and "mode" in t else f"NO READING {sorted(t)}"
    big = [e for e in D.disk_listing(bytearray(open(dsk, "rb").read())) if e.startswith(("BIG.", src))]
    print(f"{m:36s} COPY {src}: {took}   " + " | ".join(big))
