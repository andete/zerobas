#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""resetboot-acceptance (D-RESETBOOT, Joost's report 2026-10-11): after a RESET
the machine boots back into BASIC, and BASIC works.

zerobas stayed on C-BIOS's boot screen after a reset: RAM survives it, and
SUBSLOT_OK = 1 from the session before made ctl_reset call the sub ROM before
INIT had scanned for it (scratchpad/resetboot_trace.out).

openMSX driven directly (the basic_probe_bootkey.py shape): boot to the
prompt, optionally store `10 PRINT 9`, issue openMSX's `reset`, wait for the
prompt again, then type LIST (the program must be gone, as on the VG-8020)
and a line through the string heap and the float formatter -- both sub-ROM
paths, which is where the defect lived. Rows: idle / prog x VG-8020 (the
control) and both builds. Clean room: typed BASIC and the screen.
"""
import os, re, shutil, signal, subprocess, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import omsx_preflight                               # noqa: E402
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK", "C-BIOS_MSX1_EU_REPACK_DISK")
OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
WANT = "<< 2 AB 1.5 >>"
TCL = r"""
set throttle off
set ::line {PRINT"<<";1+1;LEFT$("ABC",2);1.5;">>"}
proc __rd16 {a} { expr {[debug read memory $a] + 256*[debug read memory [expr {$a+1}]]} }
proc __screen {} {
  if {[debug read memory 0xFCAF] != 0} { return "" }
  binary scan [debug read_block VRAM [__rd16 0xF3B3] 960] a* t
  return $t
}
proc __prompts {} { regexp -all {ZB|Ok} [__screen] }
proc __done {r} { set f [open {OUT} w]; puts $f $r; close $f; exit }
proc __wait {want next} {
  if {[machine_info time] > 90} { __done "TIMEOUT waiting for a prompt" }
  if {[__prompts] >= $want} { after time 1.0 $next; return }
  after time 0.1 [list __wait $want $next]
}
# After the reset, wait for the OLD prompt to go before waiting for the new one:
# the VG-8020 boots for ~8 s, and the first cut matched its stale `Ok`.
proc __gone {} {
  if {[machine_info time] > 90} { __done "TIMEOUT waiting for the screen to clear" }
  if {[__prompts] == 0} { __wait 1 __step2; return }
  after time 0.1 __gone
}
proc __step1 {} {
  if {"MODE" eq "prog"} { __key "10 PRINT 9\r" }
  after time 1.0 { reset; after time 0.1 __gone }
}
proc __step2 {} {
  __key "LIST\r"
  after time 1.0 { __key "$::line\r" }
  after time 3.0 {
    set t [__screen]
    set l [expr {[string first "10 PRINT 9" $t] >= 0 ? "LISTED" : "EMPTY"}]
    set i [string last "<<" $t]
    set j [string last ">>" $t]
    regsub -all {  +} $t { } dbg
    __done "$l [expr {$i >= 0 && $j > $i ? [string range $t $i [expr {$j+1}]] : "NONE: $dbg"}]"
  }
}
after time 0.5 { __wait 1 __step1 }
"""


def run(machine, mode):
    out = probe_tmp.tmp(f"resetgate_{machine}_{mode}.txt")
    tcl = probe_tmp.tmp(f"resetgate_{machine}_{mode}.tcl")
    if os.path.exists(out):
        os.unlink(out)
    # Keys go through the harness's KEYBUF injector, not openMSX `type`: `type`
    # drives the matrix with SHIFT for `"` `<` `$`, and the first cut came back
    # with a cleared screen and the F6..F10 labels up on every machine.
    open(tcl, "w").write(omsx_repl.key_proc() + TCL.replace("{OUT}", "{" + out + "}")
                         .replace("MODE", mode))
    proc = subprocess.Popen(omsx_preflight.guarded(
                                [OMSX, "-machine", machine, "-command",
                                 "set renderer none; set sound_driver null", "-script", tcl]),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    deadline = time.time() + 240
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.2)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        return "TIMEOUT"
    return open(out).read().strip() if os.path.exists(out) else "NO OUTPUT"


def main():
    bad, fault = [], False
    for m in MACHINES:
        for mode in ("idle", "prog"):
            r = run(m, mode)
            ok = r == f"EMPTY {WANT}"
            print(f"ROW {m:30s} {mode}: {r} {'PASS' if ok else 'FAIL'}", flush=True)
            if not ok:
                (bad.append if "8020" not in m else (lambda x: None))(f"{m}/{mode}")
                fault |= "8020" in m
    if fault:
        print("\nINSTRUMENT FAULT: the VG-8020 control did not come back as expected")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: after a reset the machine boots into BASIC "
          f"and BASIC works" + (f" -- {bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
