# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-STOPKEY3 (2026-11-06): after a Ctrl-STOP break, is a ^C (3) left in the
keyboard buffer? Found by typed session S2_stopcont: INKEY$ read 3 after CONT on the
VG-8020 and nothing here. A program `10 GOTO 10` is stopped with Ctrl-STOP held
for HOLD s (keyboard matrix); then GETPNT / PUTPNT ($F3FA / $F3F8) and the 40-byte
KEYBUF ($FBF0) are read, at 0.1 s steps. Work-area RAM only (clean-room)."""
import os, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import omsx_preflight, probe_tmp  # noqa: E402
from omsx_repl import key_proc  # noqa: E402
import run_programs as rp  # noqa: E402

HOLD = float(next((a.split("=")[1] for a in sys.argv if a.startswith("--hold=")), "0.2"))
# --noctrl: STOP alone (no CTRL); --prog="<line>\r<line>": the program typed instead of
# `10 GOTO 10` (e.g. an ON STOP GOSUB handler) -- D-STOPKEY3's two open questions.
NOCTRL = "--noctrl" in sys.argv
PROG = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--prog=")), "10 GOTO 10")
TCL = r"""
set throttle off
KEYPROC
proc __rd16 {a} { expr {[debug read memory $a] + 256*[debug read memory [expr {$a+1}]]} }
set ::__f [open {OUT} w]
proc __dump {tag} {
  set b ""
  for {set i 0} {$i < 40} {incr i} { append b [format %02X [debug read memory [expr {0xFBF0+$i}]]] }
  puts $::__f "$tag t=[format %.2f [machine_info time]] GET=[format %04X [__rd16 0xF3FA]] PUT=[format %04X [__rd16 0xF3F8]] CURLIN=[format %04X [__rd16 0xF41C]] BUF=$b"
  flush $::__f
}
PROGKEYS
after time 9 { __key "RUN\r" }
proc __kw {} { puts $::__f "KBWRITE t=[format %.4f [machine_info time]] addr=[format %04X $::wp_last_address] val=[format %02X $::wp_last_value]"; flush $::__f }
after time 9.9 { debug set_watchpoint write_mem {0xFBF0 0xFC17} {} __kw }
after time 10 { __dump RUNNING; CTRLDOWN keymatrixdown 7 0x10 }
after time [expr {10 + HOLD}] { keymatrixup 7 0x10; CTRLUP __dump RELEASED }
for {set k 1} {$k <= 10} {incr k} { after time [expr {10 + HOLD + 0.1*$k}] [list __dump +$k] }
after time 12.5 { close $::__f; exit }
"""
for m in (rp.REF, rp.ZB[0]):
    out = probe_tmp.tmp(f"stopkey_{m}.txt")
    tcl = probe_tmp.tmp(f"stopkey_{m}.tcl")
    open(tcl, "w").write(TCL.replace("{OUT}", "{" + out + "}").replace("KEYPROC", key_proc())
                         .replace("HOLD", str(HOLD)).replace("PROGKEYS", "\n".join(f'after time {5.0 + 0.6 * i:.1f} {{ __key "{ln}\\r" }}' for i, ln in enumerate(PROG.split("|"))))
                         .replace("CTRLDOWN", "" if NOCTRL else "keymatrixdown 6 0x02;")
                         .replace("CTRLUP", "" if NOCTRL else "keymatrixup 6 0x02;"))
    subprocess.run(omsx_preflight.guarded([rp.OMSX, "-machine", m, "-command",
                   "set renderer none; set sound_driver null", "-script", tcl]),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
    print(f"== {m} (hold {HOLD} s{', STOP alone' if NOCTRL else ''}; program {PROG!r})")
    for line in open(out):
        if line.startswith("KBWRITE"):
            print("  " + line.strip())
            continue
        tag, rest = line.split(" ", 1)
        f = dict(x.split("=") for x in rest.split())
        g, p = int(f["GET"], 16), int(f["PUT"], 16)
        pend = []
        i = g
        while i != p and len(pend) < 40:
            pend.append(f["BUF"][2 * (i - 0xFBF0):2 * (i - 0xFBF0) + 2])
            i = 0xFBF0 if i + 1 >= 0xFBF0 + 40 else i + 1
        print(f"  {tag:9} t={f['t']} CURLIN={f['CURLIN']} pending={' '.join(pend) or '-'}")
