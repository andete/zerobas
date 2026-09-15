#!/usr/bin/env python3
"""D-WHOEVALS step 3: WHO READS THE ARGUMENT?  (CF-3300, clean room)

cf_trace showed the FILES handler (disk ROM, page 1 = slot 3-1) switching page 1
back to slot 0 with SP DEEPER than its own frame -- a call-back, not a return --
and, for a string expression, the main ROM's H.PARD/H.NODE hooks firing inside
that call-back.  This probe asks the direct question: when the ARGUMENT's data
is read (the variable A$'s entry in the variable area, and the tokenised direct
line in KBUF/BUF), which page-1 slot is selected and how deep is SP?

  read with page 1 = slot 0   -> main BASIC reads it (call-back evaluation)
  read with page 1 = slot 3-1 -> the disk ROM reads it (own evaluation)

Phases: A$="*" (define, sets the VAR watch), PRINT A$+".BAS" (control: no
HFILE, every read from slot 0), FILES A$+".BAS", FILES 5.
All events logged only after the phase's CR (MARK) so typing noise is out.
"""
import os, re, subprocess, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "cf_whoreads2.out")
TCL = os.path.join(HERE, "cf_whoreads2.tcl")
MACHINE = "National_CF-3300"

PHASES = [
    ("define",   'A$="*"'),
    ("ctlprint", 'PRINT A$+".BAS"'),
    ("filesexp", 'FILES A$+".BAS"'),
    ("files5",   "FILES 5"),
]
T0, T1, TYPE, RUNW = 22.0, 25.0, 3.0, 3.0

tcl = r'''
set throttle off
set ::phase boot
set ::armed 0
set ::nev 0
set ::f [open "%(out)s" w]
proc lg {s} { puts $::f $s; flush $::f }
proc now {} { format %%.4f [expr {[machine_info time]}] }
proc w16 {a} { expr {[debug read memory $a] + 256*[debug read memory [expr {$a+1}]]} }
proc p1 {} { join [get_selected_slot 1] "" }
proc ev {tag body} { if {$::armed} { incr ::nev; if {$::nev < 6000} { lg "[now] $::phase $tag $body" } } }
proc rd {tag} { ev $tag "addr=[format %%04X $::wp_last_address] PC=[format %%04X [reg PC]] p1=[p1] SP=[format %%04X [reg SP]]" }
proc screen {} {
    set rows {}
    for {set r 0} {$r < 24} {incr r} {
        set b [debug read_block VRAM [expr {0x1800 + $r*32}] 32]
        set line ""
        for {set i 0} {$i < 32} {incr i} {
            binary scan [string index $b $i] cu c
            append line [expr {($c >= 32 && $c < 127) ? [format %%c $c] : "."}]
        }
        set line [string trimright $line]
        if {$line ne ""} { lappend rows "$r:$line" }
    }
    return $rows
}
proc hexdump {a n} { set s ""; for {set i 0} {$i < $n} {incr i} { append s [format %%02X [debug read memory [expr {$a+$i}]]] " " }; return $s }
proc dumpphase {} {
    lg "== end phase $::phase nev=$::nev"
    lg "KBUF F41F: [hexdump 0xF41F 16]"
    lg "BUF  F55E: [hexdump 0xF55E 32]"
    foreach r [screen] { lg "SCR $r" }
    set ::armed 0; set ::nev 0
}
proc setvarwatch {} {
    set vt [w16 0xF6C2]; set at [w16 0xF6C4]; set se [w16 0xF6C6]
    lg "VARTAB=[format %%04X $vt] ARYTAB=[format %%04X $at] STREND=[format %%04X $se]"
    if {$at <= $vt || $at - $vt > 64} { lg "VAR AREA IMPLAUSIBLE -- no var watch"; return }
    set bytes {}
    for {set a $vt} {$a < $at} {incr a} { lappend bytes [format %%02X [debug read memory $a]] }
    lg "var entry bytes: $bytes"
    debug set_watchpoint read_mem [list $vt [expr {$at-1}]] {} { rd VAR }
    # MSX string var entry: type(3) name name len lo hi -> body pointer at +4
    set len [debug read memory [expr {$vt+3}]]; set body [w16 [expr {$vt+4}]]
    lg "A\$ descriptor len=$len body=[format %%04X $body] body byte=[format %%02X [debug read memory $body]]"
    debug set_watchpoint read_mem $body {} { rd BODY }
}
after time %(t0)s { type "\r" }
after time %(t1)s {
    lg "t1 screen (expect Ok):"; foreach r [screen] { lg "SCR $r" }
    set before [list [debug read memory 0xFD9F] [debug read memory 0xFDA0]]
    debug write memory 0xFD9F 201
    set after [list [debug read memory 0xFD9F] [debug read memory 0xFDA0]]
    lg "HTIMI before=$before after=$after"
    lg "A8=[format %%02X [debug read ioports 0xA8]] page1=[p1]"
    lg "HFILE cell=[debug read memory 0xFE7B] [debug read memory 0xFE7C] [debug read memory 0xFE7D] [debug read memory 0xFE7E] [debug read memory 0xFE7F]"
    debug set_bp 0xFE7B {} { ev HFILE "SP=[format %%04X [reg SP]]" }
    debug set_bp 0x0030 {} { ev RST30 "caller=[format %%04X [w16 [reg SP]]] SP=[format %%04X [reg SP]] p1=[p1]" }
    debug set_bp 0x001C {} { ev CALSLT "IX=[format %%04X [reg IX]] IYh=[format %%02X [expr {[reg IY]>>8}]] SP=[format %%04X [reg SP]] p1=[p1]" }
    debug set_watchpoint write_io 0xA8 {} { if {[reg PC] >= 0xF380 && [reg PC] < 0xF3A0} { ev SWITCH "PC=[format %%04X [reg PC]] val=[format %%02X $::wp_last_value] p1bits=[expr {($::wp_last_value>>2)&3}] SP=[format %%04X [reg SP]]" } }
    debug set_watchpoint read_mem {0xF41F 0xF55D} {} { rd KBUF }
    debug set_watchpoint read_mem {0xF55E 0xF65F} {} { rd BUF }
}
'''
t = T1 + 0.5
for i, (name, text) in enumerate(PHASES):
    tcl += 'after time %.1f { set ::phase %s; type "%s" }\n' % (t, name, text.replace('"', '\\"'))
    t += TYPE
    tcl += 'after time %.1f { set ::armed 1; ev MARK "CR"; type "\\r" }\n' % t
    t += RUNW
    tcl += "after time %.1f { dumpphase%s }\n" % (t - 0.1, "; setvarwatch" if i == 0 else "")
tcl += "after time %.1f { lg END; close $::f; exit }\n" % (t + 0.5)
tcl = tcl % dict(out=OUT, t0=T0, t1=T1)
open(TCL, "w").write(tcl)
if os.path.exists(OUT):
    os.remove(OUT)
r = subprocess.run(["/opt/homebrew/bin/openmsx", "-machine", MACHINE,
                    "-command", "set renderer none; set sound_driver null",
                    "-script", TCL], capture_output=True, text=True, timeout=1200)
print("openmsx rc", r.returncode)
if r.stderr.strip():
    print("stderr:", r.stderr[-2000:])
if not os.path.exists(OUT):
    print("NO READING: no output file produced")
    sys.exit(1)

# ---- compress: runs of same (tag, p1) become one line with addr range + SP range
EV = re.compile(r"^(\S+) (\S+) (\S+) (.*)$")
lines = open(OUT).read().splitlines()
for ln in lines:
    if not EV.match(ln) or ln.startswith("=="):
        pass
run = None
def flush():
    global run
    if run:
        t, ph, tag, p1, n, lo, hi, splo, sphi, pcs = run
        print(f"  {t} {ph:8} {tag:6} x{n:<4} addr {lo:04X}..{hi:04X} p1={p1} SP {splo:04X}..{sphi:04X} PCs {','.join(sorted(pcs)[:6])}{'...' if len(pcs)>6 else ''}")
    run = None
for ln in lines:
    m = EV.match(ln)
    if not m or not re.match(r"^\d", ln):
        flush(); print(ln); continue
    t, ph, tag, body = m.groups()
    f = dict(kv.split("=", 1) for kv in body.split() if "=" in kv)
    if tag in ("VAR", "BODY", "KBUF", "BUF"):
        a, sp, pc = int(f["addr"], 16), int(f["SP"], 16), f["PC"]
        if run and run[1] == ph and run[2] == tag and run[3] == f["p1"]:
            run[4] += 1; run[5] = min(run[5], a); run[6] = max(run[6], a)
            run[7] = min(run[7], sp); run[8] = max(run[8], sp); run[9].add(pc)
        else:
            flush(); run = [t, ph, tag, f["p1"], 1, a, a, sp, sp, {pc}]
    else:
        flush(); print("  " + ln)
flush()
