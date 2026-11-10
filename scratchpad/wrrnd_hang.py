#!/usr/bin/env python3
# D-BDOSFCB stage A regression: $F37D WRRND on a FMAKE'd, still-open file (one SEQWRITE
# buffered, SETRND, RDRND before it) never returns on zerobas (bdosset_probe row 22;
# fine at 6d554edd). Runs bdosset's image on OUR machine and, at 150 s, samples PC and
# the top stack words 40 times, 0.01 s apart, to see where it loops. Our own disk ROM's
# PC only: the reference machines are not run.
import os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "lib"))
import omsx_preflight
import bdosset_probe as P
machine, extra = P.MACHINES["zb"]
td = tempfile.mkdtemp(prefix="wrrndhang_")
dsk = os.path.join(td, "v.dsk"); open(dsk, "wb").write(P.image())
out = os.path.join(td, "o.txt")
logp = os.path.join(HERE, "wrrnd_hang_log.out")
tcl = r'''set throttle off
set ::s {}
proc samp {n} {
  set sp [reg sp]
  binary scan [debug read_block memory $sp 8] H* st
  lappend ::s [format {%04X/%s/%s} [reg pc] [format %04X $sp] $st]
  if {$n > 0} { after time 0.01 "samp [expr {$n-1}]" } else {
    binary scan [debug read_block memory 0xC7FE 2] H* flag
    set f [open {OUT} w]; puts $f "flag=$flag"; foreach x $::s { puts $f $x }; close $f; exit }
}
set ::log {}
set ::armed 1
proc stepn {n} {
  for {set i 0} {$i < $n} {incr i} {
    lappend ::log [format {%04X:%02X} [reg pc] [reg a]]
    debug step
  }
}
debug set_bp 0x44FF {[pc_in_slot 3 1] && [reg c] == 0x24 && $::armed} {set ::armed 0; stepn 60}
after time 150 {set f [open {LOGPATH} w]; puts $f $::log; close $f; samp 40}
'''.replace("OUT", out).replace("LOGPATH", logp)
open(os.path.join(td, "s.tcl"), "w").write(tcl)
subprocess.run(omsx_preflight.guarded(["/opt/homebrew/bin/openmsx", "-machine", machine] + extra +
               ["-diska", dsk, "-command", "set renderer none; set sound_driver null",
                "-script", os.path.join(td, "s.tcl")]), stdout=subprocess.DEVNULL,
               stderr=subprocess.DEVNULL, timeout=300)
print(open(out).read() if os.path.exists(out) else "NO OUTPUT")
shutil.rmtree(td, ignore_errors=True)
