#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The program ladder (D-PROGLADDER): whole BASIC programs of the kind people
wrote in the 1980s -- games, calculators, little office tools -- run on the
reference and on zerobas, as integration tests.

Every program here is original, written for this repo. Each is a plain ASCII
listing `probes/programs/L<n>_<name>.bas`; its first line may carry

  1 REM @ANSWERS 50|25|37

(with `@DISK` on that line, the program runs against the CF-3300 and on the DISK
target only, each with a private copy of disk/empty720.dsk) the keyboard input, one INPUT answer per `|` (each typed with a RETURN). The
listing goes on an ASCII tape and openMSX's autorun loads it with RUN"CAS:", so
each machine tokenises it ITSELF. Once the program runs (CURLIN leaves direct
mode, after the prompt has held 2 s) the answers are typed ONE AT A TIME, each
straight into an empty keyboard buffer (omsx_repl.key_proc, the project's
injector), once the program has stayed on one line for 0.5 s (it waits in
INPUT). Not openMSX's `type`: it holds each key for a fixed 1/15 s and never
waits, so a key pressed during a long interrupt-off stretch is lost -- the L5
draft lost keys on BOTH machines after disk I/O (FDC gaps up to 202 ms on the
CF-3300); D-GCDI's gate still types with `type`, ON PURPOSE, because a lost key
is what it measures. The run is over when CURLIN is back in direct mode (the
program ended, or stopped on an error).

Two things are compared:
  * the printer log: a program LPRINTs numbered checkpoints (`CP 3 ...`), which
    never scroll away -- the first checkpoint that differs names the area;
  * the text screen at the end (SCREEN 0's TXTNAM, row stride 40, or SCREEN 1's T32NAM,
    stride 32; the prompt
    row `ZB` reads as `Ok`).
The emulated seconds each machine took are printed beside them. With `--gaps`
(the gate runs that way) a JIFFY watchpoint also counts frame-interrupt gaps
(> 30 ms): where the reference has none, zerobas may have none; where it has
some (disk I/O), no zerobas gap may be longer than its longest (D-GCDI).

Clean-room: typed keys and a tape in; the printer port, the text screen and
work-area RAM (CURLIN, TXTNAM / T32NAM, SCRMOD) out. No reference ROM byte is read.

  python3 -u probes/programs/run_programs.py            # every program
  python3 -u probes/programs/run_programs.py L1_guess   # some (name substring)
  ... --keep DIR    # keep each run's printer log (.lpt) and screen (.scr) in DIR
  ... --gaps        # also report frame-interrupt gaps (see GAP_TCL)
"""
import glob, os, shutil, signal, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import cas_encode                                    # noqa: E402
import omsx_preflight                                # noqa: E402
import probe_tmp                                     # noqa: E402
from omsx_run import _tcl_dquote                     # noqa: E402
from omsx_repl import key_proc                       # noqa: E402

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
REF = "Philips_VG_8020"
ZB = ["C-BIOS_MSX1_EU_REPACK_NODISK", "C-BIOS_MSX1_EU_REPACK_DISK"]
# a program whose line 1 says `@DISK` needs a drive: the CF-3300 is the reference
# and only the DISK target runs, each with its own copy of disk/empty720.dsk (no MSX-DOS on it, so both boot to BASIC)
DISK_REF = "National_CF-3300"
DISK_ZB = ["C-BIOS_MSX1_EU_REPACK_DISK"]
LIMIT = 900.0      # emulated seconds
KEEP = None        # --keep DIR: copy each run's printer log and screen there

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
GAPWATCH
KEYPROC
proc __rd16 {a} { expr {[debug read memory $a] + 256*[debug read memory [expr {$a+1}]]} }
# phases: 0 booting (CURLIN is not yet meaningful) -> 1 the prompt held for 2 s
# (direct mode, the load is typed) -> 2 the program runs -> ended
set ::__ph 0
set ::__keys [list ANSWERS]
set ::__next 0
set ::__cl -1
set ::__clt 0
set ::__ff 0
proc __done {r} {
  set w [expr {[debug read memory 0xFCAF] == 1 ? 32 : 40}]
  set nam [expr {[debug read memory 0xFCAF] == 1 ? [__rd16 0xF3BD] : [__rd16 0xF3B3]}]
  binary scan [debug read_block VRAM $nam 960] a* t
  set f [open {OUT} w]
  puts $f "$r t=[format %.1f [machine_info time]] GAPOUT w=$w"
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
  }
  # one answer at a time: only into an EMPTY keyboard buffer (GETPNT == PUTPNT)
  # and after the previous answer's `type` is done (15 Hz, a release between
  # repeated keys: <= 2/15 s a key) -- a 39-key buffer never overflows
  # ... and only once CURLIN has held one line for 0.5 s (the program waits in
  # INPUT): a key-wait that also keeps answers out of a busy stretch
  if {$cl != $::__cl} { set ::__cl $cl; set ::__clt [machine_info time] }
  if {$::__ph == 2 && [llength $::__keys] > 0 && [machine_info time] >= $::__next
      && [machine_info time] - $::__clt >= 0.5
      && [__rd16 0xF3FA] == [__rd16 0xF3F8]} {
    set k [lindex $::__keys 0]
    set ::__keys [lrange $::__keys 1 end]
    TYPECMD $k
    set ::__next [expr {[machine_info time] + 0.3}]
  }
  if {$::__ph == 2 && $cl == 0xFFFF} {
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


# gaps=True: a write watchpoint on JIFFY ($FC9E, the frame ISR's counter) while the
# program runs; the result head gains `gaps=N max=S` -- how many frame-to-frame
# intervals exceeded 30 ms (one frame is 20 ms) and the longest. A key `type`d by
# openMSX is held 1/15 s, so a gap past ~66 ms can lose it (D-GCDI).
GAP_TCL = r"""
set ::__jt 0
set ::__jrun 0
set ::__gaps {}
proc __jw {} {
  # both ends of an interval must be inside the run (CURLIN out of direct mode),
  # decided HERE per write: the polled phase lags by up to 0.1 s, and a gap that
  # straddled that switch went uncounted (L2_adven's 90 ms READ scan, D-GCDI3)
  set t [machine_info time]
  set run [expr {$::__ph >= 1 && [__rd16 0xF41C] != 0xFFFF}]
  if {$run && $::__jrun} {
    set g [expr {$t - $::__jt}]
    if {$g > 0.03} { lappend ::__gaps [format %.3f $g] }
  }
  set ::__jt $t
  set ::__jrun $run
}
debug set_watchpoint write_mem 0xFC9E {} __jw
"""
GAP_OUT = "gaps=[llength $::__gaps] max=[expr {[llength $::__gaps] ? [lindex [lsort -real -decreasing $::__gaps] 0] : 0}]"


# A data disk in the drive makes the disk ROM ask `Enter date` at power-on, on the
# CF-3300 as on zerobas: answer it with RETURN, early, before the BASIC prompt.
DATE_TCL = r"""
after time 6 { type "\r" }
after time 10 { type "\r" }
"""


def needs_disk(text):
    return "@DISK" in (text.splitlines()[0] if text else "")


def run(machine, name, text, gaps=False, typing="inject"):
    """typing="inject": answers go into KEYBUF (key_proc) and cannot be lost;
    typing="type": openMSX's `type`, a real 1/15 s key press per character --
    for a gate whose subject IS whether a pressed key gets seen (gcdi)."""
    cas = probe_tmp.tmp(f"prog_{name}.cas")
    open(cas, "wb").write(cas_encode.build_cas_ascii("PROG", text))
    log = probe_tmp.tmp(f"prog_{machine}_{name}.lpt")
    out = probe_tmp.tmp(f"prog_{machine}_{name}.txt")
    tcl = probe_tmp.tmp(f"prog_{machine}_{name}.tcl")
    for p in (log, out):
        if os.path.exists(p):
            os.unlink(p)
    keys = " ".join(_tcl_dquote(a + "\r") for a in answers(text))
    open(tcl, "w").write(TCL.replace("AUTORUN_FIX", omsx_preflight.AUTORUN_FIX)
                         .replace("{CAS}", "{" + cas + "}").replace("{LOG}", "{" + log + "}")
                         .replace("{OUT}", "{" + out + "}").replace("LIMIT", str(LIMIT))
                         .replace("ANSWERS", keys)
                         .replace("KEYPROC", key_proc())
                         .replace("TYPECMD", "__key" if typing == "inject" else "type")
                         .replace("GAPWATCH", (GAP_TCL if gaps else "") +
                                  (DATE_TCL if needs_disk(text) else ""))
                         .replace("GAPOUT", GAP_OUT if gaps else ""))
    cmd = [OMSX, "-machine", machine, "-command",
           "set renderer none; set sound_driver null", "-script", tcl]
    if needs_disk(text):
        dsk = probe_tmp.tmp(f"prog_{machine}_{name}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "empty720.dsk"), dsk)
        cmd += ["-diska", dsk]
    proc = subprocess.Popen(omsx_preflight.guarded(cmd),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    deadline = time.time() + 600
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.2)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    lpt = open(log, "rb").read().decode("latin-1") if os.path.exists(log) else ""
    if KEEP:
        os.makedirs(KEEP, exist_ok=True)
        for src, ext in ((log, "lpt"), (out, "scr")):
            if os.path.exists(src):
                open(os.path.join(KEEP, f"{name}.{machine}.{ext}"), "wb").write(open(src, "rb").read())
    if not os.path.exists(out):
        return "NO OUTPUT", lpt, []
    head, _, scr = open(out, "rb").read().decode("latin-1").partition("\n")
    w = int(head.rsplit("w=", 1)[1]) if "w=" in head else 40
    rows = [scr[i:i + w].rstrip(" \0") for i in range(0, min(len(scr), 24 * w), w)]
    while rows and not rows[-1]:
        rows.pop()
    return " ".join(head.rsplit(" w=", 1)[0].split()), lpt, rows


# Programs whose zerobas run is KNOWN to have more frame-interrupt gaps than the
# reference, by a filed item: the gap rule reports them KNOWN instead of failing,
# and fails once they come back clean on EVERY target (so the entry cannot outlive
# its fix; one target can be clean while another is not).
KNOWN_GAPS = {
    # D-GCDI5 emptied this, then D-LATEINT (2026-10-29) closed L4_errors' entry: an
    # error raised through sub2's p0cb skipped sr_slot's `ei`, and the ON ERROR
    # handler ran under DI.
}


def _maxgap(head):
    return float(head.split("max=")[1].split()[0]) if "max=" in head else 99.0


def _gaps(head):
    return int(head.split("gaps=")[1].split()[0]) if "gaps=" in head else 10 ** 6


def _prompt(x, ref):
    if x.strip() == "ZB":                     # the prompt on a line of its own
        return x.replace("ZB", "Ok")
    k = len(x) - len(x.lstrip())              # the screen rows keep their indent
    if x[k:k + 2] == "ZB" and ref[:k] == x[:k] and ref[k:k + 2] == "Ok" and ref[k + 2:] == x[k + 2:]:
        return ref                            # drawn over a line the program filled
    return x


def first_diff(a, b):
    la, lb = a.splitlines(), b.splitlines()
    # the prompt is deliberately "ZB", not "Ok" (basic/repl.asm, D-ZBCRLF) -- a
    # line of its own, or drawn over the start of a line the program filled
    # (L4_machine's FILVRM row: `ZB####...` where the reference has `Ok####...`;
    # only where the reference's line starts `Ok` at the same place)
    lb = [_prompt(x, la[i] if i < len(la) else "") for i, x in enumerate(lb)]
    for i in range(max(len(la), len(lb))):
        x = la[i] if i < len(la) else "<none>"
        y = lb[i] if i < len(lb) else "<none>"
        if x != y:
            return f"line {i + 1}: ref {x!r} / zb {y!r}"
    return None


def main():
    global KEEP
    args = sys.argv[1:]
    if "--keep" in args:
        i = args.index("--keep")
        KEEP = args[i + 1]
        del args[i:i + 2]
    gaps = "--gaps" in args
    pick = [a for a in args if a != "--gaps"]
    # L* 80s-style programs, C* contest algorithms, G* hobbyist game-contest style
    progs = sorted(glob.glob(os.path.join(HERE, "[LCG]*.bas")))
    progs = [p for p in progs if not pick or any(s in os.path.basename(p) for s in pick)]
    bad = 0
    for path in progs:
        name = os.path.basename(path)[:-4]
        text = open(path).read()
        ref_m, zbs = (DISK_REF, DISK_ZB) if needs_disk(text) else (REF, ZB)
        any_more = False
        ref = run(ref_m, name, text, gaps)
        print(f"{name}")
        print(f"  {ref_m:30} {ref[0]}  lpt {len(ref[1].splitlines())} lines")
        for m in zbs:
            zb = run(m, name, text, gaps)
            d_lpt = first_diff(ref[1], zb[1])
            d_scr = first_diff("\n".join(ref[2]), "\n".join(zb[2]))
            ok = not d_lpt and not d_scr and zb[0].split()[0] == ref[0].split()[0]
            note = ""
            if gaps:   # no more frame-interrupt gaps than the reference (D-GCDI)
                # the reference has no gaps: zerobas may have none either. It has
                # some (disk I/O holds DI on the CF-3300 too): the COUNT swings with
                # disk timing (L5_stock: 18, then 35, against 34), so the bound is
                # its LONGEST gap -- no zerobas gap may be longer.
                if _gaps(ref[0]) == 0:
                    more = _gaps(zb[0]) > 0
                else:
                    more = _maxgap(zb[0]) > _maxgap(ref[0])
                if name in KNOWN_GAPS:
                    any_more = any_more or more
                    note = f"  (gaps KNOWN: {KNOWN_GAPS[name]})" if more else \
                        "  (gaps clean on this target)"
                else:
                    ok = ok and not more
            bad += not ok
            ratio = ""
            try:
                ratio = f"  x{float(zb[0].split('t=')[1]) / float(ref[0].split('t=')[1]):.2f} time"
            except (IndexError, ValueError, ZeroDivisionError):
                pass
            print(f"  {m:30} {zb[0]}  {'SAME' if ok else 'DIFFERS'}{ratio}{note}")
            if d_lpt:
                print(f"    printer: {d_lpt}")
            if d_scr:
                print(f"    screen:  {d_scr}")
            if not ok:
                print("    ref screen:  " + " | ".join(ref[2][-6:]))
                print("    zb screen:   " + " | ".join(zb[2][-6:]))
        if gaps and name in KNOWN_GAPS and not any_more:
            bad += 1   # a KNOWN entry must not outlive its fix
            print(f"  gaps now clean on every target: remove KNOWN_GAPS[{name!r}]")
    print(f"\n{'PASS' if not bad else 'FAIL'}: {len(progs)} program(s), {bad} divergent run(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
