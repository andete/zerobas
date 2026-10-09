# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CALLSYSTEM measurement (2026-10-09): what `CALL SYSTEM` does on the CF-3300
and on zerobas DISK, with and without an MSX-DOS 1 system disk.

  nosys     test720.dsk (no MSXDOS.SYS): `CALL SYSTEM` typed, then `PRINT "[OK]"`
  nosyserr  the same inside a program with ON ERROR GOTO, printing ERR
  nosysund  `_SYSTEM` (the underscore form)
  dos       a private copy of an MSX-DOS 1 system disk (argv[1]): the boot, then
            `BASIC`, `CALL SYSTEM`, `DIR`

Clean-room: typed keys in, the text screen out. Prints each side's screen rows.
"""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

DOS = sys.argv[1] if len(sys.argv) > 1 else None
CASES = {
    "nosys": ("test", ["CALL SYSTEM", 'PRINT "[OK]"']),
    "nosyserr": ("test", ["10 ON ERROR GOTO 90", "20 CALL SYSTEM", '30 PRINT "[BACK]":END',
                          '90 PRINT "ERR";ERR;"ERL";ERL:END', "RUN"]),
    "nosysund": ("test", ["_SYSTEM", 'PRINT "[OK]"']),
    "dos": ("dos", ["", "", "BASIC", "SCREEN 0:WIDTH 40", 'PRINT "[IN BASIC]"', "CALL SYSTEM", "", "DIR"]),
    "dosboot": ("dos", ["", "", "MODE 40", "VER"]),
    "dospeek": ("dos", ["", "", "BASIC", "SCREEN 0:WIDTH 40", "PRINT PEEK(&HF340);PEEK(&HF338);PEEK(&HF33D)"]),
    "nosyspeek": ("test", ["PRINT PEEK(&HF340);PEEK(&HF338);PEEK(&HF33D)"]),
    "dosfile": ("dos", ["", "", "BASIC", "SCREEN 0:WIDTH 40", 'OPEN "X.TXT" FOR OUTPUT AS 1', 'PRINT #1,"HELLO"', "CALL SYSTEM", "", "MODE 40", "TYPE X.TXT", "DIR X.TXT"]),
    "doskillsys": ("dos", ["", "", "BASIC", "SCREEN 0:WIDTH 40", 'KILL "MSXDOS.SYS"', "CALL SYSTEM", "", "MODE 40", "DIR"]),
    "doskillcom": ("dos", ["", "", "BASIC", "SCREEN 0:WIDTH 40", 'KILL "COMMAND.COM"', "CALL SYSTEM", "", "MODE 40", "DIR"]),
    "dosarg": ("dos", ["", "", "BASIC", "SCREEN 0:WIDTH 40", 'CALL SYSTEM("DIR")', 'PRINT "[STILL BASIC]"']),
    "dosprog": ("dos", ["", "", "BASIC", "SCREEN 0:WIDTH 40", "10 CALL SYSTEM", '20 PRINT "[AFTER]"', "RUN", "", "MODE 40", "DIR"]),
    "dos40": ("dos", ["", "", "MODE 40", "BASIC", "SCREEN 0:WIDTH 40", 'PRINT "[IN BASIC]"', "CALL SYSTEM", "", "MODE 40", "DIR"]),
}


def rows(scr):
    if scr is None:
        return ["<NO OUTPUT>"]
    return [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40) if scr[i:i + 40].strip()]


def main():
    only = [a for a in sys.argv[2:]] or [k for k in CASES if k != "dos" or DOS]
    for name in only:
        src, lines = CASES[name]
        for side, m in (("CF", "National_CF-3300"), ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK")):
            dsk = probe_tmp.tmp(f"callsystem_{name}_{m}.dsk")
            shutil.copyfile(DOS if src == "dos" else os.path.join(REPO, "disk", "test720.dsk"), dsk)
            scr = omsx_repl.run_cases(m, [("direct", lines)], batch=False, diska=dsk, boot=14.0,
                                      reset=("",) if src == "dos" else ("", "SCREEN 0:WIDTH 40"), step=5.0, run_gap=20.0)[0]
            print(f"== {name} {side}", flush=True)
            for r in rows(scr):
                print(f"   |{r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
