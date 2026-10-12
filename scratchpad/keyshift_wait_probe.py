#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-KEYSHIFT, measure first: WHICH key waits switch the key line to F6..F10
while SHIFT is held? (keyidle_probe.out: the idle prompt does, on the
VG-8020; keyshift_run.out, 2026-09-26: a busy FOR loop does not.)

A one-line program waits in each form; once it is waiting, SHIFT (row 6 bit 0)
goes down and, while it is held, the bottom row of the name table and FNKSWI
($FBCD) are read. Keys are injected into KEYBUF (omsx_repl's injector), never
with openMSX `type`, which holds SHIFT itself. Clean room: the key matrix,
VRAM, one documented cell, typed BASIC.

Prediction: on the VG-8020 INPUT$(1), INPUT and LINE INPUT switch; the busy
INKEY$ loop does not; with KEY OFF nothing is drawn. Scored: the INKEY$ loop
DOES switch (a MISS) -- the switch rides CHSNS. Round 2 adds `busy`.
"""
import os, shutil, signal, subprocess, sys, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight                               # noqa: E402
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")
OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
CASES = {"inputs": "10 A$=INPUT$(1)", "input": "10 INPUT A",
         "lineinput": "10 LINE INPUT A$", "inkey": "10 A$=INKEY$:GOTO 10",
         "keyoff": "10 KEY OFF:A$=INPUT$(1)",
         # the negative: a loop that never asks the keyboard (09-26's
         # keyshift_probe.py cannot read zerobas within its capture window)
         "busy": "10 FOR I=1 TO 30000:NEXT"}
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
  return $s
}
proc __done {r} { set f [open {OUT} w]; puts $f $r; close $f; exit }
proc __wait {} {
  if {[machine_info time] > 60} { __done "NO PROMPT" }
  if {[regexp {ZB|Ok} [__screen]]} { after time 1.0 __go; return }
  after time 0.1 __wait
}
proc __go {} {
  __key "LINE\r"
  after time 1.0 { __key "RUN\r" }
  after time 2.5 {
    set a "rest FNKSWI=[debug read memory 0xFBCD] <[__last]>"
    keymatrixdown 6 0x01
    after time 0.6 [list __held $a]
  }
}
proc __held {a} {
  __done "$a | shift FNKSWI=[debug read memory 0xFBCD] <[__last]>"
}
after time 0.5 __wait
"""


def run(machine, case):
    out = probe_tmp.tmp(f"kswait_{machine}_{case}.txt")
    tcl = probe_tmp.tmp(f"kswait_{machine}_{case}.tcl")
    if os.path.exists(out):
        os.unlink(out)
    body = TCL.replace("{OUT}", "{" + out + "}").replace('"LINE\\r"', '"' + CASES[case].replace('"', '\\"').replace("$", "\\$") + '\\r"')
    open(tcl, "w").write(omsx_repl.key_proc() + body)
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
    for case in CASES:
        for m in MACHINES:
            print(f"{case:10s} {m:30s} {run(m, case)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
