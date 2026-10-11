#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Which launch form actually stops openMSX's tape autorun? An ASCII tape
mounted, zerobas diskless, the screen read 12 s in: did `RUN"CAS:"` appear?

  A  -cassetteplayer only                                   (control: autoruns)
  B  -command "set autoruncassettes off" -cassetteplayer    (the msgexact rule)
  C  -cassetteplayer, then the -script removes openMSX's armed breakpoint
     (::openmsx::auto_run_bp) before the first prompt
  D  the same removal as a -command, placed before -cassetteplayer
Clean room: our own tape and the screen.
"""
import os, shutil, signal, subprocess, sys, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import probe_tmp                                    # noqa: E402
import cas_encode                                   # noqa: E402

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
M = "C-BIOS_MSX1_EU_REPACK_NODISK"
UNARM = ("if {[info exists ::openmsx::auto_run_bp]} "
         "{ debug remove_bp $::openmsx::auto_run_bp; unset ::openmsx::auto_run_bp }\n")
TCL = r"""
set throttle off
PRE
proc __rd16 {a} { expr {[debug read memory $a] + 256*[debug read memory [expr {$a+1}]]} }
after time 12 {
  binary scan [debug read_block VRAM [__rd16 0xF3B3] 960] a* t
  set f [open {OUT} w]
  puts $f [expr {[string first "RUN\"CAS:\"" $t] >= 0 ? "AUTORAN" : "quiet"}]
  close $f; exit
}
"""


def run(tag, pre_args, pre_tcl):
    cas = probe_tmp.tmp("noautorun.cas")
    open(cas, "wb").write(cas_encode.build_cas_ascii("X", '10 PRINT"HI"\n'))
    out, tcl = probe_tmp.tmp(f"noautorun_{tag}.txt"), probe_tmp.tmp(f"noautorun_{tag}.tcl")
    if os.path.exists(out):
        os.unlink(out)
    open(tcl, "w").write(TCL.replace("PRE", pre_tcl).replace("{OUT}", "{" + out + "}"))
    # 🔴 NEVER THE USER'S settings.xml: openMSX saves settings on exit, and the
    # first run of this diag persisted `autoruncassettes false` into it (2026-10-11).
    # A throwaway copy WITHOUT any autorun line (so the default, on) is loaded
    # with -setting, and saving is switched off as well.
    alt = probe_tmp.tmp("noautorun_settings.xml")
    user = open(os.path.expanduser("~/.openMSX/share/settings.xml")).read()
    open(alt, "w").write("".join(l for l in user.splitlines(True)
                                 if "autoruncassettes" not in l))
    cmd = [OMSX, "-setting", alt, "-command", "set save_settings_on_exit false",
           "-machine", M] + pre_args + ["-cassetteplayer", cas, "-command",
                                              "set renderer none; set sound_driver null",
                                              "-script", tcl]
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    t0 = time.time()
    while p.poll() is None and time.time() - t0 < 120:
        time.sleep(0.2)
    if p.poll() is None:
        os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        return "TIMEOUT"
    return open(out).read().strip() if os.path.exists(out) else "NO OUTPUT"


for tag, a, t in (("A", [], ""), ("B", ["-command", "set autoruncassettes off"], ""),
                  ("C", [], UNARM),
                  # D: the un-arm as a -command (what a chokepoint that sees only
                  # argv can add); placed BEFORE -cassetteplayer like B
                  ("D", ["-command", UNARM.strip()], "")):
    print(tag, run(tag, a, t), flush=True)
