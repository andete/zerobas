# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FILESBARE (gate: filesbare-acceptance): FILES with a blank or drive-only
pattern. Found 2026-09-05 (namspc `m.blank` / `m.drvbare`, deferred for main-ROM
bytes) and re-filed 2026-10-09: the CF-3300 lists the whole disk for
`FILES " "` and `FILES "A:"`, zerobas said Bad file name.

  blank    FILES " "        empty    FILES ""        drv      FILES "A:"
  drvlow   FILES "a:"       drvsp    FILES "A: "     baddrv   FILES "Q:"  (62)
  pat      FILES "HI.*"     (control: a real pattern)

Each row prints `ROW <name> CF=[...] ZB=[...] <verdict>`.
Exit 0 all agree; 1 a divergence; 2 the CF-3300 gave no reading.
Clean-room: typed BASIC in, the text screen out. CF-3300 vs zerobas DISK, each
on a private copy of disk/test720.dsk (6 files).
"""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

SPECS = {"blank": '" "', "empty": '""', "drv": '"A:"', "drvlow": '"a:"', "drvsp": '"A: "',
         "baddrv": '"Q:"', "pat": '"HI.*"'}


def lines(spec):
    return ["10 ON ERROR GOTO 90", f"20 FILES {spec}", '30 PRINT:PRINT "[OK]":END',
            '90 PRINT "ERR";ERR:END', "RUN"]


def rows(scr):
    if scr is None:
        return None
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    if "RUN" in r:
        r = r[r.index("RUN") + 1:]
    return " | ".join(x for x in r if x and x.strip() not in ("Ok", "ZB"))


def main():
    only = sys.argv[1:] or list(SPECS)
    bad, blind = [], []
    for name in only:
        got = {}
        for side, m in (("CF", "National_CF-3300"), ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK")):
            dsk = probe_tmp.tmp(f"filesbare_{name}_{m}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            got[side] = rows(omsx_repl.run_cases(m, [("direct", lines(SPECS[name]))], batch=False,
                                                 diska=dsk, boot=14.0,
                                                 reset=("", "SCREEN 0:WIDTH 40"), step=4.5,
                                                 run_gap=20.0)[0])
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
    print(f"\n{'PASS' if not bad else 'FAIL'}: FILES with a blank or drive-only pattern "
          f"({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
