#!/usr/bin/env python3
"""D-WHOEVALS step 2: ORDERED inter-slot trace on the CF-3300 while FILES is live.

Slot layout (machine XML): slot 0 = BIOS+BASIC ROM (pages 0,1); 3-0 = RAM;
3-1 = disk ROM (page 1).  Disk ROM -> main BASIC page 1 needs page 1's PRIMARY
to go 3 -> 0: an OUT ($A8) whose page-1 bits change.  We log, in ORDER with an
emulated timestamp:
  HFILE  bp $FE7B (H_FILE hook cell executing its CALLF): SP
  RST30  bp $0030 (public CALLF entry): caller = word at (SP), SP
  CALSLT bp $001C (public CALSLT entry): IX, IYh, SP, caller
  CLPRIM bp $F38C (RAM stub, found empirically in cf_stubfind): A, SP
  A8     write_io $A8: PC, value, page-1 primary bits, secondary reg (~$FFFF), SP
  MARK   just before the CR of a phase is typed
plus per-phase counts of every PC >= $8000 (RAM execution map) and the screen.

🔴 cf_stubfind typed into the DISK ROM'S DATE PROMPT (t=22 is not BASIC yet):
the first thing this does is answer it and CHECK the screen says Ok.

Clean room: RAM, ports, registers and PCs only.  No ROM byte is read.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "cf_trace.out")
TCL = os.path.join(HERE, "cf_trace.tcl")
MACHINE = "National_CF-3300"

PHASES = [
    ("idle",     None),
    ("print1",   "PRINT 1"),
    ("frog",     "FROG"),
    ("files5",   "FILES 5"),
    ("filesexp", 'A$="*":FILES A$+".BAS"'),
]
T0 = 22.0          # date prompt showing
T1 = 25.0          # BASIC prompt expected; install instruments
TYPE, RUNW = 3.0, 3.0

tcl = r'''
set throttle off
set ::phase boot
array set ::ram {}
set ::f [open "%(out)s" w]
proc lg {s} { puts $::f $s; flush $::f }
proc now {} { format %%.4f [expr {[machine_info time]}] }
proc w16 {a} { expr {[debug read memory $a] + 256*[debug read memory [expr {$a+1}]]} }
proc onram {} {
    set k "$::phase,[format %%04X [reg PC]]"
    if {[info exists ::ram($k)]} { incr ::ram($k) } else { set ::ram($k) 1 }
}
proc ev {tag body} { lg "[now] $::phase $tag $body" }
proc sec {} { expr {(~[debug read memory 0xFFFF]) & 0xFF} }
proc screen {} {
    set rows {}
    foreach {base cols} {0x1800 32 0x0000 40} {
        for {set r 0} {$r < 24} {incr r} {
            set b [debug read_block VRAM [expr {$base + $r*$cols}] $cols]
            set line ""
            for {set i 0} {$i < $cols} {incr i} {
                binary scan [string index $b $i] cu c
                append line [expr {($c >= 32 && $c < 127) ? [format %%c $c] : "."}]
            }
            set line [string trimright $line]
            if {$line ne ""} { lappend rows "[format %%04X $base]/$r:$line" }
        }
    }
    return $rows
}
proc dumpphase {} {
    lg "== end phase $::phase"
    foreach k [lsort [array names ::ram "$::phase,*"]] { lg "RAM $k $::ram($k)" }
    foreach r [screen] { lg "SCR $r" }
}
after time %(t0)s { lg "t0 screen:"; foreach r [screen] { lg "SCR $r" }; type "\r" }
after time %(t1)s {
    lg "t1 screen (expect Ok):"; foreach r [screen] { lg "SCR $r" }
    set before [list [debug read memory 0xFD9F] [debug read memory 0xFDA0] [debug read memory 0xFDA1]]
    debug write memory 0xFD9F 201
    set after [list [debug read memory 0xFD9F] [debug read memory 0xFDA0] [debug read memory 0xFDA1]]
    lg "HTIMI before=$before after=$after"
    lg "A8=[format %%02X [debug read ioports 0xA8]] sec=[format %%02X [sec]] page1=[get_selected_slot 1]"
    lg "HFILE cell=[debug read memory 0xFE7B] [debug read memory 0xFE7C] [debug read memory 0xFE7D] [debug read memory 0xFE7E] [debug read memory 0xFE7F]"
    debug set_condition {[reg PC] >= 0x8000} { onram }
    debug set_bp 0xFE7B {} { ev HFILE "SP=[format %%04X [reg SP]]" }
    debug set_bp 0x0030 {} { ev RST30 "caller=[format %%04X [w16 [reg SP]]] SP=[format %%04X [reg SP]] p1=[get_selected_slot 1]" }
    debug set_bp 0x001C {} { ev CALSLT "IX=[format %%04X [reg IX]] IYh=[format %%02X [expr {[reg IY]>>8}]] SP=[format %%04X [reg SP]] caller=[format %%04X [w16 [reg SP]]] p1=[get_selected_slot 1]" }
    debug set_bp 0xF38C {} { ev CLPRIM "A=[format %%02X [reg A]] SP=[format %%04X [reg SP]] caller=[format %%04X [w16 [reg SP]]]" }
    debug set_watchpoint write_io 0xA8 {} { ev A8 "PC=[format %%04X [reg PC]] val=[format %%02X $::wp_last_value] p1bits=[expr {($::wp_last_value>>2)&3}] sec=[format %%02X [sec]] SP=[format %%04X [reg SP]]" }
}
'''
t = T1 + 0.5
for name, text in PHASES:
    tcl += "after time %.1f { set ::phase %s" % (t, name)
    if text is not None:
        tcl += '; type "%s"' % text.replace('"', '\\"')
    tcl += " }\n"
    t += TYPE
    tcl += 'after time %.1f { ev MARK "CR"; type "\\r" }\n' % t
    t += RUNW
    tcl += "after time %.1f { dumpphase }\n" % (t - 0.1)
tcl += "after time %.1f { lg END; close $::f; exit }\n" % (t + 0.5)

tcl = tcl % dict(out=OUT, t0=T0, t1=T1)
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
