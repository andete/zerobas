# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Boot-to-first-key latency (Joost 2026-10-09: "it takes a bit of time after
the ZB prompt till I can actually start typing").

Boots a machine, polls the text screen every 20 ms of emulated time for the
prompt (`ZB` / `Ok` at the start of a row), then taps `A` (matrix row 2, bit 6)
every 100 ms -- 50 ms down, 50 ms up -- and records when the first `A` shows on
screen. Prints t_prompt, t_echo and the gap, in emulated seconds.

Clean-room: the keyboard matrix in, the VDP name table and documented work-area
cells (SCRMOD $FCAF, TXTNAM $F3B3, T32NAM $F3BD) out.
usage: bootkey_probe.py [machine ...]
"""
import os, shutil, signal, subprocess, sys, tempfile, time

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
MACHINES = sys.argv[1:] or ["C-BIOS_MSX1_EU_BASIC", "C-BIOS_MSX1_EU_REPACK_NODISK",
                            "Philips_VG_8020"]

TCL = r"""
set throttle off
set ::t_prompt -1
set ::t_echo -1
set ::n_a 0
proc __count_a {t} { return [regexp -all {a} $t] }
proc __rd16 {a} { expr {[debug read memory $a] + 256*[debug read memory [expr {$a+1}]]} }
proc __screen {} {
  set m [debug read memory 0xFCAF]
  if {$m == 0} { set base [__rd16 0xF3B3]; set w 40 } elseif {$m == 1} { set base [__rd16 0xF3BD]; set w 32 } else { return [list $m {} 0] }
  binary scan [debug read_block VRAM $base [expr {$w*24}]] a* t
  return [list $m $t $w]
}
proc __prompt_seen {t w} {
  for {set r 0} {$r < 24} {incr r} {
    set s [string trim [string range $t [expr {$r*$w}] [expr {$r*$w+$w-1}]]]
    if {$s eq "ZB" || $s eq "Ok"} { return 1 }
  }
  return 0
}
proc __done {} {
  set f [open {OUT} w]
  puts $f "t_prompt=$::t_prompt t_echo=$::t_echo"
  close $f; exit
}
proc __poll {} {
  set now [machine_info time]
  lassign [__screen] m t w
  if {$::t_prompt < 0} {
    if {$w > 0 && [__prompt_seen $t $w]} { set ::t_prompt $now; set ::n_a [__count_a $t]; __tap }
  } elseif {[__count_a $t] > $::n_a} {
    set ::t_echo $now; __done
  }
  if {$now > 40} { __done }
  after time 0.02 __poll
}
proc __tap {} {
  keymatrixdown 2 0x40
  after time 0.05 { keymatrixup 2 0x40 }
  after time 0.1 __tap
}
after time 0.5 __poll
"""


def run(machine):
    d = tempfile.mkdtemp(prefix="bootkey_")
    out = os.path.join(d, "out.txt")
    tcl = os.path.join(d, "probe.tcl")
    open(tcl, "w").write(TCL.replace("{OUT}", "{" + out + "}"))
    proc = subprocess.Popen([OMSX, "-machine", machine, "-command",
                             "set renderer none; set sound_driver null", "-script", tcl],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    deadline = time.time() + 120
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.2)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        return "TIMEOUT"
    return open(out).read().strip() if os.path.exists(out) else "NO OUTPUT"


for m in MACHINES:
    r = run(m)
    gap = ""
    try:
        kv = dict(x.split("=") for x in r.split())
        tp, te = float(kv["t_prompt"]), float(kv["t_echo"])
        if tp >= 0 and te >= 0:
            gap = f"  gap={te - tp:.2f}s"
    except (ValueError, KeyError):
        pass
    print(f"{m:32s} {r}{gap}", flush=True)
