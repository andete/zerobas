#!/usr/bin/env python3
"""D-DOSBASIC: the BDOS calls (PC = $0005, C/DE/HL) each machine makes while
`BASIC` is parsed and run -- registers only. Stock runs it from AUTOEXEC.BAT
(12.55..12.75 s); ours has it typed (14.40..14.60 s)."""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
from disk_probe_bdos import fat12_add               # noqa: E402
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import disk_probe_wrblk_alt as W                    # noqa: E402
import probe_tmp                                    # noqa: E402
for tag, machine, t0, t1 in (("STOCK", RT.REF_MACHINE, 12.55, 12.75), ("OURS", RT.OUR_MACHINE, 14.40, 14.60)):
    dsk = probe_tmp.tmp(f"bb_{tag}.dsk")
    shutil.copyfile(RT.DEFAULT_DOS, dsk)
    img = bytearray(open(dsk, "rb").read())
    fat12_add(img, "AUTOEXEC", "BAT", b"BASIC\r\n")
    open(dsk, "wb").write(img)
    out = probe_tmp.tmp(f"bb_{tag}.log")
    tcl = (f"set bf [open {{{out}}} w]\n"
           f"after time {t0} {{ set ::bid [debug set_condition {{[reg PC] == 0x0005}} "
           "{ global bf; puts $bf \"[format %.4f [machine_info time]] C=[format %02X [reg C]] "
           "DE=[format %04X [reg DE]] HL=[format %04X [reg HL]] SP=[format %04X [reg SP]]\" }] }\n"
           f"after time {t1} {{ catch {{ debug remove_condition $::bid }}; close $bf }}\n")
    W.run_once(machine, dsk, 14, t1 + 1, 600, cmd="BASIC", extra_tcl=tcl)
    print(f"== {tag} ({t0}..{t1} s)")
    for ln in open(out):
        print("  " + ln.rstrip())
