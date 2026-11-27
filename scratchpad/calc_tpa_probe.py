#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-DISKRUN calculus.dsk lead: which RAM cells does CALCULUS judge the TPA by? Boots the disk on each machine, logs the
first reads of $0006-$0007 (address, time, slot state -- NO PC: the clean room forbids recording a reference PC,
so no machine's PC is recorded) and snapshots $0000-$0007, HIMEM,
$F37D-$F37F, $F341-$F344 (RAMAD) and the slots at fixed times. RAM / registers / slots only (clean room): $0000-$0007 is read only while page 0 is RAM (slot 3) --
never a reference ROM byte.
    python3 -u scratchpad/calc_tpa_probe.py [MACHINE ...]
"""
import os
import subprocess
import sys
import tempfile

machines = sys.argv[1:] or ["National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"]
for m in machines:
    td = tempfile.mkdtemp()
    d = os.path.join(td, "d.dsk")
    subprocess.run(["cp", os.path.expanduser(os.environ.get("CALC_DISK", "~/Documents/msx/msx/disks/calculus.dsk")), d], check=True)
    log = os.path.join(td, "o.txt")
    tcl = f"""set throttle off
set f [open {{{log}}} w]
set n 0
proc hx {{a k}} {{ set s ""; for {{set i 0}} {{$i < $k}} {{incr i}} {{ append s [format %02X [peek [expr {{$a+$i}}]]] }}; return $s }}
proc snap {{t}} {{ global f
  set z "ROM(not read)"; if {{([debug read ioports 0xA8] & 3) == 3 && (([peek 0xFFFF] ^ 0xFF) & 3) == 0}} {{ set z [hx 0 8] }}
  puts $f "t=$t 0000=$z HIMEM=[format %04X [peek16 0xFC4A]] F37D=[hx 0xF37D 3] RAMAD=[hx 0xF341 4] A8=[format %02X [debug read ioports 0xA8]] SS=[format %02X [expr {{[peek 0xFFFF]^0xFF}}]]"
  flush $f }}
debug set_watchpoint read_mem {{0x0006 0x0007}} {{[expr {{[machine_info time] > 3}}]}} {{
  global f n; if {{[incr n] <= 12}} {{ set w "-"; if {{([debug read ioports 0xA8] & 3) == 3 && (([peek 0xFFFF] ^ 0xFF) & 3) == 0}} {{ set w [format %04X [peek16 6]] }}; puts $f "  READ [format %04X $::wp_last_address] t=[format %.3f [machine_info time]] A8=[format %02X [debug read ioports 0xA8]] word6=$w"; flush $f }} }}
debug set_bp 0xC01E {{[expr {{([debug read ioports 0xA8] >> 6) == 3}}]}} {{ snap "C01E@[format %.3f [machine_info time]]" }}
foreach t {{5 10 15 20 30 45}} {{ after time $t "snap $t" }}
after time 46 exit
"""
    sf = os.path.join(td, "s.tcl")
    open(sf, "w").write(tcl)
    subprocess.run(["openmsx", "-machine", m, "-diska", d, "-command", "set renderer none; set sound_driver null",
                    "-script", sf], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
    print(f"== {m}")
    print(open(log).read().rstrip() if os.path.exists(log) else "<no log>")
