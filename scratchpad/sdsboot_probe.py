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
  close $f
  exit
}}
"""
open(os.path.join(td, "s.tcl"), "w").write(tcl)
subprocess.run([shutil.which("openmsx") or "/opt/homebrew/bin/openmsx", "-machine", mach,
                "-script", os.path.join(td, "s.tcl")], timeout=1800, capture_output=True)
print(open(out).read() if os.path.exists(out) else "NO OUTPUT")
