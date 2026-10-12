#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RESETBOOT (Joost, 2026-10-11): "when resetting the msx machine it doesn't
boot back to basic". Measure first.

openMSX driven directly (the basic_probe_bootkey.py shape): wait for the
first prompt, optionally type a program line, issue openMSX's `reset` (the
machine's reset button), wait, then read the screen and the CPU's PC (a
register -- readable; no ROM byte is read). A second read 4 s later says
whether the PC is parked (a hang) or moving.

  idle   reset at the prompt
  prog   reset with `10 PRINT 1` stored

Prediction: the VG-8020 shows its banner and `Ok` again; zerobas does not
reach `ZB`.
"""
import os, shutil, signal, subprocess, sys, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight                               # noqa: E402
import probe_tmp                                    # noqa: E402

MACHINES = tuple(os.environ.get("RESETBOOT_MACHINES", "Philips_VG_8020,"
                 "C-BIOS_MSX1_EU_REPACK_NODISK,C-BIOS_MSX1_EU_REPACK_DISK").split(","))
OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
TCL = r"""
set throttle off
set ::f [open {OUT} w]
set ::phase 0
proc __rd16 {a} { expr {[debug read memory $a] + 256*[debug read memory [expr {$a+1}]]} }
proc __w {} { expr {[debug read memory 0xFCAF] == 0 ? 40 : 32} }
proc __screen {} {
  set m [debug read memory 0xFCAF]
  if {$m > 1} { return "" }
  set base [__rd16 [expr {$m == 0 ? 0xF3B3 : 0xF3BD}]]
  binary scan [debug read_block VRAM $base [expr {[__w]*24}]] a* t
  return $t
}
proc __rows {t} {
  set r {}
  set w [__w]
  for {set i 0} {$i < 24} {incr i} {
    set s [string trim [string range $t [expr {$i*$w}] [expr {$i*$w+$w-1}]]]
    regsub -all {[^ -~]} $s {.} s
    if {$s ne ""} { lappend r $s }
  }
  return [join $r " | "]
}
proc __prompt {t} { expr {[string first "ZB" $t] >= 0 || [string first "Ok" $t] >= 0} }
proc __pc {} { format %04X [reg pc] }
proc __poll {} {
  if {[machine_info time] > 60} { puts $::f "NO FIRST PROMPT"; close $::f; exit }
  if {[__prompt [__screen]]} { after time 1.0 __act; return }
  after time 0.1 __poll
}
proc __act {} {
  if {"MODE" eq "prog"} { type "10 PRINT 1\r" }
  after time 1.0 {
    puts $::f "before: [__rows [__screen]]"
    reset
    foreach dt {1 3 6} {
      after time $dt "puts \$::f \"after ${dt}s: pc=\[__pc\] mode=\[debug read memory 0xFCAF\] rows: \[__rows \[__screen\]\]\""
    }
    after time 12 {
      puts $::f "after 12s: pc=[__pc] screen0=[expr {[debug read memory 0xFCAF]}] rows: [__rows [__screen]]"
      after time 4 {
        puts $::f "after 16s: pc=[__pc]"
        close $::f; exit
      }
    }
  }
}
after time 0.5 __poll
"""


def run(machine, mode):
    out = probe_tmp.tmp(f"resetboot_{machine}_{mode}.txt")
    tcl = probe_tmp.tmp(f"resetboot_{machine}_{mode}.tcl")
    if os.path.exists(out):
        os.unlink(out)
    open(tcl, "w").write(TCL.replace("{OUT}", "{" + out + "}").replace("MODE", mode))
    proc = subprocess.Popen(omsx_preflight.guarded(
                                [OMSX, "-machine", machine, "-command",
                                 "set renderer none; set sound_driver null", "-script", tcl]),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    deadline = time.time() + 180
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.2)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        return "TIMEOUT"
    return open(out).read().rstrip() if os.path.exists(out) else "NO OUTPUT"


def main():
    for m in MACHINES:
        for mode in ("idle", "prog"):
            print(f"== {m} {mode}\n{run(m, mode)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
