#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Joost, 2026-10-11: "when pressing shift, the F1-F5 commands below should
switch to the F6-F10 ones". The 2026-09-26 probe (keyshift_probe.py) measured
only a RUNNING program -- where the VG-8020 does NOT switch -- and could not
read the idle prompt, because omsx_repl releases a held key before capturing.

This one drives openMSX directly (the basic_probe_bootkey.py shape): wait for
the prompt, read the key line (the bottom row of the name table) and FNKSWI
($FBCD) at rest, press SHIFT (matrix row 6 bit 0), read both WHILE IT IS
HELD, release it, read again. CTRL (row 6 bit 1) is the control: it makes no
character and should not switch the line. Clean room: the key matrix, VRAM,
one documented work-area cell. No ROM byte is read.

Prediction: VG-8020 shows F6..F10 labels with SHIFT held and FNKSWI flips to
0, back on release; CTRL changes nothing. zerobas never switches.
"""
import os, shutil, signal, subprocess, sys, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight                               # noqa: E402
import probe_tmp                                    # noqa: E402

ROWS = (("vg8020", "Philips_VG_8020"), ("nodisk", "C-BIOS_MSX1_EU_REPACK_NODISK"))
OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"

TCL = r"""
set throttle off
set ::f [open {OUT} w]
proc __rd16 {a} { expr {[debug read memory $a] + 256*[debug read memory [expr {$a+1}]]} }
proc __screen {} {
  set base [__rd16 0xF3B3]
  binary scan [debug read_block VRAM $base 960] a* t
  return $t
}
proc __prompt_seen {t} {
  for {set r 0} {$r < 24} {incr r} {
    set s [string trim [string range $t [expr {$r*40}] [expr {$r*40+39}]]]
    if {$s eq "ZB" || $s eq "Ok"} { return 1 }
  }
  return 0
}
proc __read {tag} {
  set t [__screen]
  set last [string range $t 920 959]
  regsub -all {[^ -~]} $last {.} last
  puts $::f "$tag FNKSWI=[debug read memory 0xFBCD] <$last>"
}
proc __seq {} {
  __read rest
  keymatrixdown 6 0x01
  after time 0.5 {
    __read shift_held
    keymatrixup 6 0x01
    after time 0.5 {
      __read shift_up
      keymatrixdown 6 0x02
      after time 0.5 {
        __read ctrl_held
        keymatrixup 6 0x02
        after time 0.5 { __read ctrl_up; close $::f; exit }
      }
    }
  }
}
proc __poll {} {
  if {[machine_info time] > 40} { puts $::f "NO PROMPT"; close $::f; exit }
  if {[debug read memory 0xFCAF] == 0 && [__prompt_seen [__screen]]} {
    after time 1.0 __seq
    return
  }
  after time 0.05 __poll
}
after time 0.5 __poll
"""


def run(machine):
    out = probe_tmp.tmp(f"keyidle_{machine}.txt")
    tcl = probe_tmp.tmp(f"keyidle_{machine}.tcl")
    if os.path.exists(out):
        os.unlink(out)
    open(tcl, "w").write(TCL.replace("{OUT}", "{" + out + "}"))
    proc = subprocess.Popen(omsx_preflight.guarded(
                                [OMSX, "-machine", machine, "-command",
                                 "set renderer none; set sound_driver null", "-script", tcl]),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    deadline = time.time() + 120
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.2)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        return "TIMEOUT"
    return open(out).read().rstrip() if os.path.exists(out) else "NO OUTPUT"


def main():
    for name, m in ROWS:
        print(f"== {name} ({m})")
        print(run(m))
    return 0


if __name__ == "__main__":
    sys.exit(main())
