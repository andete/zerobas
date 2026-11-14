#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LOOPPROF / Joost 2026-11-14 ("investigate what the references do ?"): what a `FOR I%`
loop keeps on the reference's stack. Black box, RAM only: while `FOR I%=1 TO 32000:NEXT`
runs, read the published STKTOP ($F674) and VARTAB ($F6C2) cells, the 64 bytes just
below STKTOP (the BASIC stack grows down from there), the CPU's SP, and the variable
table's first 16 bytes (I%'s entry) -- twice, ~1 s apart, so fields that move (none in a
frame that holds a POINTER to the variable) separate from fields that stay. No ROM byte
is read; only RAM through the emulator's debugger.

    python3 -u scratchpad/forframe_probe.py [machine ...]
"""
import os, subprocess, sys, tempfile, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_preflight  # noqa: E402

OPENMSX = shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
PROG = "10 FOR I%=1 TO 32000:NEXT\\r"
TCL = r"""
set throttle off
proc rw {a} { return [expr {[peek $a] + 256*[peek [expr {$a+1}]]}] }
proc dump {f tag} {
  set st [rw 0xF674]
  set vt [rw 0xF6C2]
  binary scan [debug read_block memory [expr {$st-64}] 64] H* s
  binary scan [debug read_block memory $vt 16] H* v
  puts $f "$tag sp=[format %04X [reg sp]] stktop=[format %04X $st] vartab=[format %04X $vt]"
  puts $f "  stack\[stktop-64..stktop\): $s"
  puts $f "  vars\[vartab..+16\): $v"
}
after time T0 { type "PROG" }
after time T1 { type "RUN\r" }
after time T2 { set f [open {OUT} w]; dump $f A; after time T3 [list dumpb $f] }
proc dumpb {f} { dump $f B; close $f; exit }
"""


def run(machine):
    td = tempfile.mkdtemp(prefix="forframe_")
    try:
        out = os.path.join(td, "o.txt")
        tcl = os.path.join(td, "s.tcl")
        t0 = float(os.environ.get("FORFRAME_T0", "8"))   # the disk machines boot longer: 25
        t = {"T0": t0, "T1": t0 + 1, "T2": t0 + 3, "T3": t0 + 4}
        body = TCL.replace("PROG", PROG).replace("OUT", out)
        for k, v in t.items():
            body = body.replace(k, str(v))
        open(tcl, "w").write(body)
        subprocess.run(omsx_preflight.guarded([OPENMSX, "-machine", machine, "-command",
                       "set renderer none; set sound_driver null", "-script", tcl]),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
        return open(out).read() if os.path.exists(out) else "<no output>\n"
    finally:
        shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    for m in sys.argv[1:] or ["Philips_VG_8020", "National_CF-3300"]:
        print(f"=== {m}")
        print(run(m), end="", flush=True)
