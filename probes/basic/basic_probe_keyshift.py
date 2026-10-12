#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""keyshift-acceptance (D-KEYSHIFT, Joost's report 2026-10-11): while SHIFT is
held, the function-key line shows F6..F10 -- whenever BASIC asks the keyboard.

Measured on the VG-8020 (scratchpad/keyidle_probe.out, keyshift_wait.out):
the prompt, INPUT, LINE INPUT, INPUT$ and an INKEY$ loop switch, and switch
back on release; a loop that never asks the keyboard does not; with KEY OFF
nothing is drawn and FNKSWI stays 1. zerobas never switched.

openMSX driven directly so the key line can be read WHILE the key is held:
each case waits (or idles at the prompt), then the bottom row of the name
table and FNKSWI ($FBCD) are read at rest, with SHIFT (row 6 bit 0) held, and
after release. Keys typed through omsx_repl's KEYBUF injector. Every row of
the diskless build must equal the VG-8020's. Clean room: the key matrix,
VRAM, one documented cell, typed BASIC.
"""
import os, shutil, signal, subprocess, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import omsx_preflight                               # noqa: E402
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
CASES = {"prompt": None, "inputs": "10 A$=INPUT$(1)", "input": "10 INPUT A",
         "lineinput": "10 LINE INPUT A$", "inkey": "10 A$=INKEY$:GOTO 10",
         "keyoff": "10 KEY OFF:A$=INPUT$(1)", "busy": "10 FOR I=1 TO 30000:NEXT"}
TCL = r"""
set throttle off
proc __rd16 {a} { expr {[debug read memory $a] + 256*[debug read memory [expr {$a+1}]]} }
proc __screen {} {
  if {[debug read memory 0xFCAF] != 0} { return "" }
  binary scan [debug read_block VRAM [__rd16 0xF3B3] 960] a* t
  return $t
}
proc __last {} {
  set s [string range [__screen] 920 959]
  regsub -all {[^ -~]} $s {.} s
  regsub -all {  +} [string trim $s] { } s
  return "FNKSWI=[debug read memory 0xFBCD] <$s>"
}
proc __done {r} { set f [open {OUT} w]; puts $f $r; close $f; exit }
proc __wait {} {
  if {[machine_info time] > 60} { __done "NO PROMPT" }
  if {[regexp {ZB|Ok} [__screen]]} { after time 1.0 __go; return }
  after time 0.1 __wait
}
proc __go {} {
  if {"LINE" ne ""} {
    __key "LINE\r"
    after time 1.0 { __key "RUN\r" }
    after time 2.5 __read
  } else {
    after time 0.5 __read
  }
}
proc __read {} {
  set a "rest [__last]"
  keymatrixdown 6 0x01
  after time 0.6 [list __held $a]
}
proc __held {a} {
  set ::ra $a
  set ::rb "held [__last]"
  keymatrixup 6 0x01
  after time 1.5 { __done "$::ra | $::rb | up [__last]" }
}
after time 0.5 __wait
"""


def run(machine, case):
    out = probe_tmp.tmp(f"keyshift_{machine}_{case}.txt")
    tcl = probe_tmp.tmp(f"keyshift_{machine}_{case}.tcl")
    if os.path.exists(out):
        os.unlink(out)
    line = (CASES[case] or "").replace('"', '\\"').replace("$", "\\$")
    open(tcl, "w").write(omsx_repl.key_proc()
                         + TCL.replace("{OUT}", "{" + out + "}").replace("LINE", line))
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
    return open(out).read().strip() if os.path.exists(out) else "NO OUTPUT"


def main():
    only = sys.argv[1:] or list(CASES)
    bad, fault = [], False
    for case in only:
        a, b = run(REF, case), run(ZB, case)
        same = a == b
        print(f"ROW {case:10s} VG-8020 [{a}]\n{'':15s}zerobas [{b}] {'SAME' if same else 'DIVERGES'}",
              flush=True)
        fault |= not a.startswith("rest ")
        if not same:
            bad.append(case)
    if fault:
        print("\nINSTRUMENT FAULT: the VG-8020 gave no reading")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: the key line follows SHIFT as on the VG-8020"
          + (f" -- {bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
