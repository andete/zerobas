#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-DISKROMHOST step 2b: the TWO-STEP HIMEM claim of a disk ROM and the layout it leaves, black box.

Boots MACHINE (+ EXT, or "none") with a private COPY of DISK (or "none") and logs, by time:
  WR <cell>   every write to HIMEM / MEMSIZ / STKTOP / FILTAB (a RAM watchpoint): the value written and SP
  HRUNC       each H.RUNC ($FECB, a hook address in RAM) entry: SP and the layout cells
  DOS         the first two RAM $0100 entries after 1 s (MSX-DOS): the layout cells, the screen cells, VDP R#0-R#7,
              the words at $0006 and $0038-$003A (RAM under DOS), DRVTBL $FB21-$FB28, SLTWRK's non-zero entries
  AT <t>      the cells at a time; with no DOS disk BASIC is at its Ok, and the probe types
              PRINT FRE(0);FRE("") and shows the answer
CLEAN ROOM: only registers other than PC, work-area RAM ($F39A-$FD99; never $F380-$F399, never a hook's bytes from
$FD9A up), RAM below $F380 (the file table) and VDP registers. No ROM byte is read, no PC recorded.

    python3 -u scratchpad/diskhost2_ref.py MACHINE EXT|none DISK|none SECONDS
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
SECONDS = float(sys.argv[4])

TCL = r"""
set renderer none
set throttle off
catch { set sound_driver null }
set f [open $::env(LOGF) w]
proc w16 {a} { format %04X [peek16 $a] }
proc t {} { format %.4f [machine_info time] }
proc cells {} {
  set s "HIMEM=[w16 0xFC4A] MEMSIZ=[w16 0xF672] STKTOP=[w16 0xF674] FRETOP=[w16 0xF69B] SAVSTK=[w16 0xF6B1]"
  append s " FILTAB=[w16 0xF860] NULBUF=[w16 0xF862] MAXFIL=[peek 0xF85F]"
  set ft [peek16 0xF860]
  if {$ft >= 0x8000 && $ft < 0xF370} {
    set tw {}
    for {set i 0} {$i <= [peek 0xF85F] && $i < 8} {incr i} { lappend tw [w16 [expr {$ft + 2*$i}]] }
    append s " TAB=\[$tw\]"
  }
  return $s
}
proc scr {} {
  set s "SCRMOD=[peek 0xFCAF] OLDSCR=[peek 0xFCB0] LINLEN=[peek 0xF3B0] LINL40=[peek 0xF3AE] LINL32=[peek 0xF3AF]"
  append s " CRTCNT=[peek 0xF3B1] CSRY=[peek 0xF3DC] CSRX=[peek 0xF3DD] CNSDFG=[peek 0xF3DE]"
  set r {}
  for {set i 0} {$i < 8} {incr i} { lappend r [format %02X [vdpreg $i]] }
  append s " VDP=\[$r\]"
  return $s
}
set ::nw 0
foreach {nm a} {HIMEM 0xFC4A MEMSIZ 0xF672 STKTOP 0xF674 FRETOP 0xF69B SAVSTK 0xF6B1 FILTAB 0xF860} {
  debug set_watchpoint write_mem [list $a [expr {$a + 1}]] {} "incr ::nw; if {\$::nw <= 400} { puts \$::f \"WR $nm\[expr {\$::wp_last_address - $a ? {.hi} : {.lo}}\] \[t\] val=\[format %02X \$::wp_last_value\] SP=\[format %04X \[reg sp\]\]\" }"
}
set ::hk 0
debug set_bp 0xFECB {} { incr ::hk; if {$::hk <= 6} { puts $::f "HRUNC [t] SP=[format %04X [reg sp]] [cells]" } }
set ::hits 0
debug set_bp 0x0100 {[machine_info time] > 1.0 && [lindex [get_selected_slot 0] 0] != 0} {
  incr ::hits
  if {$::hits <= 2} {
    puts $::f "DOS [t] SP=[format %04X [reg sp]] [cells]"
    puts $::f "DOS     [scr]"
    set d {}
    for {set i 0} {$i < 8} {incr i} { lappend d [format %02X [peek [expr {0xFB21 + $i}]]] }
    puts $::f "DOS     W0006=[w16 0x0006] B0038=[format %02X%02X%02X [peek 0x38] [peek 0x39] [peek 0x3A]] DRVTBL=\[$d\]"
    set sw {}
    for {set a 0xFD09} {$a < 0xFD89} {incr a 2} {
      set v [peek16 $a]
      if {$v != 0} { set o [expr {$a - 0xFD09}]; lappend sw "[expr {$o/32}]-[expr {($o%32)/8}]p[expr {($o%8)/2}]:[format %04X $v]" }
    }
    puts $::f "DOS     SLTWRK=\[$sw\]"
    flush $::f
  }
}
proc at {tag} {
  puts $::f "AT $tag [t] [cells]"
  puts $::f "AT      [scr]"
  foreach l [split [get_screen] "\n"] { if {[string trim $l] ne ""} { puts $::f "  |$l" } }
  flush $::f
}
after time [expr {SECS - 6}] { at pre }
after time [expr {SECS - 5.5}] { type "\r" }
after time [expr {SECS - 4}] { type "PRINT FRE(0);FRE(\"\")\r" }
after time [expr {SECS - 0.5}] { at end ; puts $::f "hits0100 $::hits HRUNCs $::hk"; close $::f; exit }
""".replace("SECS", str(SECONDS))


def main():
    tcl = probe_tmp.tmp("diskhost2.tcl")
    open(tcl, "w").write(TCL)
    log = probe_tmp.tmp("diskhost2.log")
    if os.path.exists(log):
        os.remove(log)
    cmd = [openmsx_paths.find_openmsx_binary(), "-machine", MACHINE]
    if EXT != "none":
        cmd += ["-ext", EXT]
    if DISK != "none":
        disk = probe_tmp.tmp(f"diskhost2_{os.path.basename(DISK)}")
        shutil.copyfile(DISK, disk)                     # a private copy: the original is never written
        cmd += ["-diska", disk]
    cmd += ["-script", tcl]
    env = dict(os.environ, LOGF=log)
    subprocess.run(omsx_preflight.guarded(cmd), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=400)
    print(f"### {MACHINE} + {EXT}, disk {os.path.basename(DISK)}, {SECONDS} s")
    print(open(log).read() if os.path.exists(log) else "<NO LOG>")


if __name__ == "__main__":
    main()
