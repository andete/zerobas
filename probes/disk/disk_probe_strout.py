# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-STROUT (gate: strout-acceptance): BDOS $09 STROUT prints on ours as on the
CF-3300. A COM prints HELLO-STROUT$ with it; both machines' screens (the name
table VDP R#2 points at) must show HELLO-STROUT and the DOS banner's
COMMAND version 1.08 line (itself printed with STROUT).

On the C-BIOS target RES_PRINT ($F1C9) was never installed (it lived below the
RAMAD $FF gate), so STROUT printed nothing and slid through RST 38h.
Exit 0 when both screens carry both texts; 1 otherwise.
"""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
from disk_probe_bdos import fat12_add               # noqa: E402
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import disk_probe_wrblk_alt as W                    # noqa: E402
import probe_tmp                                    # noqa: E402
HERE = os.path.dirname(os.path.abspath(__file__))  # probes/disk/, beside strout.asm
import subprocess
subprocess.run(["pasmo", "--bin", os.path.join(HERE, "strout.asm"), probe_tmp.tmp("strout.com")], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
COM = open(probe_tmp.tmp("strout.com"), "rb").read()
results = {}
for tag, machine in (("STOCK", RT.REF_MACHINE), ("OURS", RT.OUR_MACHINE)):
    dsk = probe_tmp.tmp(f"strout_{tag}.dsk")
    shutil.copyfile(RT.DEFAULT_DOS, dsk)
    img = bytearray(open(dsk, "rb").read())
    fat12_add(img, "STROUT", "COM", COM)
    fat12_add(img, "AUTOEXEC", "BAT", b"STROUT\r\n")
    open(dsk, "wb").write(img)
    out = probe_tmp.tmp(f"strout_{tag}.log")
    trace = ""
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
    text = ""
    for ln in open(out):
        print("  " + ln.rstrip()[:240])
        text += ln
    ok_m = "HELLO-STROUT" in text and "COMMAND version" in text
    print(f"  {tag}: {'prints' if ok_m else 'does NOT print'} HELLO-STROUT and the COMMAND banner")
    results[tag] = ok_m
if not results.get("STOCK"):
    print("\nINSTRUMENT FAULT: the CF-3300 did not print it -- no reference")
    sys.exit(2)
print(f"\n{'PASS' if results.get('OURS') else 'FAIL'}: STROUT on ours")
sys.exit(0 if results.get("OURS") else 1)
