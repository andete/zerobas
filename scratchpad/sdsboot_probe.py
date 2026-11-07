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
value) until then. SDS_BOOT=1: registers, slots and a few work-area cells (DRVINF,
the RAM slot ids, EXPTBL / SLTTBL, $FFFF) at the boot sector's entry, $C01E.
SDS_FORCE="af=0x006A,bc=0,0xFB21=2,..." (with SDS_BOOT) overwrites registers / RAM
there first -- an experiment on OUR machine only.
SDS_RDSLT=1: every RDSLT ($000C, a published BIOS entry) called from RAM: slot, address
and the byte it returns (registers only). SDS_BOOTCODE=1: registers at every PC
$C030..$C056 the boot code runs (RAM; the first 120 hits after 2 s). SDS_ENASLT=1: every
ENASLT ($0024) from RAM (slot, page, A8) and the registers at $C057..$C0A5.
"""
import os, subprocess, sys, tempfile, shutil
D = os.environ["DISKCORPUS_DIR"]
img = os.path.join(D, os.environ.get("SDS_IMG", "SDSNAT1C.DSK"))   # SDS_IMG: another image (D-DISKCARVE, GAUNT)
mach = sys.argv[1] if len(sys.argv) > 1 else "C-BIOS_MSX1_EU_REPACK_DISK"
T = float(sys.argv[2]) if len(sys.argv) > 2 else 45
# SDS_LO / SDS_HI: the RAM window SDS_ENASLT logs registers in (default $C057..$C0A5);
# SDS_CAP: how many hits are kept (default 120). D-SDSBOOT, 2026-11-07: past $C0A5.
# SDS_BP=0x46BA,0x4E00: registers at OUR ROM's addresses (zerobas machine only -- never
# a reference ROM address). SDS_PEEK=1 adds the 3 bytes at PC, $A8 and the
# secondary register -- zerobas only (never the reference's RAM code, §8.5).
LO = os.environ.get("SDS_LO", "0xC057"); HI = os.environ.get("SDS_HI", "0xC0A5")
CAP = int(os.environ.get("SDS_CAP", "120"))
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
  if {{[info exists ::env(SDS_P1)] && ![info exists ::p1e] && $pc >= 0x4000 && $pc < 0x8000 && [machine_info time] > 4.0 && [lindex [get_selected_slot 1] 0] == 3 && [lindex [get_selected_slot 1] 1] == 0}} {{
    set ::p1e 1
    lappend ::ev "[format %.4f [machine_info time]] FIRST PC IN PAGE-1 RAM: [format %04X $pc] after: [join [lrange $::ring end-11 end] {{ }}]"
  }}
  lappend ::ring "[format %04X $pc]/[format %02X [lindex [get_selected_slot [expr {{$pc >> 14}}]] 0]]"
  if {{[llength $::ring] > 160}} {{ set ::ring [lrange $::ring end-159 end] }}
}}
if {{[info exists ::env(SDS_RING)]}} {{ debug set_condition 1 __rg }}
proc __ram38 {{}} {{
  set b ""
  for {{set i 0x38}} {{$i < 0x3B}} {{incr i}} {{ append b [format %02X [debug read {{Main RAM}} $i]] }}
  return $b
}}
proc __ff {{}} {{ if {{[catch {{ lappend ::ev "[format %.4f [machine_info time]] AFTER A8=FF from RAM PC: RAM 0038..003A=[__ram38] iff=[reg iff]" }} e]}} {{ lappend ::ev "TCL ERROR __ff: $e" }} }}
proc __a8 {{}} {{ if {{![info exists ::z0]}} {{ if {{$::wp_last_value == 0xFF && [reg pc] >= 0x8000 && [reg pc] < 0xF300 && ![info exists ::ff1]}} {{ set ::ff1 1; after time 0.0005 __ff }}; lappend ::ev "[format %.4f [machine_info time]] A8 := [format %02X $::wp_last_value] at PC=[format %04X [reg pc]] sp=[format %04X [reg sp]]" }} }}
if {{[info exists ::env(SDS_A8)]}} {{ debug set_watchpoint write_io 0xA8 1 __a8 }}
proc __c01e {{}} {{
  if {{[info exists ::c1e]}} return
  set ::c1e 1
  set r ""
  foreach x {{af bc de hl ix iy sp}} {{ append r " $x=[format %04X [reg $x]]" }}
  set w ""
  foreach {{a n}} {{0xF341 3 0xF345 4 0xF347 2 0xF348 1 0xFB21 8 0xF30D 4 0xF3D0 6 0xFCC1 4 0xFFFF 1}} {{
    set b ""
    for {{set i 0}} {{$i < $n}} {{incr i}} {{ append b [format %02X [debug read memory [expr {{$a + $i}}]]] }}
    append w " [format %04X $a]=$b"
  }}
  if {{[info exists ::env(SDS_FORCE)]}} {{
    foreach item [split $::env(SDS_FORCE) ,] {{
      lassign [split $item =] k v
      if {{[string match 0x* $k]}} {{ debug write memory $k [expr {{$v}}] }} else {{ reg $k [expr {{$v}}] }}
    }}
    lappend ::ev "FORCED $::env(SDS_FORCE)"
  }}
  lappend ::ev "[format %.4f [machine_info time]] BOOT C01E $r A8=[format %02X [debug read ioports 0xA8]] slots=[get_selected_slot 0]|[get_selected_slot 1]|[get_selected_slot 2]|[get_selected_slot 3] $w"
}}
if {{[info exists ::env(SDS_BOOT)]}} {{ debug set_bp 0xC01E 1 __c01e }}
proc __rds {{}} {{
  if {{[catch {{
    set sp [reg sp]
    set ret [expr {{[debug read memory $sp] | ([debug read memory [expr {{$sp+1}}]] << 8)}}]
    if {{$ret >= 0x8000}} {{
      set ::rdsret $ret
      lappend ::ev "[format %.4f [machine_info time]] RDSLT slot=[format %02X [reg a]] addr=[format %04X [reg hl]] from=[format %04X $ret]"
      debug set_bp $ret {{[reg pc] == $::rdsret}} {{ lappend ::ev "    -> A=[format %02X [reg a]]"; debug remove_bp [lindex [debug list_bp] end 0] }}
    }}
  }} e]}} {{ lappend ::ev "TCL ERROR __rds: $e" }}
}}
proc __bc {{}} {{
  if {{[catch {{
    if {{![info exists ::bcn]}} {{ set ::bcn 0 }}
    if {{[incr ::bcn] <= {CAP}}} {{
      set xtra ""
      if {{[info exists ::env(SDS_PEEK)] && [string match *REPACK* [machine_info config_name]]}} {{
        set pc [reg pc]
        set xtra " @pc=[format %02X%02X%02X [debug read memory $pc] [debug read memory [expr {{$pc+1}}]] [debug read memory [expr {{$pc+2}}]]] A8=[format %02X [debug read ioports 0xA8]] FFFF=[format %02X [expr {{255 - [debug read memory 0xFFFF]}}]]"
      }}
      lappend ::ev "[format %.4f [machine_info time]] PC=[format %04X [reg pc]] af=[format %04X [reg af]] bc=[format %04X [reg bc]] de=[format %04X [reg de]] hl=[format %04X [reg hl]] sp=[format %04X [reg sp]]$xtra"
    }}
  }} e]}} {{ lappend ::ev "TCL ERROR __bc: $e" }}
}}
if {{[info exists ::env(SDS_BOOTCODE)]}} {{ for {{set x 0xC01E}} {{$x <= 0xC056}} {{incr x}} {{ debug set_bp $x {{[machine_info time] > 2.0}} __bc }} }}
proc __ena {{}} {{
  if {{[catch {{
    set sp [reg sp]
    set ret [expr {{[debug read memory $sp] | ([debug read memory [expr {{$sp+1}}]] << 8)}}]
    if {{$ret >= 0x8000}} {{ lappend ::ev "[format %.4f [machine_info time]] ENASLT slot=[format %02X [reg a]] page=[format %02X [reg h]] from=[format %04X $ret] A8=[format %02X [debug read ioports 0xA8]]" }}
  }} e]}} {{ lappend ::ev "TCL ERROR __ena: $e" }}
}}
if {{[info exists ::env(SDS_ENASLT)]}} {{
  debug set_bp 0x0024 {{[machine_info time] > 2.0}} __ena
  for {{set x {LO}}} {{$x <= {HI}}} {{incr x}} {{ debug set_bp $x {{[machine_info time] > 2.0}} __bc }}
}}
if {{[info exists ::env(SDS_BP)] && [string match *REPACK* [machine_info config_name]]}} {{
  foreach x [split $::env(SDS_BP) ,] {{ debug set_bp $x {{[machine_info time] > 2.0}} __bc }}
}}
if {{[info exists ::env(SDS_RDSLT)]}} {{ debug set_bp 0x000C {{[machine_info time] > 9.0 || [string match *REPACK* [machine_info config_name]]}} __rds }}
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
