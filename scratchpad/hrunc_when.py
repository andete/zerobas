#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-NMSHOST host contract item 3: WHEN does BASIC call H.RUNC ($FECB)? The method of D-HSTKE (stke_when.out): after
boot, our OWN counting handler goes into RAM -- the hook becomes `jp $D210` and $D210 holds `push hl / ld hl,$D200 /
inc (hl) / pop hl / ret` -- then each action is typed and the count read back after it. Black box: our code, RAM,
typed keys; never a ROM byte. The cold start's own call cannot be counted this way (the handler goes in after it).

    python3 -u scratchpad/hrunc_when.py [MACHINE ...] > scratchpad/AE_hrunc_when.out 2>&1
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

MACHINES = sys.argv[1:] or ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"]
# (label, typed text); each runs after the previous one's count is read
ACTIONS = [
    ("direct PRINT", 'PRINT 1'),
    ("CLEAR", 'CLEAR'),
    ("CLEAR 300", 'CLEAR 300'),
    ("NEW", 'NEW'),
    ("typed line", '10 PRINT 2'),
    ("second line", '20 END'),
    ("RUN", 'RUN'),
    ("GOTO 10 (direct)", 'GOTO 10'),
    ("error (direct)", 'FOO'),
    ("MAXFILES=2", 'MAXFILES=2'),
    ("RUN after MAXFILES", 'RUN'),
]

TCL = r"""
set renderer none
set throttle off
set f [open $::env(LOGF) w]
proc arm {} {
  foreach {a v} {0xD200 0x00 0xD210 0xE5 0xD211 0x21 0xD212 0x00 0xD213 0xD2 0xD214 0x34 0xD215 0xE1 0xD216 0xC9} { poke $a $v }
  foreach {a v} {0xFECB 0xC3 0xFECC 0x10 0xFECD 0xD2 0xFECE 0xC9 0xFECF 0xC9} { poke $a $v }
}
set ::acts [list ACTS]
set ::i 0
proc hr_step {} { if {[catch hr_step_ {err}]} { puts $::f "TCLERR\t$err"; close $::f; exit } }
proc hr_step_ {} {
  if {$::i > 0} { puts $::f "[lindex $::acts [expr {2*($::i-1)}]]\t[peek 0xD200]" }
  if {$::i >= [expr {[llength $::acts]/2}]} { close $::f; exit }
  type "[lindex $::acts [expr {2*$::i+1}]]\r"
  incr ::i
  after time 2 hr_step
}
after time 12 { if {[catch {arm; puts $::f "armed\t[peek 0xD200]"} err]} { puts $::f "TCLERR\t$err"; close $::f; exit }; hr_step }
"""


def run(machine):
    acts = " ".join("{%s} {%s}" % (lbl, txt) for lbl, txt in ACTIONS)
    tcl = probe_tmp.tmp(f"hrunc_{machine}.tcl")
    open(tcl, "w").write(TCL.replace("ACTS", acts))
    os.makedirs("/tmp/zerobas/hrunc_keep", exist_ok=True)
    log = f"/tmp/zerobas/hrunc_keep/hrunc_{machine}.log"
    cmd = [openmsx_paths.find_openmsx_binary(), "-machine", machine, "-script", tcl]
    subprocess.run(omsx_preflight.guarded(cmd), env=dict(os.environ, LOGF=log), stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=180)
    print(f"### {machine}  (H.RUNC count after each typed action; cumulative)")
    prev = 0
    for ln in open(log):
        lbl, n = ln.rstrip("\n").split("\t")
        n = int(n)
        print(f"   {lbl:22s} {n:3d}   (+{n - prev})")
        prev = n


def main():
    for m in MACHINES:
        run(m)


if __name__ == "__main__":
    main()
