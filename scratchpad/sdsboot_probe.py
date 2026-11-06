#!/usr/bin/env python3
"""D-SDSBOOT (2026-11-07): what SDSNAT1C.DSK leaves on zerobas's screen -- the disk
collection's one boot regression (BOTH-RUN on 11-04 -> ZB-NOBOOT; first bad commit
ccfceefd, D-TRAPCOST). Boots the image on a machine, and at T seconds prints the
SCREEN 1 / 0 name table as text plus CURLIN / ERRLIN / ERRFLG. The software is RUN,
never decoded: only VRAM and work-area cells are read.

    DISKCORPUS_DIR=... [SDS_TRANS=1] python3 -u scratchpad/sdsboot_probe.py [machine] [T]
SDS_TRANS=1 also logs every distinct transfer of control from RAM ($8000+) into
$0000-$7FFF (interrupts excluded; PC values only, OUR machine) -- the D-BASICINT
class's tell: a program calling a fixed BASIC-ROM internal.
SDS_HOOK=1 timestamps every write to the H.TIMI hook ($FD9F..$FDA3, work area, with
the value), the first write to $9900 and its first run (no byte of it is read) --
D-SDSBOOT's race question. Works on the reference too: only RAM writes and the PC.
SDS_RING=1 (OUR machine only): the last 48 PCs (with page's primary slot) before
the first PC = $0000. SDS_A8=1: every write to the slot-select port $A8 (time, PC,
value) until then.
"""
import os, subprocess, sys, tempfile, shutil
D = os.environ["DISKCORPUS_DIR"]
img = os.path.join(D, "SDSNAT1C.DSK")
mach = sys.argv[1] if len(sys.argv) > 1 else "C-BIOS_MSX1_EU_REPACK_DISK"
T = float(sys.argv[2]) if len(sys.argv) > 2 else 45
td = tempfile.mkdtemp()
dsk = os.path.join(td, "d.dsk"); shutil.copyfile(img, dsk)
out = os.path.join(td, "o.txt")
tcl = f"""set renderer none; set sound_driver null; set throttle off
diska {{{dsk}}}
set ::lastpc 0
array set ::tr {{}}
proc __tr {{}} {{
  set pc [reg pc]
  if {{$pc < 0x8000 && $::lastpc >= 0x8000 && $pc != 0x38}} {{
    set k "[format %04X $pc] from [format %04X $::lastpc]"
    if {{![info exists ::tr($k)]}} {{ set ::tr($k) [machine_info time] }}
  }}
  set ::lastpc $pc
}}
if {{[info exists ::env(SDS_TRANS)]}} {{ debug set_condition 1 __tr }}
set ::ev {{}}
proc __hk {{}} {{ lappend ::ev "[format %.4f [machine_info time]] HOOK [format %04X $::wp_last_address] := [format %02X $::wp_last_value]" }}
proc __w99 {{}} {{ if {{![info exists ::w99]}} {{ set ::w99 1; lappend ::ev "[format %.4f [machine_info time]] FIRST WRITE 9900" }} }}
proc __x99 {{}} {{ if {{![info exists ::x99]}} {{ set ::x99 1; lappend ::ev "[format %.4f [machine_info time]] FIRST RUN 9900 (sp=[format %04X [reg sp]])" }} }}
set ::ring {{}}
proc __rg {{}} {{
  set pc [reg pc]
  if {{$pc == 0x38 && ![info exists ::i38] && [lindex [get_selected_slot 0] 0] == 3}} {{
    set ::i38 1
    lappend ::ev "[format %.4f [machine_info time]] FIRST 0038 WITH PAGE 0 = SLOT 3 after: [join $::ring {{ }}]"
  }}
  if {{$pc == 0 && ![info exists ::z0]}} {{
    set ::z0 1
    lappend ::ev "[format %.4f [machine_info time]] FIRST PC=0000 after: [join $::ring {{ }}]"
  }}
  lappend ::ring "[format %04X $pc]/[format %02X [lindex [get_selected_slot [expr {{$pc >> 14}}]] 0]]"
  if {{[llength $::ring] > 160}} {{ set ::ring [lrange $::ring end-159 end] }}
}}
if {{[info exists ::env(SDS_RING)]}} {{ debug set_condition 1 __rg }}
proc __a8 {{}} {{ if {{![info exists ::z0]}} {{ lappend ::ev "[format %.4f [machine_info time]] A8 := [format %02X $::wp_last_value] at PC=[format %04X [reg pc]] sp=[format %04X [reg sp]]" }} }}
if {{[info exists ::env(SDS_A8)]}} {{ debug set_watchpoint write_io 0xA8 1 __a8 }}
if {{[info exists ::env(SDS_HOOK)]}} {{
  debug set_watchpoint write_mem {{0xFD9F 0xFDA3}} 1 __hk
  debug set_watchpoint write_mem 0x9900 1 __w99
  debug set_bp 0x9900 1 __x99
}}
after time {T} {{
 set f [open {{{out}}} w]
 if {{[catch {{
  set scm [debug read memory 0xFCAF]
  set base [expr {{$scm == 0 ? 0 : 0x1800}}]
  set w [expr {{$scm == 0 ? 40 : 32}}]
  puts $f "SCRMOD=$scm CURLIN=[expr {{[debug read memory 0xF41C] | ([debug read memory 0xF41D]<<8)}}] ERRLIN=[expr {{[debug read memory 0xF6B3] | ([debug read memory 0xF6B4]<<8)}}] ERRFLG=[debug read memory 0xF414] PC=[format %04X [reg pc]]"
  for {{set r 0}} {{$r < 24}} {{incr r}} {{
    set s ""
    for {{set c 0}} {{$c < $w}} {{incr c}} {{
      set ch [debug read VRAM [expr {{$base + $r*$w + $c}}]]
      if {{$ch < 32 || $ch > 126}} {{set ch 46}}
      append s [format %c $ch]
    }}
    puts $f "|$s|"
  }}
 }} err]}} {{ puts $f "TCL ERROR: $err" }}
  foreach k [lsort [array names ::tr]] {{ puts $f "TRANS $k t=[format %.2f $::tr($k)]" }}
  foreach e $::ev {{ puts $f "EV $e" }}
  close $f
  exit
}}
"""
open(os.path.join(td, "s.tcl"), "w").write(tcl)
subprocess.run([shutil.which("openmsx") or "/opt/homebrew/bin/openmsx", "-machine", mach,
                "-script", os.path.join(td, "s.tcl")], timeout=1800, capture_output=True)
print(open(out).read() if os.path.exists(out) else "NO OUTPUT")
