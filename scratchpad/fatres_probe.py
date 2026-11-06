# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FATRES: where does the CF-3300 keep the FAT in RAM -- normal boot vs a CTRL boot
(CTRL held at power-on)? Black-box, RAM ONLY (clean-room: work-area RAM contents and
addresses are readable; no ROM byte is read, nothing is single-stepped).

A copy of disk/test720.dsk (our own generated image; its FAT sector 1 is known) is
mounted. Per boot mode: HIMEM ($FC4A) after boot; `FILES` typed (a FAT + directory
read); RAM $8000-$FFFF dumped; every place the FAT's first 12 bytes occur is listed,
with how far the match runs against the whole 3-sector FAT. Then `SAVE "Z"` (which
changes the FAT) and a second dump: is the RAM copy updated (does it still match the
image's NEW FAT)?"""
import os, shutil, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import omsx_preflight, probe_tmp  # noqa: E402
from omsx_repl import key_proc  # noqa: E402
import run_programs as rp  # noqa: E402

TCL = r"""
set throttle off
KEYPROC
proc __rd16 {a} { expr {[debug read memory $a] + 256*[debug read memory [expr {$a+1}]]} }
proc __dump {f} { set o [open $f w]; fconfigure $o -translation binary; puts -nonewline $o [debug read_block memory 0x8000 0x8000]; close $o }
CTRLHOLD
after time 6 { type "\r" }
after time 10 { type "\r" }
after time 16 { set o [open {OUT}.himem w]; puts $o [format %04X [__rd16 0xFC4A]]; close $o; __key "FILES\r" }
after time 22 { __dump {OUT}.a; __key "10 REM Z\r" }
after time 24 { __key "SAVE \"Z\"\r" }
after time 32 { __dump {OUT}.b; exit }
"""


def fat_of(img):
    return open(img, "rb").read()[512:512 + 3 * 512]


def run(machine, ctrl, tag):
    dsk = probe_tmp.tmp(f"fatres_{tag}.dsk")
    shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
    out = probe_tmp.tmp(f"fatres_{tag}")
    tcl = probe_tmp.tmp(f"fatres_{tag}.tcl")
    hold = ("keymatrixdown 6 0x02\nafter time 8 { keymatrixup 6 0x02 }" if ctrl else "")
    open(tcl, "w").write(TCL.replace("{OUT}", out).replace("KEYPROC", key_proc()).replace("CTRLHOLD", hold))
    fat_before = fat_of(dsk)
    subprocess.run(omsx_preflight.guarded([rp.OMSX, "-machine", machine, "-command",
                   "set renderer none; set sound_driver null", "-script", tcl, "-diska", dsk]),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
    fat_after = fat_of(dsk)
    himem = open(out + ".himem").read().strip()
    print(f"== {machine} {'CTRL boot' if ctrl else 'normal boot'}: HIMEM ${himem}; "
          f"SAVE changed the FAT on disk: {fat_before != fat_after}")
    for lab, f, fat in (("after FILES", out + ".a", fat_before), ("after SAVE", out + ".b", fat_after)):
        ram = open(f, "rb").read()
        key = fat[:12]
        i, found = 0, []
        while True:
            j = ram.find(key, i)
            if j < 0:
                break
            n = 0
            while n < len(fat) and j + n < len(ram) and ram[j + n] == fat[n]:
                n += 1
            found.append((0x8000 + j, n))
            i = j + 1
        print(f"   {lab}: FAT[0..11] = {key.hex(' ')}; in RAM at " +
              (", ".join(f"${a:04X} (matches {n} of {len(fat)} B)" for a, n in found) or "NOWHERE"))


for ctrl in (False, True):
    run("National_CF-3300", ctrl, "cf" + ("c" if ctrl else "n"))
