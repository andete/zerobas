#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DISKRUN mb.dsk, before the $5E10 pin (Joost ruled 2026-10-27: "Start BASIC (NMS
1200)"): what does the screen show over time when mb.dsk boots -- does the NMS 1200
ask the date before AUTOEXEC.BAS runs? On the VG-8020 + Philips NMS 1200, the
National CF-3300 and zerobas. Each run boots a fresh temp copy of the collection's
mb.dsk (DISKCORPUS_DIR; its location is never written here) and captures the screen
at fixed emulated times, typing nothing. Black box: the screen and CURLIN out.
    DISKCORPUS_DIR=... python3 -u scratchpad/mbtime_probe.py [eu,jp,zb]
"""
import os, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_preflight  # noqa: E402
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diskcorpus_run as D  # noqa: E402

MACHINES = {"eu": ("Philips_VG_8020", ["-ext", "Philips_NMS_1200"]),
            "jp": ("National_CF-3300", []),
            "zb": ("C-BIOS_MSX1_EU_REPACK_DISK", [])}
TIMES = [6, 9, 12, 16, 22, 30]


def run(key):
    machine, extra = MACHINES[key]
    td = tempfile.mkdtemp(prefix="mbtime_")
    dsk = os.path.join(td, "m.dsk")
    shutil.copy(os.path.join(os.environ["DISKCORPUS_DIR"], "mb.dsk"), dsk)
    out = os.path.join(td, "c.txt")
    tcl = ["set throttle off", "proc __cap {tag} {", f"  set f [open {{{out}}} a]",
           "  binary scan [debug read_block VRAM 0 16384] H* v",
           "  set r {}", "  for {set i 0} {$i < 8} {incr i} { lappend r [vdpreg $i] }",
           "  binary scan [debug read_block memory 0xF41C 2] H* cl",
           '  puts $f "$tag [reg pc] $r $cl $v"', "  close $f", "}"]
    tcl += [f"after time {t} {{ __cap T{t} }}" for t in TIMES]
    tcl.append(f"after time {TIMES[-1] + 0.5} {{ exit }}")
    open(os.path.join(td, "s.tcl"), "w").write("\n".join(tcl) + "\n")
    subprocess.run(omsx_preflight.guarded(["/opt/homebrew/bin/openmsx", "-machine", machine] + extra +
                   ["-diska", dsk, "-command", "set renderer none; set sound_driver null",
                    "-script", os.path.join(td, "s.tcl")]),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=150)
    caps = {}
    if os.path.exists(out):
        for ln in open(out):
            p = ln.split()
            caps[p[0]] = {"pc": int(p[1]), "regs": [int(x) for x in p[2:10]],
                          "curlin": int(p[10][2:4] + p[10][0:2], 16), "vram": bytes.fromhex(p[11])}
    shutil.rmtree(td, ignore_errors=True)
    return caps


def main():
    for k in (sys.argv[1] if len(sys.argv) > 1 else "eu,jp,zb").split(","):
        caps = run(k)
        for t in TIMES:
            c = caps.get(f"T{t}")
            txt = " / ".join(x for x in D.screen_text(c) if x.strip())[-200:] if c else "<none>"
            print(f"{k} T{t:<3} pc={c['pc']:04X} curlin={c['curlin']:04X}  {txt}" if c else f"{k} T{t} <none>", flush=True)


if __name__ == "__main__":
    main()
