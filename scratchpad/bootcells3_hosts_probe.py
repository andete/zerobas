#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-BOOTCELLS step 3: which $F39A-$FD99 bytes does the VG-8020 ever change across boot + a workload?
Clean room: reads only $F39A-$FD99 RAM. Snapshots after each typed step.

    python3 scratchpad/bootcells3_hosts_probe.py MACHINE OUT.log   (then scratchpad/bootcells3_hosts_an.py OUT.log)
"""
import os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib")); sys.path.insert(0, os.path.join(ROOT, "tools"))
import omsx_preflight, openmsx_paths
machine = sys.argv[1]; out = sys.argv[2]
STEPS = [
 ("boot", ""),
 ("prog", '10 FOR I=1 TO 3:GOSUB 100:NEXT\r20 A$="X"+STR$(I):DIM B(10):READ D:DATA 5\r25 DEF FNA(X,Y)=X*Y+1:Z=FNA(2,3)\r30 PRINT A$;D;Z:END\r100 RETURN\rRUN\r'),
 ("clear", "CLEAR 300,&HC000\r"),
 ("maxf3", "MAXFILES=3\r"),
 ("maxf0", "MAXFILES=0\r"),
 ("files", "FILES\r"),
 ("play", 'PLAY "CDEFG"\r'),
 ("gfx", 'SCREEN 2:LINE(0,0)-(100,100),15:CIRCLE(50,50),20:DRAW"U10R10D10L10":PAINT(60,40):PSET(5,5):FOR I=1 TO 300:NEXT\r'),
 ("traps", 'KEY(1) ON:ON KEY GOSUB 200:ON INTERVAL=10 GOSUB 200:INTERVAL ON:ON STRIG GOSUB 200:STRIG(0) ON\r'),
 ("err", 'ON ERROR GOTO 0:PRINT 1/0\r'),
 ("run2", 'NEW\r10 ON ERROR GOTO 50\r20 ERROR 5\r50 PRINT ERR:RESUME NEXT\rRUN\r'),
 ("misc", 'PRINT FRE(0);FRE("");HEX$(PEEK(0)):A$=INKEY$:LIST\r'),
]
tcl = ["set renderer none", "set throttle off", "catch { set sound_driver null }",
       "set f [open $::env(LOGF) w]",
       "proc snap {tag} { global f; binary scan [debug read_block memory 0xF39A [expr {0xFD9A - 0xF39A}]] H* d; puts $f \"SNAP $tag $d\"; flush $f }"]
t = 12.0
for tag, text in STEPS:
    if text:
        esc = text.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("[", "\\[").replace("]", "\\]").replace("\r", "\\r")
        tcl.append(f'after time {t} {{ type "{esc}" }}')
        t += 8.0
    tcl.append(f"after time {t} {{ snap {tag} }}")
    t += 0.5
tcl.append(f"after time {t+0.5} {{ close $f; exit }}")
p = os.path.join(os.path.dirname(out), "hostprobe.tcl"); open(p, "w").write("\n".join(tcl) + "\n")
subprocess.run(omsx_preflight.guarded([openmsx_paths.find_openmsx_binary(), "-machine", machine, "-script", p]),
               env=dict(os.environ, LOGF=out), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
print(open(out).read().count("SNAP"), "snapshots")
