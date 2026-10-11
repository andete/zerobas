#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-AUTORUN, end to end: openMSX's OWN tape autorun, three tape types.

The way a user meets it: `autoruncassettes` on and a tape inserted before the
first prompt. openMSX then sets its breakpoint on H.READ and types the load
command when the prompt arrives -- RUN"CAS:" for an ASCII file, BLOAD"CAS:",R
for a binary, CLOAD (then RUN, on the next H.MAIN) for a tokenised program.
Every tape's program prints AUTORAN; the row passes when that appears on the
screen within the time limit.

Driven directly (the basic_probe_bootkey.py shape) because the setting and the
insertion must precede the first prompt. Clean room: our own tapes, the
screen. No ROM byte is read.
"""
import os, shutil, signal, subprocess, sys, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight                               # noqa: E402
import probe_tmp                                    # noqa: E402
import cas_encode                                   # noqa: E402

MACHINES = tuple(os.environ.get("AUTORUN_MACHINES", "Philips_VG_8020,"
                 "C-BIOS_MSX1_EU_REPACK_NODISK,C-BIOS_MSX1_EU_REPACK_DISK").split(","))
OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
LIMIT = 90.0

# LD HL,msg / loop: LD A,(HL) / OR A / RET Z / CALL CHPUT / INC HL / JR loop
CODE = bytes([0x21, 0x0D, 0xC0, 0x7E, 0xB7, 0xC8, 0xCD, 0xA2, 0x00, 0x23,
              0x18, 0xF7, 0x00]) + b"AUTORAN\r\n\0"
BODY = bytes([0x91]) + b'"AUTORAN"' + b"\0"          # PRINT"AUTORAN"
TOKPROG = (0x8001 + 4 + len(BODY)).to_bytes(2, "little") + (10).to_bytes(2, "little") \
    + BODY + b"\0\0"
TAPES = {"ascii": cas_encode.build_cas_ascii("AUTO", '10 PRINT"AUTORAN"\n'),
         "binary": cas_encode.build_cas("AUTO", 0xC000, 0xC000, CODE),
         "tokenised": cas_encode.build_cas_basic_csave("AUTO", TOKPROG)}

TCL = r"""
set throttle off
# 🔴 omsx_preflight.guarded() un-arms autorun on EVERY launch (a trace on
# `cassetteplayer` + a direct un-arm that runs AFTER this script's top level),
# so this probe, which WANTS autorun, removes the trace and inserts from an
# `after` -- still long before the first prompt (scratchpad/noautorun_diag2.out J)
after time 0.3 {
  trace remove execution cassetteplayer leave ::__zb_unarm
  set autoruncassettes on
  cassetteplayer insert {CAS}
}
proc __rd16 {a} { expr {[debug read memory $a] + 256*[debug read memory [expr {$a+1}]]} }
proc __done {r} {
  set f [open {OUT} w]
  puts $f "$r t=[format %.1f [machine_info time]]"
  close $f; exit
}
proc __poll {} {
  if {[debug read memory 0xFCAF] == 0} {
    binary scan [debug read_block VRAM [__rd16 0xF3B3] 960] a* t
    if {[string first "AUTORAN" $t] >= 0} { __done RAN }
  }
  if {[machine_info time] > LIMIT} { __done NOT-RUN }
  after time 0.2 __poll
}
after time 0.5 __poll
"""


def run(machine, kind):
    cas = probe_tmp.tmp(f"autorun_e2e_{kind}.cas")
    open(cas, "wb").write(TAPES[kind])
    out = probe_tmp.tmp(f"autorun_e2e_{machine}_{kind}.txt")
    tcl = probe_tmp.tmp(f"autorun_e2e_{machine}_{kind}.tcl")
    if os.path.exists(out):
        os.unlink(out)
    open(tcl, "w").write(TCL.replace("{CAS}", "{" + cas + "}")
                         .replace("{OUT}", "{" + out + "}").replace("LIMIT", str(LIMIT)))
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
    bad = 0
    for m in MACHINES:
        for kind in TAPES:
            r = run(m, kind)
            bad += not r.startswith("RAN")
            print(f"{m:32s} {kind:10s} {r}", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
