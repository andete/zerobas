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


def _sym(n):
    return int([l.split()[2] for l in open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build", "basic-reloc.sym"))
                if l.split()[:1] == [n]][0].rstrip("Hh"), 16)


USRCALL = int([l.split()[2] for l in open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build", "basic-reloc.sym"))
                if l.split()[:1] == ["usr_call"]][0].rstrip("Hh"), 16)


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
           "debug set_bp 0x001C {[pc_in_slot 0] && [machine_info time] > 3.0} {binary scan [debug read_block memory [reg sp] 24] H* st; puts $::wf \"[format %.4f [machine_info time]] CS ix=[format %04X [reg ix]] iy=[format %04X [reg iy]] ret=[format %04X [__rd16 [reg sp]]] st=$st\"; flush $::wf}",
           # the disk-ROM address the game calls ($5C11): who, with what registers
           "debug set_bp 0x5C11 {[machine_info time] > 3.0} {binary scan [debug read_block memory [reg sp] 8] H* st; puts $::wf \"[format %.4f [machine_info time]] K5 af=[format %04X [reg af]] bc=[format %04X [reg bc]] de=[format %04X [reg de]] hl=[format %04X [reg hl]] ix=[format %04X [reg ix]] iy=[format %04X [reg iy]] sp=[format %04X [reg sp]] st=$st\"; flush $::wf}",
           # the reference's RUN-without-argument ($73AC, our basicint_run): the program state handed over
           "debug set_bp 0x73AC {[pc_in_slot 0] && [machine_info time] > 3.0} {set ::pd 1; binary scan [debug read_block memory [reg sp] 8] H* st; puts $::wf \"[format %.4f [machine_info time]] RN txttab=[format %04X [__rd16 0xF676]] vartab=[format %04X [__rd16 0xF6C2]] arytab=[format %04X [__rd16 0xF6C4]] hl=[format %04X [reg hl]] sp=[format %04X [reg sp]] st=$st first=[format %04X [__rd16 [__rd16 0xF676]]]\"; flush $::wf}",
           # after basicint_run: does run_prog_top run, and when / from where does the reboot ($0000) come
           "debug set_bp 0x6554 {[pc_in_slot 0] && [machine_info time] > 3.0} {binary scan [debug read_block memory 0xFBE5 11] H* nk; binary scan [debug read_block memory 0xFBDA 11] H* ok; puts $::wf \"[format %.4f [machine_info time]] RPT sp=[format %04X [reg sp]] newkey=$nk oldkey=$ok\"; flush $::wf}",
           "debug set_bp 0x73B7 {[pc_in_slot 0] && [machine_info time] > 3.0} {puts $::wf \"[format %.4f [machine_info time]] RELINKED hl=[format %04X [reg hl]]\"; flush $::wf}",
           "debug set_bp 0x0000 {[machine_info time] > 3.0} {binary scan [debug read_block memory [reg sp] 16] H* st; puts $::wf \"[format %.4f [machine_info time]] RST0 sp=[format %04X [reg sp]] st=$st\"; flush $::wf}",
           # the keyboard rows when CURLIN first reads 5 (line 5's CONTROL check)
           "set ::l5 0", "set ::nl 0", "set ::lastcl -1",
           # the program area right after the RUN entry returned to the run loop (CF: line 5's first CURLIN
           # write; ZB: the first CURLIN write after RN) -- dumped for a byte comparison only
           "set ::pd 0",
           "debug set_watchpoint write_mem 0xF41D {} {if {$::pd == 1} {set ::pd 2; binary scan [debug read_block memory 0x8001 0x680] H* pg; set g [open {PDUMP} w]; puts $g $pg; close $g}}",
           # every CURLIN value change after 3 s (the line sequence), up to 60
           "debug set_watchpoint write_mem 0xF41D {} {if {[machine_info time] > 3.0 && $::nl < 60} {set c [__rd16 0xF41C]; if {$c != $::lastcl} {set ::lastcl $c; incr ::nl; binary scan [debug read_block memory 0xF39A 4] H* ut; puts $::wf \"[format %.4f [machine_info time]] CL $c usrtab=$ut\"; flush $::wf}}}",
           "debug set_watchpoint write_mem 0xF41C {} {if {$::l5 == 0 && $::wp_last_value == 5} {set ::l5 1; binary scan [debug read_block memory 0xFBE5 11] H* nk; puts $::wf \"[format %.4f [machine_info time]] L5 newkey=$nk\"; flush $::wf}}",
           # every SAVSTK write ($F6B1, the run loop's SP anchor): when, from where, CURLIN
           "set ::nw 0",
           "debug set_bp 0x1AA3 {[pc_in_slot 0] && [machine_info time] > 3.0 && $::nw < 30} {binary scan [debug read_block memory [reg sp] 24] H* st; puts $::wf \"[format %.4f [machine_info time]] CK sp=[format %04X [reg sp]] hl=[format %04X [reg hl]] de=[format %04X [reg de]] bc=[format %04X [reg bc]] af=[format %04X [reg af]] ix=[format %04X [reg ix]] iy=[format %04X [reg iy]] st=$st\"; flush $::wf}",
           "set ::tr 0",
           "set ::pf 1",
           "set ::ring {}",
           "set ::rd 0",
           "set ::nu 0",
           "set ::nd 0",
           "set ::pr 0",
           "set ::ntr 0",
           "set ::pk [dict create]",
           "after time 4.0 {binary scan [debug read_block memory 0xFB21 12] H* d; puts $::wf \"4.0000 DRVINF $d\"; flush $::wf}",
           "after time 12.0 {binary scan [debug read_block memory 0xFB21 12] H* d; puts $::wf \"12.0000 DRVINF $d\"; flush $::wf}",
           "debug set_bp PEEKRD {[pc_in_slot 0] && [string match C-BIOS* {MACH}] && [machine_info time] > 3.0} {set k [format %04X [reg hl]]; if {![dict exists $::pk $k] && [dict size $::pk] < 40} {dict set ::pk $k 1; puts $::wf \"[format %.4f [machine_info time]] PEEK a=$k v=[format %02X [debug read memory [reg hl]]] cl=[__rd16 0xF41C]\"; flush $::wf}}",
           "after time 7.0 {binary scan [debug read_block memory [reg sp] 64] H* st; puts $::wf \"7.0000 STK pc=[format %04X [reg pc]] sp=[format %04X [reg sp]] a8=[format %02X [debug read ioports 0xA8]] st=$st\"; flush $::wf}",
           "debug set_bp 0x4010 {$::nd < 80} {incr ::nd; binary scan [debug read_block memory [reg sp] 6] H* st; puts $::wf \"[format %.4f [machine_info time]] DSKIO af=[format %04X [reg af]] bc=[format %04X [reg bc]] de=[format %04X [reg de]] hl=[format %04X [reg hl]] sp=[format %04X [reg sp]] a8=[format %02X [debug read ioports 0xA8]] st=$st\"; flush $::wf}",
           "debug set_bp 0x0144 {$::nd < 80} {incr ::nd; binary scan [debug read_block memory [reg sp] 6] H* st; puts $::wf \"[format %.4f [machine_info time]] PHYDIO af=[format %04X [reg af]] bc=[format %04X [reg bc]] de=[format %04X [reg de]] hl=[format %04X [reg hl]] sp=[format %04X [reg sp]] a8=[format %02X [debug read ioports 0xA8]] st=$st\"; flush $::wf}",
           "debug set_bp 0x4257 {$::nd < 80 && [string match C-BIOS* {MACH}]} {incr ::nd; binary scan [debug read_block memory [reg sp] 6] H* st; puts $::wf \"[format %.4f [machine_info time]] ZDSKIO af=[format %04X [reg af]] bc=[format %04X [reg bc]] de=[format %04X [reg de]] hl=[format %04X [reg hl]] sp=[format %04X [reg sp]] a8=[format %02X [debug read ioports 0xA8]] st=$st\"; flush $::wf}",
           "debug set_bp USRCALL {[pc_in_slot 0] && [string match C-BIOS* {MACH}] && [machine_info time] > 5.0 && $::nu < 30} {incr ::nu; binary scan [debug read_block memory 0xF39A 20] H* ut; binary scan [debug read_block memory [reg sp] 8] H* st; puts $::wf \"[format %.4f [machine_info time]] USR cl=[__rd16 0xF41C] af=[format %04X [reg af]] hl=[format %04X [reg hl]] de=[format %04X [reg de]] usrtab=$ut st=$st\"; flush $::wf}",
           "debug set_bp 0xFFFF {[machine_info time] > 5.0} {binary scan [debug read_block memory [expr {[reg sp] - 8}] 24] H* st; puts $::wf \"[format %.6f [machine_info time]] PFFFF sp=[format %04X [reg sp]] hl=[format %04X [reg hl]] de=[format %04X [reg de]] bc=[format %04X [reg bc]] af=[format %04X [reg af]] ix=[format %04X [reg ix]] iy=[format %04X [reg iy]] a8=[format %02X [debug read ioports 0xA8]] ffff=[format %02X [debug read memory 0xFFFF]] st-8=$st\"; flush $::wf}",
           "debug set_condition {[machine_info time] > 5.1260 && $::rd == 0} {lappend ::ring [format %04X:%X:%04X [reg pc] [pc_in_slot 0] [reg sp]]; if {[llength $::ring] > 300} {set ::ring [lrange $::ring 100 end]}}",
           "debug set_watchpoint write_mem 0x8100 {} {if {$::nw < 40} {incr ::nw; if {$::rd == 0 && [machine_info time] > 5.13} {set ::rd 1; puts $::wf \"RING [join $::ring { }]\"}; puts $::wf \"[format %.4f [machine_info time]] W8 a=[format %04X $::wp_last_address] v=[format %02X $::wp_last_value] pc=[format %04X [reg pc]] sp=[format %04X [reg sp]] hl=[format %04X [reg hl]] de=[format %04X [reg de]] bc=[format %04X [reg bc]] a8=[format %02X [debug read ioports 0xA8]]\"; flush $::wf}}",
           "debug set_watchpoint write_mem 0x8200 {} {if {$::nw < 40} {incr ::nw; puts $::wf \"[format %.4f [machine_info time]] W8 a=[format %04X $::wp_last_address] v=[format %02X $::wp_last_value] pc=[format %04X [reg pc]] sp=[format %04X [reg sp]] hl=[format %04X [reg hl]] de=[format %04X [reg de]] bc=[format %04X [reg bc]] a8=[format %02X [debug read ioports 0xA8]]\"; flush $::wf}}",
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
    open(os.path.join(td, "s.tcl"), "w").write("\n".join(tcl).replace("WFDIR", td).replace("MACH", machine).replace("USRCALL", "0x%04X" % USRCALL).replace("PEEKRD", "0x%04X" % (_sym("ev_ff_posany") - 4)).replace("PDUMP", os.path.join(os.environ.get("PDUMP_DIR", td), machine[:6] + "_prog.hex")) + "\n")
    subprocess.run([D.OMSX, "-machine", machine, "-diska", dsk, "-command",
                    "set renderer none; set sound_driver null", "-script", os.path.join(td, "s.tcl")],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60 + end * 3)
    rows = open(out).read().splitlines() if os.path.exists(out) else []
    wf = os.path.join(td, "w.txt")
    rows += open(wf).read().splitlines()[:2000] if os.path.exists(wf) else []
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
