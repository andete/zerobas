# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CALLSYSTEM (gate: callsystem-acceptance): CALL SYSTEM, back to MSX-DOS.
Measured 2026-10-09 (scratchpad/callsystem_probe.py, callsystem_swap.py): on the
CF-3300 it returns WARM to A> after a DOS boot, closing the open files first,
and is Illegal function call after a data-disk boot; zerobas said Syntax error.

  nosys     data disk: `CALL SYSTEM`                 -> 5, BASIC goes on
  nosysprg  data disk: in a program, ON ERROR        -> ERR 5 ERL 20
  nosysund  data disk: `_SYSTEM`                     -> 5
  dosarg    after DOS: `CALL SYSTEM("DIR")`          -> Syntax error, still BASIC
  dos       after DOS: `CALL SYSTEM`, `DIR MSXDOS.SYS` -> A>, no banner, the key
            row gone, the BASIC text above kept
  dosprog   after DOS: from a program line           -> the same
  dosfile   after DOS: an OPEN output file           -> closed (TYPE shows it)
  doscom    after DOS: COMMAND.COM deleted           -> MSXDOS.SYS asks for it

Each row prints `ROW <name> CF=[...] ZB=[...] <verdict>`.
Exit 0 all agree; 1 a divergence; 2 the CF-3300 gave no reading / no DOS disk.
Clean-room: typed keys in, the text screen out. CF-3300 vs zerobas DISK, each on
a private copy of disk/test720.dsk (data rows) or of the MSX-DOS 1 system disk
disk_bdos_acceptance.py uses (--dos-disk to override; refused if absent).
"""
import argparse, os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

DEFAULT_DOS_DISK = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")
TO_BASIC = ["", "", "BASIC", "SCREEN 0:WIDTH 40"]   # date prompt, time, then BASIC
ROWS = {
    "nosys":    ("data", ["CALL SYSTEM", 'PRINT "[OK]"']),
    "nosysprg": ("data", ["10 ON ERROR GOTO 90", "20 CALL SYSTEM", '30 PRINT "[BACK]":END',
                          '90 PRINT "ERR";ERR;"ERL";ERL:END', "RUN"]),
    "nosysund": ("data", ["_SYSTEM", 'PRINT "[OK]"']),
    "dosarg":   ("dos", TO_BASIC + ['CALL SYSTEM("DIR")', 'PRINT "[STILL BASIC]"']),
    "dos":      ("dos", TO_BASIC + ["CALL SYSTEM", "DIR MSXDOS.SYS"]),
    "dosprog":  ("dos", TO_BASIC + ["10 CALL SYSTEM", '20 PRINT "[AFTER]"', "RUN",
                                    "DIR MSXDOS.SYS"]),
    "dosfile":  ("dos", TO_BASIC + ['OPEN "X.TXT" FOR OUTPUT AS 1', 'PRINT #1,"HELLO"',
                                    "CALL SYSTEM", "TYPE X.TXT"]),
    "doscom":   ("dos", TO_BASIC + ['KILL "COMMAND.COM"', "CALL SYSTEM"]),
}


def rows(scr):
    if scr is None:
        return None
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)]
    # the BASIC prompt is the one thing that may differ (Ok / ZB): drop it
    return " | ".join(x for x in r if x and x.strip() not in ("Ok", "ZB"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dos-disk", default=DEFAULT_DOS_DISK)
    ap.add_argument("only", nargs="*")
    args = ap.parse_args()
    only = args.only or list(ROWS)
    if any(ROWS[n][0] == "dos" for n in only) and not os.path.isfile(args.dos_disk):
        print(f"INSTRUMENT FAULT: no MSX-DOS 1 system disk at {args.dos_disk} (--dos-disk)")
        return 2
    bad, blind = [], []
    for name in only:
        src, lines = ROWS[name]
        got = {}
        for side, m in (("CF", "National_CF-3300"), ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK")):
            dsk = probe_tmp.tmp(f"callsystem_{name}_{m}.dsk")
            shutil.copyfile(args.dos_disk if src == "dos" else
                            os.path.join(REPO, "disk", "test720.dsk"), dsk)
            reset = ("",) if src == "dos" else ("", "SCREEN 0:WIDTH 40")
            try:
                got[side] = rows(omsx_repl.run_cases(m, [("direct", lines)], batch=False,
                                                     diska=dsk, boot=14.0, reset=reset,
                                                     step=5.0, run_gap=20.0)[0])
            except SystemExit as e:
                # 🔴 omsx_repl RAISES on a mangled delivery, which ended the
                # whole run at the first such row -- and a knife harness then
                # scored the rows never printed as UNMOVED (K-CS4, 2026-10-09).
                # On zerobas's side it is a reading (a DOS date prompt ate the
                # typed line); on the reference's it is no reading at all.
                got[side] = None if side == "CF" else \
                    "<APPARATUS: " + str(e).splitlines()[0][:70] + ">"
        if got["CF"] is None:
            blind.append(name)
            verdict = "NO-REFERENCE"
        elif got["CF"] == got["ZB"]:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad.append(name)
        print(f"ROW {name} CF=[{got['CF']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: the CF-3300 gave no reading on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: CALL SYSTEM ({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
