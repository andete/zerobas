# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BOOTKEYS, measure first (2026-10-10): what SHIFT or CTRL held from power-on
does on the CF-3300 and on zerobas DISK.

The key is pressed in the Tcl prologue (before the machine runs) and released 6
emulated seconds later. Then a program reports FRE(0), HIMEM ($FC4A), the drive
count ($F347, MSX-DOS 1 work area) and DSKF(0), with ON ERROR catching each.
DSKF(2) is left out: on the CF-3300 it prompts for drive B and waits.

Clean-room: the key matrix in; typed BASIC; documented work-area cells out.
"""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

KEYS = {"plain": None, "shift": (6, 0x01), "ctrl": (6, 0x02)}
LINES = ["10 ON ERROR GOTO 90",
         '20 PRINT "F";FRE(0);"H";HEX$(PEEK(&HFC4A)+256*PEEK(&HFC4B));"D";PEEK(&HF347)',
         '30 PRINT "K";DSKF(0)', "40 END", '90 PRINT "E";ERR;ERL:RESUME NEXT', "RUN"]


def rows(scr):
    if scr is None:
        return "<NO CAPTURE>"
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    banner = [x.strip() for x in r[:6] if x.strip()]
    if "RUN" in r:
        r = r[r.index("RUN") + 1:]
    return " | ".join(x for x in r if x and x.strip() not in ("Ok", "ZB")), banner


for name, key in KEYS.items():
    for side, m in (("CF", "National_CF-3300"), ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK")):
        dsk = probe_tmp.tmp(f"bootkeys_{name}_{m}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        pro = () if key is None else (f"keymatrixdown {key[0]} {key[1]}",
                                      f"after time 6 {{ keymatrixup {key[0]} {key[1]} }}")
        scr = omsx_repl.run_cases(m, [("direct", LINES)], batch=False, diska=dsk, boot=14.0,
                                  reset=("", "SCREEN 0:WIDTH 40"), step=4.0, run_gap=10.0, prologue=pro)[0]
        out, banner = rows(scr) if scr else ("<NO CAPTURE>", [])
        print(f"{name:6s} {side}  [{out}]", flush=True)
