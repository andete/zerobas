#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-DISKROMHOST step 2: zerobas's disk ROM on a host. Boots MACHINE (+ an extension, or "none") with a private COPY of
DISK (or "none") and reports: entries into a few of zerobas's OWN disk-ROM routines (by build/disk.sym, only while page
1 is a non-slot-0 ROM slot -- the cartridge / slot 3-1; never on a reference machine without our ROM), H.RUNC entries,
the first RAM $0100 entries after 1 s (MSX-DOS), the screen at a few times, and -- when KEYS are given -- the typed
lines' answers. Black box on the reference: the screen, RAM cells and hook-address breakpoints only.

    python3 -u scratchpad/diskhost_probe.py MACHINE EXT|none DISK|none SECONDS ["T:text\\r|T2:text2\\r"]
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
KEYS = sys.argv[5] if len(sys.argv) > 5 else ""
# our disk ROM is in the machine: only then are its own symbols traced (never a reference cartridge or machine ROM)
OURS = EXT.startswith("zerobas-disk") or "REPACK" in MACHINE or "ZEROBASDISK" in MACHINE or MACHINE.endswith("_BASIC_DISK")
SYMS = ["init", "init_p2", "hrunc_h", "boot_disk_go", "dos_handoff"]

TCL = r"""
set renderer none
set throttle off
catch { set sound_driver null }
set f [open $::env(LOGF) w]
set ::hits 0
debug set_bp 0x0100 {[machine_info time] > 1.0 && [lindex [get_selected_slot 0] 0] != 0} {
  incr ::hits; if {$::hits <= 2} { puts $::f "HIT0100 [format %.3f [machine_info time]] SCRMOD=[peek 0xFCAF] LINLEN=[peek 0xF3B0] HIMEM=[format %04X [peek16 0xFC4A]]" }
}
set ::hk 0
debug set_bp 0xFECB {} { incr ::hk; if {$::hk <= 8} { puts $::f "HRUNC [format %.4f [machine_info time]] SP=[format %04X [reg sp]] HIMEM=[format %04X [peek16 0xFC4A]]" } }
set ::hs 0
debug set_bp 0xFEDA {} { incr ::hs; if {$::hs <= 4} { puts $::f "HSTKE [format %.4f [machine_info time]] SP=[format %04X [reg sp]] byte0=[format %02X [peek 0xFEDA]]" } }
array set ::sc {}
foreach {nm a} $::env(SYMS) {
  set ::sc($nm) 0
  debug set_bp $a "\[lindex \[get_selected_slot 1\] 0\] != 0" "incr ::sc($nm); if {\$::sc($nm) <= 3} { puts \$::f \"SYM $nm \[format %.4f \[machine_info time\]\] SP=\[format %04X \[reg sp\]\] HIMEM=\[format %04X \[peek16 0xFC4A\]\]\" }"
}
proc shot {tag} {
  binary scan [debug read_block memory 0xFECB 5] H* x
  puts $::f "=== SCREEN $tag s HIMEM=[format %04X [peek16 0xFC4A]] H.RUNC-all-RET=[expr {$x eq "c9c9c9c9c9"}] H.RUNC-byte0=[string range $x 0 1]"
  foreach l [split [get_screen] "\n"] { if {[string trim $l] ne ""} { puts $::f "  |$l" } } ; flush $::f
}
if {$::env(KEYS) ne ""} {
  foreach kv [split $::env(KEYS) "|"] {
    set i [string first ":" $kv]
    set t [string range $kv 0 [expr {$i - 1}]]
    set txt [string map {"\\r" "\r"} [string range $kv [expr {$i + 1}] end]]
    after time $t [list type $txt]
  }
}
foreach s $::env(SHOTS) { after time $s "shot $s" }
after time SECS { puts $::f "hits0100 $::hits"; close $::f; exit }
""".replace("SECS", str(SECONDS))


def syms():
    if not OURS:
        return ""
    tab = {}
    for line in open(os.path.join(ROOT, "build", "disk.sym")):
        p = line.split()
        if len(p) >= 3 and p[1] == "EQU":
            tab[p[0]] = int(p[2].rstrip("H"), 16)
    return " ".join(f"{n} {tab[n]}" for n in SYMS if n in tab)


def main():
    tcl = probe_tmp.tmp("diskhost.tcl")
    open(tcl, "w").write(TCL)
    log = probe_tmp.tmp("diskhost.log")
    cmd = [openmsx_paths.find_openmsx_binary(), "-machine", MACHINE]
    if EXT != "none":
        cmd += ["-ext", EXT]
    if DISK != "none":
        disk = probe_tmp.tmp(f"diskhost_{os.path.basename(DISK)}")
        shutil.copyfile(DISK, disk)                     # a private copy: the original is never written
        cmd += ["-diska", disk]
    cmd += ["-script", tcl]
    shots = os.environ.get("SHOTS", f"{SECONDS - 0.5}")
    env = dict(os.environ, LOGF=log, SYMS=syms(), KEYS=KEYS, SHOTS=shots.replace(",", " "))
    subprocess.run(omsx_preflight.guarded(cmd), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=300)
    print(f"### {MACHINE} + {EXT}, disk {os.path.basename(DISK)}, {SECONDS} s, keys {KEYS!r}")
    print(open(log).read() if os.path.exists(log) else "<NO LOG>")


if __name__ == "__main__":
    main()
