#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-NMSHOST: does the REFERENCE boot MSX-DOS at all, and with which disk interface? Runs a machine + one disk
interface extension + a private copy of a DOS disk, and reports the text screen (get_screen) at a few emulated times
and whether execution ever reached RAM $0100 (MSX-DOS's entry; a RAM breakpoint, hits in the first second ignored).
Black box: the screen and a RAM address; never a ROM byte.

    python3 -u scratchpad/dosref_probe.py MACHINE EXT DISK [SECONDS] > scratchpad/AE_dosref_<x>.out 2>&1
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_preflight  # noqa: E402
import probe_tmp  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "tools"))
import openmsx_paths  # noqa: E402

MACHINE, EXT, DISK = sys.argv[1:4]
SECONDS = float(sys.argv[4]) if len(sys.argv) > 4 else 40

TCL = r"""
set renderer none
set throttle off
catch { set sound_driver null }
set f [open $::env(LOGF) w]
set ::hits 0
debug set_bp 0x0100 {[machine_info time] > 1.0 && [lindex [get_selected_slot 0] 0] != 0} {
  incr ::hits; if {$::hits <= 3} { puts $::f "HIT0100 [format %.3f [machine_info time]] page0=[get_selected_slot 0] SCRMOD=[peek 0xFCAF] OLDSCR=[peek 0xFCB0] LINL40=[peek 0xF3AE] LINL32=[peek 0xF3AF] LINLEN=[peek 0xF3B0] CRTCNT=[peek 0xF3B1] CSRY=[peek 0xF3DC] CSRX=[peek 0xF3DD] R0=[vdpreg 0] R1=[vdpreg 1] R2=[vdpreg 2] R4=[vdpreg 4] R7=[vdpreg 7] HIMEM=[peek16 0xFC4A] CNSDFG=[peek 0xF3DE]" }
}
set ::hk 0
foreach {nm a} {RUNC 0xFECB STKE 0xFEDA} {
  debug set_bp $a {[machine_info time] > 1.0} "incr ::hk; if {\$::hk <= 12} { puts \$::f \"HOOK $nm \[format %.3f \[machine_info time\]\] SCRMOD=\[peek 0xFCAF\] LINLEN=\[peek 0xF3B0\] R1=\[vdpreg 1\] CSRY=\[peek 0xF3DC\]\" }"
}
if {[info exists ::env(DOSREF_ALLHOOKS)]} {
  array set ::hn {}
  for {set a 0xFD9A} {$a <= 0xFFC9} {incr a 5} {
    set ::hn($a) 0
    debug set_bp $a "\[machine_info time\] > $::env(DOSREF_ALLHOOKS)" "incr ::hn($a); if {\$::hn($a) <= 2} { puts \$::f \"ANYHOOK [format %04X $a] #\$::hn($a) \[format %.4f \[machine_info time\]\] SCRMOD=\[peek 0xFCAF\] LINLEN=\[peek 0xF3B0\] R1=\[vdpreg 1\]\" }"
  }
}
set ::r1 [vdpreg 1]
proc r1watch {} { if {[vdpreg 1] != $::r1} { set ::r1 [vdpreg 1]; if {[machine_info time] > 1.0} { puts $::f "R1CHANGE [format %.4f [machine_info time]] R1=$::r1 SCRMOD=[peek 0xFCAF]" } }; after time 0.001 r1watch }
r1watch
if {[info exists ::env(DOSREF_RET)]} {
  set ::retdone 0
  debug set_bp 0xFECB {[machine_info time] > $::env(DOSREF_RET) && !$::retdone} {
    set ::sp0 [reg sp]; set ::retdone 1
    puts $::f "RUNC_ENTER [format %.5f [machine_info time]] SP=[format %04X $::sp0] R1=[vdpreg 1]"
    set ::cid [debug set_condition {[reg sp] > $::sp0} {
      puts $::f "RUNC_RETURNED [format %.5f [machine_info time]] SP=[format %04X [reg sp]] R1=[vdpreg 1] SCRMOD=[peek 0xFCAF]"
      debug remove_condition $::cid
    }]
  }
}
# zerobas ONLY (never on a reference machine): entries from cartridge code into zerobas's own slot-0 ROM, by
# zerobas's own PC value, in a time window
if {[info exists ::env(DOSREF_ZBCALLS)]} {
  if {[string match "*Philips*" [machine_info config_name]]} { error "DOSREF_ZBCALLS is for zerobas only" }
  lassign $::env(DOSREF_ZBCALLS) ::w0 ::w1
  set ::prevcart 0; set ::ncalls 0
  after time $::w0 {
    set ::zcid [debug set_condition 1 {
      set p [reg pc]; set sl [lindex [get_selected_slot [expr {$p >> 14}]] 0]
      if {$p < 0x8000 && $sl == 0} {
        if {$::prevcart && $::ncalls < 400} { incr ::ncalls; puts $::f "ZBENTRY [format %.5f [machine_info time]] PC=[format %04X $p] SP=[format %04X [reg sp]] A=[format %02X [expr {[reg af]>>8}]] IX=[format %04X [reg ix]] IY=[format %04X [reg iy]] HL=[format %04X [reg hl]]" }
        set ::prevcart 0
      } elseif {$p >= 0x4000 && $p < 0x8000} { set ::prevcart 1 } else { set ::prevcart 0 }
    }]
  }
  after time $::w1 { debug remove_condition $::zcid }
}
# zerobas ONLY: patch OUR OWN main ROM in the emulator (an experiment, never a reference machine): "ADDR B1 B2 ..."
if {[info exists ::env(DOSREF_PATCH)]} {
  if {[string match "*Philips*" [machine_info config_name]]} { error "DOSREF_PATCH is for zerobas only" }
  set pa [lindex $::env(DOSREF_PATCH) 0]
  foreach b [lrange $::env(DOSREF_PATCH) 1 end] { debug write "C-BIOS Main ROM" $pa $b; incr pa }
  puts $::f "PATCHED $::env(DOSREF_PATCH) readback [debug read "C-BIOS Main ROM" [lindex $::env(DOSREF_PATCH) 0]]"
}
# DOSREF_SNAP=T: published data cells $F39A-$FD99, VRAM and VDP R#0-7 at the first H.RUNC entry after T s (S0) and
# at the first H.PHYD entry after that (S1); every VDP register change and the VRAM write count in between
if {[info exists ::env(DOSREF_SNAP)]} {
  proc snap {tag} {
    binary scan [debug read_block memory 0xF39A 0xA00] H* d
    binary scan [debug read_block "physical VRAM" 0 0x4000] H* v
    set r {}; for {set i 0} {$i < 8} {incr i} { lappend r [vdpreg $i] }
    puts $::f "SNAP $tag [format %.5f [machine_info time]] REGS $r"
    puts $::f "SNAPDATA $tag $d"
    puts $::f "SNAPVRAM $tag $v"
  }
  set ::snapst 0; set ::vw 0
  debug set_bp 0xFECB {[machine_info time] > $::env(DOSREF_SNAP) && $::snapst == 0} {
    set ::snapst 1; snap S0
    set ::regs {}; for {set i 0} {$i < 8} {incr i} { lappend ::regs [vdpreg $i] }
    set ::vwid [debug set_watchpoint write_io 0x98 {} { incr ::vw }]
    proc regpoll {} {
      if {$::snapst != 1} return
      for {set i 0} {$i < 8} {incr i} { if {[vdpreg $i] != [lindex $::regs $i]} { lset ::regs $i [vdpreg $i]; puts $::f "VDPREG [format %.5f [machine_info time]] R$i=[vdpreg $i] vramwrites=$::vw" } }
      after time 0.0002 regpoll
    }
    regpoll
  }
  debug set_bp 0xFFA7 {$::snapst == 1} { set ::snapst 2; puts $::f "VRAMWRITES $::vw"; snap S1 }
}
proc shot {tag} { puts $::f "=== SCREEN $tag s"; foreach l [split [get_screen] "\n"] { if {[string trim $l] ne ""} { puts $::f "  |$l" } } ; flush $::f }
foreach s {10 20} { after time $s "shot $s" }
after time SECS { puts $::f "hits0100 $::hits"; close $::f; exit }
""".replace("SECS", str(SECONDS))


def main():
    disk = probe_tmp.tmp(f"dosref_{os.path.basename(DISK)}")
    shutil.copyfile(DISK, disk)
    tcl = probe_tmp.tmp("dosref.tcl")
    open(tcl, "w").write(TCL)
    log = probe_tmp.tmp("dosref.log")
    cmd = [openmsx_paths.find_openmsx_binary(), "-machine", MACHINE, "-ext", EXT, "-diska", disk, "-script", tcl]
    subprocess.run(omsx_preflight.guarded(cmd), env=dict(os.environ, LOGF=log), stdout=subprocess.DEVNULL if not os.environ.get("DOSREF_DEBUG") else None,
                   stderr=subprocess.DEVNULL if not os.environ.get("DOSREF_DEBUG") else None, timeout=240)
    print(f"### {MACHINE} + {EXT}, disk {os.path.basename(DISK)} ({os.path.getsize(DISK)} B), {SECONDS} s")
    print(open(log).read() if os.path.exists(log) else "<NO LOG>")


if __name__ == "__main__":
    main()
