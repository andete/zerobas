#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""savedev-acceptance (D-SAVEDEV): SAVE to the printer, the screen and GRP:.

Measured on the VG-8020 (no disk) and the CF-3300 alike: the run ends FIRST,
then `SAVE "LPT:"` lists the program to the printer, `SAVE "CRT:"` lists it on
the screen (as LIST does), and `SAVE "GRP:"` is ERR 5 -- in 65535, the run
already over, yet the ON ERROR handler still runs. zerobas raised 56 for all
three (and, on the diskless target before D-NODEV, took them as tape names).

Each row is one small program (a delay first, so the runner sees it run); the
printer log and the lines on the screen after `Found:` (the function-key bar's
spacing differs by machine, and the prompt reads ZB) must equal the
reference's: the VG-8020 for the diskless target, the CF-3300 for the DISK one.

Clean-room: typed keys and a tape in; the printer port and the text screen out.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs                                  # noqa: E402

DEVS = ['"LPT:"', '"CRT:"', '"GRP:"']
PAIRS = [(False, run_programs.REF, "C-BIOS_MSX1_EU_REPACK_NODISK"),
         (True, run_programs.DISK_REF, "C-BIOS_MSX1_EU_REPACK_DISK")]


def prog(dev, disk):
    return (("1 REM @DISK\n" if disk else "") + "10 ON ERROR GOTO 90\n"
            "15 FOR I=1 TO 500:NEXT\n20 LPRINT \"S\"\n30 SAVE " + dev + "\n"
            "40 LPRINT \"AFTER\":END\n90 LPRINT \"ERR\";ERR;ERL:END\n")


def listed(rows):
    body = [r.strip() for r in rows if r.strip()]
    i = max([k for k, r in enumerate(body) if r.startswith("Found:")] + [-1])
    return [r for r in body[i + 1:] if r not in ("Ok", "ZB") and "goto" not in r
            and "Ã" not in r]


def main():
    bad = 0
    for dev in DEVS:
        for disk, ref_m, zb_m in PAIRS:
            text = prog(dev, disk)
            ref = run_programs.run(ref_m, "savedev", text)
            zb = run_programs.run(zb_m, "savedev", text)
            ok = (ref[1] == zb[1] and listed(ref[2]) == listed(zb[2])
                  and ref[1].startswith("S"))
            bad += not ok
            print(f"SAVE {dev:7} {zb_m:30} printer {zb[1]!r:.60}  "
                  f"listed {len(listed(zb[2]))}  {'SAME' if ok else 'DIVERGES'}")
            if not ok:
                print(f"      ref {ref[1]!r:.80} {listed(ref[2])}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: SAVE to LPT: / CRT: / GRP: as on the VG-8020 "
          f"and the CF-3300")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
