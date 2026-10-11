#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Joost, 2026-10-11: openMSX's tape AUTORUN does not work on zerobas.

openMSX's autorun (its own source, visible in the binary's strings) sets a
debugger breakpoint at H.READ ($FF07) and, when it fires, types RUN"CAS:" /
BLOAD"CAS:",R / CLOAD; for a CLOAD tape it then waits on H.MAIN ($FF0C) to
type RUN. zerobas's source names neither hook, so the breakpoint never fires.

THE METHOD (black-box, our own code in RAM): a stored program CLEARs the top
of memory, POKEs two 10-byte counters (PUSH AF / LD A,(n) / INC A / LD (n),A /
POP AF / RET) and points H.READ and H.MAIN at them with a JP. When the program
ENDs, the machine returns to its prompt; a second, typed line prints both
counts. Clean room: typed BASIC, POKE/PEEK of RAM cells we own and of two
documented hook cells. No ROM byte is read.

Prediction: VG-8020 both counts > 0; zerobas 0 0.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
SETUP = ["CLEAR 200,&HE000",
         "FOR I=0 TO 19:READ A$:POKE &HE000+I,VAL(\"&H\"+A$):NEXT",
         "DATA F5,3A,20,E0,3C,32,20,E0,F1,C9",
         "DATA F5,3A,21,E0,3C,32,21,E0,F1,C9",
         "POKE &HE020,0:POKE &HE021,0",
         "POKE &HFF08,0:POKE &HFF09,&HE0:POKE &HFF07,&HC3",
         "POKE &HFF0D,10:POKE &HFF0E,&HE0:POKE &HFF0C,&HC3",
         "END"]
READ = ['PRINT"<";PEEK(&HE020);PEEK(&HE021);">"']


def answer(raw):
    t = " ".join("".join(raw or "").split())
    i, j = t.rfind("<"), t.rfind(">")
    return t[i + 1:j].strip() if 0 <= i < j else None


def main():
    for m in (REF, ZB):
        raws = omsx_repl.run_cases(m, [("stored", SETUP), ("direct", READ)],
                                   batch=True)
        print(f"{m:32s} H.READ H.MAIN counts: {answer(raws[-1])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
