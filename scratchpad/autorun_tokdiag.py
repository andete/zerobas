#!/usr/bin/env python3
# D-BIOSLADDER B1 follow-up: why the tokenised tape no longer autoruns on zerobas.
# basic_probe_autorun's own Tcl, plus a write watchpoint on KEYBUF (time:byte) after
# t = 1 s, and the screen text at the end. RAM / VRAM read back; no ROM byte.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "basic"))
import basic_probe_autorun as A
A.LIMIT = 30.0
EXTRA = r'''
set ::kl {}
set ::hk {}
debug set_bp 0xFF07 {} {lappend ::hk [format {%.2f:READ} [machine_info time]]}
if {[string match *REPACK* [machine_info config_name]]} { debug set_bp 0x1B45 {} {lappend ::hk [format {%.2f:EXTROMS} [machine_info time]]} }
debug set_bp 0xFF0C {} {lappend ::hk [format {%.2f:MAIN} [machine_info time]]}
debug set_watchpoint write_mem {0xFBF0 0xFC17} {$::wp_last_value != 0 && $::wp_last_value != 255} {lappend ::kl [format {%.2f:%02X} [machine_info time] $::wp_last_value]}
proc __done {r} {
  binary scan [debug read_block VRAM [__rd16 0xF3B3] 960] a* t
  set rows {}
  for {set i 0} {$i < 24} {incr i} { lappend rows [string trimright [string range $t [expr {$i*40}] [expr {$i*40+39}]]] }
  set f [open {OUT} w]
  puts $f "$r t=[format %.1f [machine_info time]] keys=$::kl hooks=[lrange $::hk 0 12] screen=[join $rows |]"
  close $f; exit
}
'''
A.TCL = A.TCL.replace("after time 0.5 __poll", EXTRA + "after time 0.5 __poll")
m = sys.argv[1] if len(sys.argv) > 1 else "C-BIOS_MSX1_EU_REPACK_NODISK"
os.environ["ZEROBAS_REFCACHE"] = "0"
print(A.run(m, "tokenised"))
