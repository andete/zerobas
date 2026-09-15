#!/usr/bin/env python3
"""D-WHOEVALS step 1: FIND THE INTER-SLOT STUB EMPIRICALLY on the CF-3300.

Layout (machine XML, not ROM): slot 0 = BIOS+BASIC ROM, slot 3-0 = RAM,
slot 3-1 = disk ROM (page 1).  A call from the disk ROM into main BASIC must
flip page 1's PRIMARY slot 3 -> 0 (an OUT to $A8) and the code doing so must
run from RAM.  So, per phase, count (a) every instruction fetched with
PC >= $8000 and (b) every write to port $A8 with PC and value.

Phases: idle (nothing typed), PRINT 1 (control), FROG (control, unknown word),
FILES 5 (subject, ERR 13), FILES"*.BAS" (subject, ERR 70 with no disk).
Controls MUST show no page-1 traffic to slot 3; if they do, the instrument is
measuring something else.

Clean room: reads RAM/hook cells, port writes, PC values.  No ROM bytes read.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "cf_stubfind.out")
TCL = os.path.join(HERE, "cf_stubfind.tcl")
MACHINE = "National_CF-3300"
HTIMI = 0xFD9F

PHASES = [
    ("idle",     None),
    ("print1",   "PRINT 1"),
    ("frog",     "FROG"),
    ("files5",   "FILES 5"),
    ("filesstr", 'FILES"*.BAS"'),
]
T0, GAP = 22.0, 4.0

tcl = r'''
set throttle off
set ::phase boot
array set ::ram {}
array set ::a8 {}
set ::f [open "%(out)s" w]
proc lg {s} { puts $::f $s; flush $::f }
proc onram {} {
    set k "$::phase,[format %%04X [reg PC]]"
    if {[info exists ::ram($k)]} { incr ::ram($k) } else { set ::ram($k) 1 }
}
proc ona8 {} {
    set k "$::phase,[format %%04X [reg PC]],[format %%02X $::wp_last_value]"
    if {[info exists ::a8($k)]} { incr ::a8($k) } else { set ::a8($k) 1 }
}
proc screen {} {
    # SCREEN 0 name table at VRAM 0, 40x24
    set rows {}
    for {set r 0} {$r < 24} {incr r} {
        set b [debug read_block VRAM [expr {$r*40}] 40]
        set line ""
        for {set i 0} {$i < 40} {incr i} {
            binary scan [string index $b $i] cu c
            append line [expr {($c >= 32 && $c < 127) ? [format %%c $c] : "."}]
        }
        set line [string trimright $line]
        if {$line ne ""} { lappend rows "$r:$line" }
    }
    return $rows
}
proc dumpphase {} {
    lg "== phase $::phase"
    foreach k [lsort [array names ::ram "$::phase,*"]] { lg "RAM $k $::ram($k)" }
    foreach k [lsort [array names ::a8 "$::phase,*"]] { lg "A8 $k $::a8($k)" }
    foreach r [screen] { lg "SCR $r" }
}
after time %(t0)s {
    set before [list [debug read memory %(htimi)d] [debug read memory %(htimi_1)d] [debug read memory %(htimi_2)d]]
    debug write memory %(htimi)d 201
    set after [list [debug read memory %(htimi)d] [debug read memory %(htimi_1)d] [debug read memory %(htimi_2)d]]
    lg "HTIMI before=$before after=$after"
    lg "A8 now=[format %%02X [debug read ioports 0xA8]]"
    lg "HFILE cell=[debug read memory 0xFE7B] [debug read memory 0xFE7C] [debug read memory 0xFE7D] [debug read memory 0xFE7E] [debug read memory 0xFE7F]"
    set ::cond [debug set_condition {[reg PC] >= 0x8000} { onram }]
    set ::wp [debug set_watchpoint write_io 0xA8 {} { ona8 }]
}
'''
t = T0 + 0.5
for name, text in PHASES:
    tcl += "after time %.1f { set ::phase %s" % (t, name)
    if text is not None:
        tcl += '; type "%s\\r"' % text.replace('"', '\\"')
    tcl += " }\n"
    t += GAP
    tcl += "after time %.1f { dumpphase }\n" % (t - 0.1)
tcl += "after time %.1f { lg END; close $::f; exit }\n" % (t + 0.5)

tcl = tcl % dict(out=OUT, t0=T0, htimi=HTIMI, htimi_1=HTIMI + 1, htimi_2=HTIMI + 2)
open(TCL, "w").write(tcl)
if os.path.exists(OUT):
    os.remove(OUT)
r = subprocess.run(["/opt/homebrew/bin/openmsx", "-machine", MACHINE,
                    "-command", "set renderer none; set sound_driver null",
                    "-script", TCL], capture_output=True, text=True, timeout=900)
print("openmsx rc", r.returncode)
if r.stderr.strip():
    print("stderr:", r.stderr[-2000:])
if not os.path.exists(OUT):
    print("NO READING: no output file produced")
    sys.exit(1)
print(open(OUT).read())
