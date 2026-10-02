"""Is BDOS $09 STROUT broken on ours? A COM prints HELLO-STROUT$ with it, on both
machines: the screen (name table) and the PHASE byte after; on the CF-3300 also
the PC path from $F1C9 (registers only, 40 steps, slot of page 1 noted)."""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
from disk_probe_bdos import fat12_add               # noqa: E402
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import disk_probe_wrblk_alt as W                    # noqa: E402
import probe_tmp                                    # noqa: E402
HERE = os.path.dirname(os.path.abspath(__file__))
import subprocess
subprocess.run(["pasmo", "--bin", os.path.join(HERE, "strout.asm"), probe_tmp.tmp("strout.com")], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
COM = open(probe_tmp.tmp("strout.com"), "rb").read()
for tag, machine in (("STOCK", RT.REF_MACHINE), ("OURS", RT.OUR_MACHINE)):
    dsk = probe_tmp.tmp(f"strout_{tag}.dsk")
    shutil.copyfile(RT.DEFAULT_DOS, dsk)
    img = bytearray(open(dsk, "rb").read())
    fat12_add(img, "STROUT", "COM", COM)
    fat12_add(img, "AUTOEXEC", "BAT", b"STROUT\r\n")
    open(dsk, "wb").write(img)
    out = probe_tmp.tmp(f"strout_{tag}.log")
    trace = ("set tn 0\nset ::tid [debug set_condition {[reg PC] == 0xF1C9} "
             "{ global tf tn; set ::tid2 [debug set_condition {1} "
             "{ global tf tn; puts $tf \"PC [format %04X [reg PC]] s1=[pc_in_slot 3 1]/[pc_in_slot 0 0]\"; "
             "incr tn; if {$tn >= 40} { debug remove_condition $::tid2 } }]; "
             "debug remove_condition $::tid }]\n") if tag == "STOCK" else ""
    tcl = (f"set tf [open {{{out}}} w]\n" + trace +
           "proc dumpv {t} { global tf; set nb [expr {([vdpreg 2] & 15) * 1024}]; "
           "set w [expr {([vdpreg 1] & 16) ? 40 : 32}]; set s {}; "
           "for {set i 0} {$i < [expr {24 * $w}]} {incr i} { set c [debug read VRAM [expr {$nb + $i}]]; "
           "append s [expr {$c >= 32 && $c < 127 ? [format %c $c] : { }}]; "
           "if {($i + 1) % $w == 0} { append s {|} } }; "
           "puts $tf \"SCR $t PHASE=[debug read memory 0xC000] [string map {{  } {}} $s]\"; flush $tf }\n"
           "after time 20 { dumpv 20 }\nafter time 30 { dumpv 30; close $tf }\n")
    W.run_once(machine, dsk, 14, 31, 300, cmd="STROUT", extra_tcl=tcl)
    print(f"== {tag}")
    for ln in open(out):
        print("  " + ln.rstrip()[:240])
