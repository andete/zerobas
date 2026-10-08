#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FDCDI, MEASURE FIRST on main: are keys typed DURING long disk work kept?

The program writes 4200 B (PRINT# x 200 + CLOSE) and POKEs &HD000 = 1 when it
starts and 2 when it is done (s10b_stopwatch.py's markers). DELAY emulated
seconds after the start, openMSX `type`s the next line through the KEY MATRIX
(not KEYBUF injection) -- `print"z"+"q"+str$(7*6)` -- so it can only arrive if
the keyboard is scanned while the disk work runs. DELAY + 30 s after the start
the screen is read: the line's output `zq 42` (which its echo cannot
contain) says it arrived whole; the echo row says how much of it survived.

    python3 -u scratchpad/fdcdi_typeahead.py [ours] [cf] [--delay=N]
"""
import os, shutil, subprocess, sys
sys.path.insert(0, "/Users/joost/projects/zerobas/probes/lib")
import probe_tmp, omsx_preflight
S = probe_tmp.tmp("")
LOOP = 'for i=1 to 200:print#1,\\"abcdefghijklmnopqrs\\":next:close#1:poke \\&hd000,2'
TYPED = 'print\\"z\\"+\\"q\\"+str\\$(7*6)\\r'   # \\$: Tcl would read $(7*6) as a variable
DELAY = next((float(a.split("=")[1]) for a in sys.argv if a.startswith("--delay=")), 3.0)


def run(machine, tag):
    dsk = probe_tmp.tmp(f"ta_{tag}.dsk")
    shutil.copyfile("/Users/joost/projects/zerobas/disk/test720.dsk", dsk)
    out = os.path.join(S, f"ta_{tag}.txt")
    if os.path.exists(out):
        os.remove(out)
    tcl = f'''set throttle off
set f [open {{{out}}} w]
set t1 0
set t2 0
proc scr {{}} {{ set b [expr {{[debug read "VDP regs" 2] * 1024}}]; set s ""; for {{set i 0}} {{$i < 960}} {{incr i}} {{ set c [debug read VRAM [expr {{$b + $i}}]]; if {{$c < 32 || $c > 126}} {{append s " "}} else {{append s [format %c $c]}} }}; return $s }}
proc fin {{}} {{ puts $::f "t=[expr {{$::t2 - $::t1}}] scr=[scr]"; close $::f; exit }}
proc poll {{}} {{
  set v [debug read memory 0xD000]
  if {{$v == 1 && $::t1 == 0}} {{ set ::t1 [machine_info time]; after time {DELAY} {{ type "{TYPED}" }}; after time [expr {{{DELAY} + 30}}] fin }}
  if {{$v == 2 && $::t2 == 0}} {{ set ::t2 [machine_info time] }}
  if {{$::t2 == 0}} {{ after time 0.02 poll }}
}}
after time 12 {{ type "\\r" }}
after time 14 {{ debug write memory 0xD000 0; type "open\\"big.txt\\" for output as #1:poke \\&hd000,1:{LOOP}\\r"; poll }}
after time 400 {{ puts $f "timeout m=[debug read memory 0xD000] scr=[scr]"; close $f; exit }}
'''
    tf = os.path.join(S, f"ta_{tag}.tcl")
    open(tf, "w").write(tcl)
    subprocess.run(omsx_preflight.guarded(["openmsx", "-machine", machine, "-diska", dsk, "-command",
                    "set renderer none; set sound_driver null; set save_settings_on_exit false",
                    "-script", tf]), capture_output=True, timeout=900)
    r = open(out).read().strip() if os.path.exists(out) else "no reading"
    ok = "zq 42" in r
    echo = r[r.find("print"):][:60] if "print" in r[r.find("scr="):] else "(no echo)"
    print(f"{tag}: delay {DELAY}s  arrived whole: {ok}  | {r[:8]}", flush=True)
    sc = r[r.find("scr=") + 4:]
    for k in range(0, len(sc), 40):
        row = sc[k:k + 40].rstrip()
        if row:
            print(f"   |{row}")


which = [a for a in sys.argv[1:] if not a.startswith("--")] or ["ours", "cf"]
if "ours" in which:
    run("C-BIOS_MSX1_EU_REPACK_DISK", "ours")
if "cf" in which:
    run("National_CF-3300", "cf")
