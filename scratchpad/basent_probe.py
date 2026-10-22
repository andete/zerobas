#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-BASENT triage: what the disk ROM's published BASENT entry ($4022, "start BASIC")
does with the HL it is given -- measured with OUR OWN program on each machine:
a 14-byte stub at $D000 (`ld iy,<MASTERS>00 / ld ix,$4022 / ld hl,$D100 / jp CALSLT`,
the slot read from $F348), our own text at $D100 (0-terminated), then the screen.
Black box: a published entry, our own bytes in, the screen out. No ROM byte read.

    DISKCORPUS_DIR=<dir holding IMAGE> python3 -u scratchpad/basent_probe.py IMAGE \
        [--persist PATH] [--machines ref,ref2,zb] 'T$ expression' ...
e.g. '"PRINT 12345"'  'CHR$(&H91)+" 12345"'  '""'
"""
import argparse, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MACH = {"ref": ("National_CF-3300", []), "ref2": ("Philips_VG_8020", ["--ext", "Philips_NMS_1200"]),
        "zb": ("C-BIOS_MSX1_EU_REPACK_DISK", [])}
STUB = "&HFD,&H21,0,0,&HDD,&H21,&H22,&H40,&H21,0,&HD1,&HC3,&H1C,0"


def steps(texpr):
    return ["14:NEW", "16:CLEAR 200,&HCFFF",
            "19:10 FOR I=0 TO 13:READ A:POKE &HD000+I,A:NEXT:POKE &HD003,PEEK(&HF348)",
            f"23:20 T$={texpr}:FOR I=1 TO LEN(T$):POKE &HD0FF+I,ASC(MID$(T$,I,1)):NEXT:"
            "POKE &HD100+LEN(T$),0",
            "28:30 DEFUSR=&HD000:X=USR(0)",
            f"31:40 DATA {STUB}",
            "35:RUN", "41:", "50:"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("texts", nargs="+")
    ap.add_argument("--persist")
    ap.add_argument("--machines", default="ref,ref2,zb")
    a = ap.parse_args()
    for t in a.texts:
        for m in a.machines.split(","):
            machine, extra = MACH[m]
            print(f"##### T$={t}  on {m} ({machine})", flush=True)
            cmd = [sys.executable, "-u", os.path.join(HERE, "disklook.py"), a.image, machine,
                   *steps(t), *extra] + (["--persist", a.persist] if a.persist else [])
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            out = r.stdout.split("== S7", 1)
            print(("== S7" + out[1]) if len(out) > 1 else r.stdout[-2000:], flush=True)


if __name__ == "__main__":
    main()
