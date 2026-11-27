#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""C-BIOS integration step 1: BIOS FORMAT ($0147) on the BASIC-less C-BIOS host must RETURN (refused, Cy = 1).
A .COM run from AUTOEXEC.BAT calls $0147 through MSX-DOS's CALSLT ($001C) with the main slot (EXPTBL), stores the
returned AF at $0400 and a done-mark $A5 at $0402, then loops. Read at 40 s. Clean room: our own program; RAM only."""
import os, shutil, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "disk")); sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
from disk_probe_bdos import fat12_add  # noqa: E402
import omsx_preflight, probe_tmp  # noqa: E402
ASM = """        org $0100
        ld a,$EE
        ld ($0402),a
        ld iy,($FCC0)        ; IYH = EXPTBL (the main slot)
        ld ix,$0147
        call $001C           ; CALSLT: BIOS FORMAT
        push af
        pop hl
        ld ($0400),hl
        ld a,$A5
        ld ($0402),a
loop:   jr loop
"""
MACHINE = sys.argv[1] if len(sys.argv) > 1 else "CBIOS2_CUR_MSX1_EU_NOBASIC_DISK"
td = tempfile.mkdtemp(dir=probe_tmp.ROOT)
src = os.path.join(td, "f.asm"); com = os.path.join(td, "f.com"); open(src, "w").write(ASM)
subprocess.run(["pasmo", "--bin", src, com], check=True, stdout=subprocess.DEVNULL)
dsk = os.path.join(td, "d.dsk"); shutil.copyfile(os.path.expanduser("~/Documents/msx/msx/disks/test.dsk"), dsk)
img = bytearray(open(dsk, "rb").read())
fat12_add(img, "BIOSFMT", "COM", open(com, "rb").read()); fat12_add(img, "AUTOEXEC", "BAT", b"BIOSFMT\r\n")
open(dsk, "wb").write(img)
out = os.path.join(td, "o.txt"); tcl = os.path.join(td, "s.tcl")
open(tcl, "w").write(f"""set throttle off
after time 40 {{ set f [open {{{out}}} w]; binary scan [debug read_block memory 0x0400 3] H* m; puts $f $m; close $f; exit }}
""")
subprocess.run(omsx_preflight.guarded(["openmsx", "-machine", MACHINE, "-diska", dsk, "-command",
               "set renderer none; set sound_driver null", "-script", tcl]), stdout=subprocess.DEVNULL,
               stderr=subprocess.DEVNULL, timeout=200)
m = bytes.fromhex(open(out).read().strip()) if os.path.exists(out) else None
if m is None:
    print("NO READING"); sys.exit(2)
f, a, mark = m[0], m[1], m[2]
print(f"{MACHINE}: returned={'yes' if mark == 0xA5 else 'NO (mark %02X)' % mark} A={a:02X} F={f:02X} Cy={f & 1}")
shutil.rmtree(td, ignore_errors=True)
sys.exit(0 if mark == 0xA5 and f & 1 else 1)
