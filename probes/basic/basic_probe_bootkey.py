# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BOOTSCAN (gate: bootkey-acceptance): the keyboard answers as soon as the
prompt shows. Found 2026-10-09 by Joost ("it takes a bit of time after the ZB
prompt till I can actually start typing"): zerobas took its first key 2.5 s after
`ZB` appeared -- C-BIOS leaves the key-scan countdown SCNCNT at its power-on
$FF -- where the VG-8020 takes one at once.

Each machine boots; the probe polls the text screen every 20 ms of emulated
time for the prompt (`ZB` / `Ok` alone on a row), then taps `a` every 100 ms and
records when the first one shows. A row passes when the gap is <= LIMIT.

  vg8020   Philips_VG_8020               the reference -- the CONTROL: if it
                                         fails, the tap/poll apparatus is broken
  nodisk   C-BIOS_MSX1_EU_REPACK_NODISK  zerobas, no disk ROM
  disk     C-BIOS_MSX1_EU_REPACK_DISK    zerobas with its disk ROM

Prints `ROW <name> gap=<s> <PASS|FAIL>`. Exit 0 all pass; 1 a zerobas row
fails; 2 the control failed or a machine gave no reading.
Clean-room: the keyboard matrix in; the VDP name table and documented
work-area cells (SCRMOD, TXTNAM, T32NAM) out.
"""
import os, shutil, signal, subprocess, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import omsx_preflight                               # noqa: E402
import probe_tmp                                    # noqa: E402

LIMIT = 0.3
ROWS = (("vg8020", "Philips_VG_8020"), ("nodisk", "C-BIOS_MSX1_EU_REPACK_NODISK"),
        ("disk", "C-BIOS_MSX1_EU_REPACK_DISK"))

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"

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
    out = probe_tmp.tmp(f"bootkey_{machine}.txt")
    tcl = probe_tmp.tmp(f"bootkey_{machine}.tcl")
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
    return open(out).read().strip() if os.path.exists(out) else "NO OUTPUT"




def main():
    bad, blind = [], []
    for name, m in ROWS:
        r = run(m)
        try:
            kv = dict(x.split("=") for x in r.split())
            tp, te = float(kv["t_prompt"]), float(kv["t_echo"])
        except (ValueError, KeyError):
            tp = te = -1
        if tp < 0 or te < 0:
            print(f"ROW {name} gap=none ({r}) NO-READING", flush=True)
            blind.append(name)
            continue
        ok = te - tp <= LIMIT
        print(f"ROW {name} gap={te - tp:.2f}s {'PASS' if ok else 'FAIL'}", flush=True)
        if not ok:
            (blind if name == "vg8020" else bad).append(name)
    if blind:
        print(f"\nINSTRUMENT FAULT: no reading / the control failed on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: the first key is taken within {LIMIT}s of the prompt")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
