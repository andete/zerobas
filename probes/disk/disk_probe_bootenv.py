#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-BOOTREGS: the environment a disk's boot code gets at step 7 (the "load the
system" call to $C01E, Cy = 1), before any MSXDOS.SYS -- on the CF-3300 and on
zerobas.

Our OWN boot code, written into a copy of the DOS test disk's boot sector at $1E:
    RET NC                          step 5 (Cy = 0): back to the disk ROM
    LD ($C803),DE / LD ($C805),HL   the registers step 7 hands over
    $0141 in page-0 RAM := LD A,$A5 / RET
    LD A,7 / RST 30h $80 $0141 -> ($C800)   CALLF, an "expanded" id on slot 0
    LD A,7 / RST 30h $00 $0141 -> ($C801)   CALLF, slot 0
    LD A,$5A -> ($C802), then JR $
Measured 2026-10-23 (scratchpad/bootcallf_run.out): the CF-3300 runs the RAM at
$0141 for slot $80 (A = $A5: its primary is not expanded) and the BIOS's SNSMAT for
slot $00 (row 7, no key: $FF); it enters the boot code with DE = $F368 and HL =
$F323. frayd1.dsk's boot code relies on both (D-BOOTREGS). Read back from RAM at T14.
Black box: our own code's answers; nothing of the reference is read.
"""
import os, shutil, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import omsx_preflight                               # noqa: E402
import probe_tmp                                    # noqa: E402

CODE = bytes([0xD0,                                   # RET NC
              0xED, 0x53, 0x03, 0xC8,                 # LD ($C803),DE
              0x22, 0x05, 0xC8,                       # LD ($C805),HL
              0x3E, 0x3E, 0x32, 0x41, 0x01,           # LD A,$3E / LD ($0141),A
              0x3E, 0xA5, 0x32, 0x42, 0x01,           # LD A,$A5 / LD ($0142),A
              0x3E, 0xC9, 0x32, 0x43, 0x01,           # LD A,$C9 / LD ($0143),A
              0x3E, 0x07, 0xF7, 0x80, 0x41, 0x01,     # LD A,7 / RST 30h $80 $0141
              0x32, 0x00, 0xC8,                       # LD ($C800),A
              0x3E, 0x07, 0xF7, 0x00, 0x41, 0x01,     # LD A,7 / RST 30h $00 $0141
              0x32, 0x01, 0xC8,                       # LD ($C801),A
              0x3E, 0x5A, 0x32, 0x02, 0xC8,           # LD A,$5A / LD ($C802),A
              0x18, 0xFE])                            # JR $
NAMES = ["CALLF $80:$0141", "CALLF $00:$0141", "mark", "DE", "HL"]
got = {}
for tag, machine in (("STOCK", RT.REF_MACHINE), ("OURS", RT.OUR_MACHINE)):
    dsk = probe_tmp.tmp(f"bootenv_{tag}.dsk")
    shutil.copyfile(RT.DEFAULT_DOS, dsk)
    img = bytearray(open(dsk, "rb").read())
    img[0x1E:0x1E + len(CODE)] = CODE
    open(dsk, "wb").write(img)
    out = probe_tmp.tmp(f"bootenv_{tag}.mem")
    if os.path.exists(out):
        os.remove(out)
    tcl = (f"set throttle off\nafter time 14 {{ set f [open {{{out}}} w]; "
           "binary scan [debug read_block {Main RAM} 0xC800 7] H* b; puts $f $b; close $f; exit }\n")
    s = probe_tmp.tmp(f"bootenv_{tag}.tcl")
    open(s, "w").write(tcl)
    subprocess.run(omsx_preflight.guarded([RT.OMSX, "-machine", machine, "-diska", dsk,
                    "-command", "set renderer none; set sound_driver null", "-script", s]),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
    b = bytes.fromhex(open(out).read().split()[0]) if os.path.exists(out) else b""
    got[tag] = b
    if len(b) == 7:
        print(f"{tag}: CALLF $80:$0141 -> A={b[0]:02X}   CALLF $00:$0141 -> A={b[1]:02X}   "
              f"mark={b[2]:02X}   step 7 entered with DE={b[3] | b[4] << 8:04X} HL={b[5] | b[6] << 8:04X}")
    else:
        print(f"{tag}: <NO OUTPUT>")
S, O = got["STOCK"], got["OURS"]
ok = len(S) == len(O) == 7 and S[2] == 0x5A and O == S
print("PASS: the boot code's step-7 environment matches the CF-3300 (DE / HL, CALLF to page 0)"
      if ok else "FAIL: the step-7 environment differs (see above)")
sys.exit(0 if ok else 1)
