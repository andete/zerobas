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
    # FDC command traffic (D-COPYSLOW): every write to the WD2793's command register (any of its mirrors in $7F80-$7FBF -- the National
    # decode repeats the 8 registers there -- memory-mapped in the interface's page 1 -- hardware traffic, no PC, no ROM byte), counted by command class while the copy runs
    fdc = os.path.join(td, "fdc.txt")
    tcl = tcl.replace("set throttle off", "set throttle off\nset ::fdc [dict create]\nset ::fdcsec [dict create]\nset ::counting 0\n"
        "debug set_watchpoint write_mem {0x7F80 0x7FBF} {$::counting} {if {($::wp_last_address & 7) == 0} {"
        "set c [expr {$::wp_last_value >> 4}]; dict incr ::fdc $c; "
        "dict incr ::fdcsec \"$c:[peek 0x7FB9]:[peek 0x7FBA]\"}}\n"
        "debug set_watchpoint write_mem {0xBF80 0xBFBF} {$::counting} {if {($::wp_last_address & 7) == 0} {"
        "set c [expr {$::wp_last_value >> 4}]; dict incr ::fdc [expr {$c + 100}]; "
        "dict incr ::fdcsec \"p2/$c:[peek 0xBFB9]:[peek 0xBFBA]\"}}", 1)
    # count from the MODE 40 step's snapshot to the COPY step's, which also writes the counts
    a = "  close $f }"
    assert tcl.count(a) == 1, "snap's close"
    tcl = tcl.replace(a, "  if {$tag eq \"mode\"} {set ::counting 1}\n"
                         "  if {$tag eq \"copy\"} {set ::counting 0; puts $f \"FDC $::fdc\"; puts $f \"FDCSEC $::fdcsec\"}\n" + a)
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
    fdcline = next((ln for ln in open(out).read().splitlines() if ln.startswith("FDC ")), "FDC -")
    names = {0: "restore", 1: "seek", 2: "step", 3: "step", 4: "stepin", 5: "stepin", 6: "stepout", 7: "stepout",
             8: "read", 9: "readM", 10: "write", 11: "writeM", 12: "readaddr", 13: "irq", 14: "readtrk", 15: "writetrk"}
    kv = fdcline.split()[1:]
    took += "  FDC " + " ".join(f"{names.get(int(kv[i]), kv[i])}={kv[i + 1]}" for i in range(0, len(kv) - 1, 2))
    big = [e for e in D.disk_listing(bytearray(open(dsk, "rb").read())) if e.startswith(("BIG.", src))]
    print(f"{m:36s} COPY {src}: {took}   " + " | ".join(big))
    sec = next((ln for ln in open(out).read().splitlines() if ln.startswith("FDCSEC ")), "FDCSEC")
    kv = sec.split()[1:]
    rows = sorted(((int(kv[i + 1]), kv[i]) for i in range(0, len(kv) - 1, 2)), reverse=True)
    if os.environ.get("FDCSEC"):
        sm = {}
        for n, k in rows:
            cmd, trk, sec = k.split(":")
            cls = cmd.split("/")[-1]
            kind = {"8": "read", "10": "write"}.get(cls)
            if not kind:
                continue
            where = ("FAT" if trk == "0" and 2 <= int(sec) <= 7 else "track0-other" if trk == "0" else "data")
            sm[(kind, where)] = sm.get((kind, where), 0) + n
        print("   by area (both mirrors): " + ", ".join(f"{k} {w}={v}" for (k, w), v in sorted(sm.items())))
