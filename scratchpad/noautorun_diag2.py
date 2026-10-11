#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""noautorun_diag.py found the un-arm works for a tape mounted with
`-cassetteplayer`; lnblank-say then autoran anyway, because it mounts the tape
from its Tcl prologue (`cassetteplayer insert`), after startup. ~40 sites in
the tree insert from Tcl. Does an execution TRACE on `cassetteplayer`,
installed by one startup -command, un-arm every insertion?

  A  argv tape, nothing                        (control: autoruns)
  E  script insert at t=0, nothing             (control: autoruns)
  G  argv tape + the startup hook              -> quiet
  H  script insert + the startup hook          -> quiet
  I  script insert + hook, the script removes the trace first -> PREDICTED
     autoruns, MISSED: quiet (the script runs before the -commands)
  J  as I, but the removal and insertion run 0.3 s in -> autoruns (what the
     autorun gate does, since it NEEDS autorun)

Isolated from the user's openMSX settings: a throwaway copy via -setting,
saving off, and the user's file hashed before and after. Clean room: our own
tape and the screen.
"""
import hashlib, os, shutil, signal, subprocess, sys, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import probe_tmp                                    # noqa: E402
import cas_encode                                   # noqa: E402

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
M = "C-BIOS_MSX1_EU_REPACK_NODISK"
HOOK = ("proc ::__zb_unarm {args} { if {[info exists ::openmsx::auto_run_bp]} "
        "{ debug remove_bp $::openmsx::auto_run_bp; unset ::openmsx::auto_run_bp } }; "
        "trace add execution cassetteplayer leave ::__zb_unarm; ::__zb_unarm")
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
USER = os.path.expanduser("~/.openMSX/share/settings.xml")


def run(tag, argv_tape, hook, pre):
    cas = probe_tmp.tmp("noautorun2.cas")
    open(cas, "wb").write(cas_encode.build_cas_ascii("X", '10 PRINT"HI"\n'))
    out, tcl = probe_tmp.tmp(f"noautorun2_{tag}.txt"), probe_tmp.tmp(f"noautorun2_{tag}.tcl")
    alt = probe_tmp.tmp("noautorun2_settings.xml")
    open(alt, "w").write("".join(l for l in open(USER).read().splitlines(True)
                                 if "autoruncassettes" not in l))
    if os.path.exists(out):
        os.unlink(out)
    open(tcl, "w").write(TCL.replace("PRE", pre.replace("{CAS}", "{" + cas + "}"))
                         .replace("{OUT}", "{" + out + "}"))
    cmd = [OMSX, "-setting", alt, "-command", "set save_settings_on_exit false",
           "-machine", M]
    if hook:
        cmd += ["-command", HOOK]
    if argv_tape:
        cmd += ["-cassetteplayer", cas]
    cmd += ["-command", "set renderer none; set sound_driver null", "-script", tcl]
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    t0 = time.time()
    while p.poll() is None and time.time() - t0 < 120:
        time.sleep(0.2)
    if p.poll() is None:
        os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        return "TIMEOUT"
    return open(out).read().strip() if os.path.exists(out) else "NO OUTPUT"


before = hashlib.sha256(open(USER, "rb").read()).hexdigest()
INS = "cassetteplayer insert {CAS}"
for tag, argv_tape, hook, pre in (
        ("A", True, False, ""), ("E", False, False, INS),
        ("G", True, True, ""), ("H", False, True, INS),
        ("I", False, True, "trace remove execution cassetteplayer leave ::__zb_unarm\n" + INS),
        # J: I MISSED (quiet) -- -script evidently runs BEFORE the -commands, so
        # the hook's closing direct un-arm cleared I's insertion. J inserts 0.3 s
        # in (still long before the first prompt), after the hook has run.
        ("J", False, True, "after time 0.3 { trace remove execution cassetteplayer leave "
                           "::__zb_unarm; " + INS + " }")):
    print(tag, run(tag, argv_tape, hook, pre), flush=True)
after = hashlib.sha256(open(USER, "rb").read()).hexdigest()
print("user settings", "UNTOUCHED" if before == after else "CHANGED -- STOP")
