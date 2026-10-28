#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The program ladder (D-PROGLADDER): whole BASIC programs of the kind people
wrote in the 1980s -- games, calculators, little office tools -- run on the
reference and on zerobas, as integration tests.

Every program here is original, written for this repo. Each is a plain ASCII
listing `probes/programs/L<n>_<name>.bas`; its first line may carry

  1 REM @ANSWERS 50|25|37

the keyboard input, one INPUT answer per `|` (each typed with a RETURN). The
listing goes on an ASCII tape and openMSX's autorun loads it with RUN"CAS:", so
each machine tokenises it ITSELF. The answers are typed once the program is
running (CURLIN leaves direct mode, after the prompt has held 2 s); openMSX's `type` waits for room in the
keyboard buffer. The run is over when CURLIN is back in direct mode (the
program ended, or stopped on an error).

Two things are compared:
  * the printer log: a program LPRINTs numbered checkpoints (`CP 3 ...`), which
    never scroll away -- the first checkpoint that differs names the area;
  * the text screen at the end (row stride 40, or 32 in SCREEN 1; the prompt
    row `ZB` reads as `Ok`).
The emulated seconds each machine took are printed beside them.

Clean-room: typed keys and a tape in; the printer port, the text screen and
work-area RAM (CURLIN, TXTNAM, SCRMOD) out. No reference ROM byte is read.

  python3 -u probes/programs/run_programs.py            # every program
  python3 -u probes/programs/run_programs.py L1_guess   # some (name substring)
"""
import glob, os, signal, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import cas_encode                                    # noqa: E402
import omsx_preflight                                # noqa: E402
import probe_tmp                                     # noqa: E402
from omsx_run import _tcl_dquote                     # noqa: E402

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
REF = "Philips_VG_8020"
ZB = ["C-BIOS_MSX1_EU_REPACK_NODISK", "C-BIOS_MSX1_EU_REPACK_DISK"]
LIMIT = 900.0      # emulated seconds

TCL = r"""
set throttle off
set printerlogfilename {LOG}
plug printerport logger
after time 0.3 {
  trace remove execution cassetteplayer leave ::__zb_unarm
  set autoruncassettes on
  cassetteplayer insert {CAS}
  AUTORUN_FIX
}
proc __rd16 {a} { expr {[debug read memory $a] + 256*[debug read memory [expr {$a+1}]]} }
# phases: 0 booting (CURLIN is not yet meaningful) -> 1 the prompt held for 2 s
# (direct mode, the load is typed) -> 2 the program runs -> ended
set ::__ph 0
set ::__ff 0
proc __done {r} {
  set w [expr {[debug read memory 0xFCAF] == 1 ? 32 : 40}]
  binary scan [debug read_block VRAM [__rd16 0xF3B3] 960] a* t
  set f [open {OUT} w]
  puts $f "$r t=[format %.1f [machine_info time]] w=$w"
  puts -nonewline $f $t
  close $f; exit
}
proc __poll {} {
  if {$::__ph == 3} return
  set cl [__rd16 0xF41C]
  if {$::__ph == 0} {
    if {$cl == 0xFFFF} { incr ::__ff } else { set ::__ff 0 }
    if {$::__ff >= 20} { set ::__ph 1 }
  } elseif {$::__ph == 1 && $cl != 0xFFFF} {
    set ::__ph 2
    if {"ANSWERS" ne ""} { type "ANSWERS" }
  } elseif {$::__ph == 2 && $cl == 0xFFFF} {
    set ::__ph 3
    after time 0.5 { __done ENDED }
  }
  if {[machine_info time] > LIMIT} { __done TIMEOUT }
  after time 0.1 __poll
}
after time 0.5 __poll
"""


def answers(text):
    first = text.splitlines()[0] if text else ""
    if "@ANSWERS" not in first:
        return []
    return first.split("@ANSWERS", 1)[1].strip().split("|")


def run(machine, name, text):
    cas = probe_tmp.tmp(f"prog_{name}.cas")
    open(cas, "wb").write(cas_encode.build_cas_ascii("PROG", text))
    log = probe_tmp.tmp(f"prog_{machine}_{name}.lpt")
    out = probe_tmp.tmp(f"prog_{machine}_{name}.txt")
    tcl = probe_tmp.tmp(f"prog_{machine}_{name}.tcl")
    for p in (log, out):
        if os.path.exists(p):
            os.unlink(p)
    keys = "".join(a + "\r" for a in answers(text))
    open(tcl, "w").write(TCL.replace("AUTORUN_FIX", omsx_preflight.AUTORUN_FIX)
                         .replace("{CAS}", "{" + cas + "}").replace("{LOG}", "{" + log + "}")
                         .replace("{OUT}", "{" + out + "}").replace("LIMIT", str(LIMIT))
                         .replace('"ANSWERS"', _tcl_dquote(keys)))
    proc = subprocess.Popen(omsx_preflight.guarded(
                                [OMSX, "-machine", machine, "-command",
                                 "set renderer none; set sound_driver null", "-script", tcl]),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    deadline = time.time() + 600
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.2)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    lpt = open(log, "rb").read().decode("latin-1") if os.path.exists(log) else ""
    if not os.path.exists(out):
        return "NO OUTPUT", lpt, []
    head, _, scr = open(out, "rb").read().decode("latin-1").partition("\n")
    w = int(head.rsplit("w=", 1)[1]) if "w=" in head else 40
    rows = [scr[i:i + w].rstrip(" \0") for i in range(0, min(len(scr), 24 * w), w)]
    while rows and not rows[-1]:
        rows.pop()
    return head.rsplit(" w=", 1)[0], lpt, rows


def first_diff(a, b):
    la, lb = a.splitlines(), b.splitlines()
    # the prompt is deliberately "ZB", not "Ok" (basic/repl.asm, D-ZBCRLF)
    lb = [x.replace("ZB", "Ok") if x.strip() == "ZB" else x for x in lb]
    for i in range(max(len(la), len(lb))):
        x = la[i] if i < len(la) else "<none>"
        y = lb[i] if i < len(lb) else "<none>"
        if x != y:
            return f"line {i + 1}: ref {x!r} / zb {y!r}"
    return None


def main():
    pick = sys.argv[1:]
    progs = sorted(glob.glob(os.path.join(HERE, "L*.bas")))
    progs = [p for p in progs if not pick or any(s in os.path.basename(p) for s in pick)]
    bad = 0
    for path in progs:
        name = os.path.basename(path)[:-4]
        text = open(path).read()
        ref = run(REF, name, text)
        print(f"{name}")
        print(f"  {REF:30} {ref[0]}  lpt {len(ref[1].splitlines())} lines")
        for m in ZB:
            zb = run(m, name, text)
            d_lpt = first_diff(ref[1], zb[1])
            d_scr = first_diff("\n".join(ref[2]), "\n".join(zb[2]))
            ok = not d_lpt and not d_scr and zb[0].split()[0] == ref[0].split()[0]
            bad += not ok
            ratio = ""
            try:
                ratio = f"  x{float(zb[0].split('t=')[1]) / float(ref[0].split('t=')[1]):.2f} time"
            except (IndexError, ValueError, ZeroDivisionError):
                pass
            print(f"  {m:30} {zb[0]}  {'SAME' if ok else 'DIFFERS'}{ratio}")
            if d_lpt:
                print(f"    printer: {d_lpt}")
            if d_scr:
                print(f"    screen:  {d_scr}")
            if not ok:
                print("    ref screen:  " + " | ".join(ref[2][-6:]))
                print("    zb screen:   " + " | ".join(zb[2][-6:]))
    print(f"\n{'PASS' if not bad else 'FAIL'}: {len(progs)} program(s), {bad} divergent run(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
