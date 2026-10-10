# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BOOTKEYS (gate: bootkeys-acceptance): SHIFT held at power-on keeps Disk
BASIC out, as on the CF-3300. Measured 2026-10-10 (scratchpad/bootkeys_run.out):
the CF-3300 with SHIFT has no Disk BASIC -- DSKF(0) is Illegal function call,
HIMEM $F380; CTRL keeps it with ONE drive. zerobas ignored both keys.

The key is pressed in the Tcl prologue (before the machine runs) and released 6
emulated seconds later; a program then reports DSKF(0) under ON ERROR.

  plain   no key        -> DSKF answers (Disk BASIC present)
  shift   SHIFT held    -> ERR 5 at DSKF (Disk BASIC absent)
  ctrl    CTRL held     -> DSKF answers. NOT compared here: the drive count
                           (D-DSKIB's drive-B model) and HIMEM (zerobas keeps its
                           own workspace at $E000+: the TIER 4 RAM layout)

Prints `ROW <name> CF=[...] ZB=[...] <SAME|DIVERGES>`; exit 0 all agree, 1 a
divergence, 2 the CF-3300 gave no reading.
Clean-room: the key matrix in; typed BASIC out.
"""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

KEYS = {"plain": None, "shift": (6, 0x01), "ctrl": (6, 0x02)}
LINES = ["10 ON ERROR GOTO 90", '20 PRINT "K";DSKF(0)', "30 END",
         '90 PRINT "E";ERR;ERL:END', "RUN"]


def rows(scr):
    if scr is None:
        return None
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    if "RUN" in r:
        r = r[r.index("RUN") + 1:]
    return " | ".join(x for x in r if x and x.strip() not in ("Ok", "ZB"))


def main():
    only = sys.argv[1:] or list(KEYS)
    bad, blind = [], []
    for name in only:
        key = KEYS[name]
        got = {}
        for side, m in (("CF", "National_CF-3300"), ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK")):
            dsk = probe_tmp.tmp(f"bootkeys_{name}_{m}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            pro = () if key is None else (f"keymatrixdown {key[0]} {key[1]}",
                                          f"after time 6 {{ keymatrixup {key[0]} {key[1]} }}")
            got[side] = rows(omsx_repl.run_cases(m, [("direct", LINES)], batch=False,
                                                 diska=dsk, boot=14.0,
                                                 reset=("", "SCREEN 0:WIDTH 40"), step=4.0,
                                                 run_gap=10.0, prologue=pro)[0])
        if got["CF"] is None:
            verdict = "NO-REFERENCE"
            blind.append(name)
        elif got["CF"] == got["ZB"]:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad.append(name)
        print(f"ROW {name} CF=[{got['CF']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: the CF-3300 gave no reading on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: keys held at power-on "
          f"({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
