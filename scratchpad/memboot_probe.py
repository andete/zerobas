#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-NMSHOST / memory parity: the published system DATA cells ($F39A-$FD99) after a plain power-on with NO cartridge,
at BASIC's Ok, on the VG-8020 and on zerobas NODISK -- the same SYSDATA line scratchpad/sysdata_diff.py reads.
Clean room: only $F39A-$FD99 (never the reference's RAM-resident code at $F380-$F399, never the hooks from $FD9A).

    python3 -u scratchpad/memboot_probe.py [SECONDS] -> /tmp/zerobas/memboot_keep/memboot_{ref,zb}.log
    python3 scratchpad/sysdata_diff.py /tmp/zerobas/memboot_keep/memboot_ref.log /tmp/zerobas/memboot_keep/memboot_zb.log
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_preflight  # noqa: E402
import probe_tmp  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "tools"))
import openmsx_paths  # noqa: E402

SECONDS = float(sys.argv[1]) if len(sys.argv) > 1 else 12.0
MACHINES = [("ref", "Philips_VG_8020"), ("zb", "C-BIOS_MSX1_EU_REPACK_NODISK")]
TCL = r"""
set renderer none
set throttle off
catch { set sound_driver null }
after time SECS {
  binary scan [debug read_block memory 0xF39A [expr {0xFD9A - 0xF39A}]] H* d
  set f [open $::env(LOGF) w]
  puts $f "SYSDATA $d"
  flush $f   ;# D-BOOTCELLS step 3: on zerobas get_screen below can hang; the data is out first
  puts $f "SCREEN [string map {"\n" " | "} [string trim [get_screen]]]"
  close $f
  exit
}
"""


def main():
    keep = "/tmp/zerobas/memboot_keep"
    os.makedirs(keep, exist_ok=True)
    tcl = probe_tmp.tmp("memboot.tcl")
    open(tcl, "w").write(TCL.replace("SECS", str(SECONDS)))
    for tag, machine in MACHINES:
        log = os.path.join(keep, f"memboot_{tag}.log")
        cmd = [openmsx_paths.find_openmsx_binary(), "-machine", machine, "-script", tcl]
        subprocess.run(omsx_preflight.guarded(cmd), env=dict(os.environ, LOGF=log), stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=180)
        scr = next((ln for ln in open(log) if ln.startswith("SCREEN")), "SCREEN ?").strip()
        print(f"{tag} {machine}: {scr[:150]}")


if __name__ == "__main__":
    main()
