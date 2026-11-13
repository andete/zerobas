#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ROBOREG: is the CPU stuck in the interrupt path? Per 0.5 s sample, both machines:
$0038 entries (the IRQ), $FD9A entries (H.KEYI), port $99 reads (the VDP status, the
acknowledge), and the PC / CURLIN -- each counter reset after the sample. Black-box: a PC
breakpoint at the published IRQ vector and the published hook, an I/O read watch.

    DISKCORPUS_DIR=... python3 -u scratchpad/roboirq_probe.py IMAGE [END]
"""
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import diskcorpus_run as D  # noqa: E402


def run(machine, image, end):
    td = tempfile.mkdtemp(prefix="roboirq_")
    dsk = os.path.join(td, "d.dsk")
    shutil.copy(image, dsk)
    out = os.path.join(td, "o.txt")
    tcl = ["set throttle off", "set ::n38 0", "set ::nki 0", "set ::n99 0",
           "debug set_bp 0x0038 {} {incr ::n38}",
           "debug set_bp 0xFD9A {} {incr ::nki}",
           "debug set_watchpoint read_io 0x99 {} {incr ::n99}",
           # who writes the H.KEYI hook: PC, SP, the stack's top two words, CURLIN, the value
           f"set ::wf [open {{{os.path.join('WFDIR', 'w.txt')}}} w]",
           # the first instruction run with SP in the hook area (once: the condition removes itself)
           "proc __rd16 {a} { binary scan [debug read_block memory $a 2] s v; return [expr {$v & 0xFFFF}] }",
           "set ::spc [debug set_condition {[reg sp] >= 0xFF00 || [reg sp] < 0x0100} {binary scan [debug read_block memory [reg sp] 8] H* st; "
           "binary scan [debug read_block memory 0xF41C 2] s cl; "
           "puts $::wf \"[format %.4f [machine_info time]] SP pc=[format %04X [reg pc]] sp=[format %04X [reg sp]] st=$st cl=[expr {$cl & 0xFFFF}] hl=[format %04X [reg hl]] de=[format %04X [reg de]] savstk=[format %04X [__rd16 0xF6B1]]\"; flush $::wf; debug remove_condition $::spc}]",
           # the error abort's entry (our own fre_abort_low, $3BDA on HEAD): who raised it
           "debug set_bp 0x3BDA {[pc_in_slot 0]} {binary scan [debug read_block memory [reg sp] 24] H* st; "
           "puts $::wf \"[format %.4f [machine_info time]] AB sp=[format %04X [reg sp]] hl=[format %04X [reg hl]] a=[format %02X [reg a]] st=$st cl=[__rd16 0xF41C] savstk=[format %04X [__rd16 0xF6B1]]\"; flush $::wf}",
           # every CALSLT ($001C) and CALLF ($0030) before the crash: target IX / slot IY / caller
           "debug set_bp 0x001C {[pc_in_slot 0] && [machine_info time] > 3.0} {puts $::wf \"[format %.4f [machine_info time]] CS ix=[format %04X [reg ix]] iy=[format %04X [reg iy]] ret=[format %04X [__rd16 [reg sp]]]\"; flush $::wf}",
           # the disk-ROM address the game calls ($5C11): who, with what registers
           "debug set_bp 0x5C11 {[machine_info time] > 3.0} {binary scan [debug read_block memory [reg sp] 8] H* st; puts $::wf \"[format %.4f [machine_info time]] K5 af=[format %04X [reg af]] bc=[format %04X [reg bc]] de=[format %04X [reg de]] hl=[format %04X [reg hl]] ix=[format %04X [reg ix]] iy=[format %04X [reg iy]] sp=[format %04X [reg sp]] st=$st\"; flush $::wf}",
           # every SAVSTK write ($F6B1, the run loop's SP anchor): when, from where, CURLIN
           "debug set_watchpoint write_mem 0xF6B1 {} {puts $::wf \"[format %.4f [machine_info time]] SV pc=[format %04X [reg pc]] sp=[format %04X [reg sp]] v=[format %02X $::wp_last_value] cl=[__rd16 0xF41C]\"; flush $::wf}",
           "debug set_watchpoint write_mem 0xFD9A {} {binary scan [debug read_block memory [reg sp] 4] H* st; "
           "puts $::wf \"[format %.4f [machine_info time]] W pc=[format %04X [reg pc]] sp=[format %04X [reg sp]] st=$st v=[format %02X $::wp_last_value] hl=[format %04X [reg hl]] de=[format %04X [reg de]] bc=[format %04X [reg bc]]\"; flush $::wf}",
           "proc __s {t} {",
           f"  set f [open {{{out}}} a]",
           "  binary scan [debug read_block memory 0xF41C 2] s cl",
           "  binary scan [debug read_block memory 0xFD9A 5] H* hk",
           "  puts $f \"$t [format %04X [reg pc]] [expr {$cl & 0xFFFF}] $::n38 $::nki $::n99 hk=$hk sp=[format %04X [reg sp]]\"",
           "  close $f; set ::n38 0; set ::nki 0; set ::n99 0",
           "}"]
    t = 0.5
    while t <= end:
        tcl.append(f"after time {t} {{ __s {t} }}")
        t += 0.5
    tcl.append(f"after time {end + 0.3} {{ exit }}")
    open(os.path.join(td, "s.tcl"), "w").write("\n".join(tcl).replace("WFDIR", td) + "\n")
    subprocess.run([D.OMSX, "-machine", machine, "-diska", dsk, "-command",
                    "set renderer none; set sound_driver null", "-script", os.path.join(td, "s.tcl")],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60 + end * 3)
    rows = open(out).read().splitlines() if os.path.exists(out) else []
    wf = os.path.join(td, "w.txt")
    rows += open(wf).read().splitlines()[:80] if os.path.exists(wf) else []
    shutil.rmtree(td, ignore_errors=True)
    return rows


def main():
    img = os.path.join(os.environ["DISKCORPUS_DIR"], sys.argv[1])
    end = float(sys.argv[2]) if len(sys.argv) > 2 else 14.0
    for side, mach in (("REF", D.REF), ("ZB", D.ZB)):
        for r in run(mach, img, end):
            print(side, r, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
