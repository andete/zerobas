#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-ENDCLOSE (docs/disk/port-readiness.md gap 5): DOES `END` CLOSE AN OPEN FILE? A disk file and `CRT:`, on the
VG-8020 + Sony HBD-F1, the National CF-3300 and zerobas.

Joost 2026-11-25: "yes, measure that". kstop.py's goldfish pass found the VG-8020 answering `File not OPEN` to a
`PRINT #1` after a program that OPENed "CRT:" and ENDed, where zerobas prints; END.md's "open files stay open" was
measured on the CF-3300 with a disk file. So the references may split by machine or by device. Each machine boots a
copy of disk/test720.dsk and types, boot per case:

    10 OPEN "<dev>" FOR OUTPUT AS #1:END     RUN     PRINT #1,"[X]"

where <dev> is a disk file (T.TXT) or CRT:. Reading: CLOSED when the screen says `File not OPEN` (END closed it),
OPEN when `[X]` was printed after the PRINT # line (it stayed open), else the rows as they are.

The VG-8020 + HBD-F1 is composed here (`Philips_VG_8020_HBDF1` in openMSX's user machines): openMSX's own
Philips_VG_8020 config with its external slot 1 holding the Sony_HBD-F1 extension's drive -- the shape of the
Philips_VG_8020_NMS1200 machine the spec rows use -- since run_cases takes no -ext.

Clean room: typed BASIC in, the screen out. Exit 0 when both references close and zerobas's open files read as pinned
(D-ENDCLOSE); 1 otherwise; 2 a missing reading.
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "tools"))
# zerobas MEASURED, never replayed -- also when run by hand (the default store mode serves zerobas readings too)
os.environ.setdefault("ZEROBAS_REFCACHE", "refs")
import omsx_repl  # noqa: E402
import openmsx_paths  # noqa: E402
import probe_tmp  # noqa: E402

VG_HBD = "Philips_VG_8020_HBDF1"
MACHINES = (("VG", VG_HBD), ("CF", "National_CF-3300"), ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK"))
DEVICES = (("disk", "T.TXT"), ("crt", "CRT:"))


def compose_vg_hbd():
    """openMSX's VG-8020 with the HBD-F1's drive in slot 1 (from the two stock configs; nothing hand-written)"""
    share = openmsx_paths.find_share(None)
    vg = open(os.path.join(share, "machines", "Philips_VG_8020.xml")).read()
    ext = open(os.path.join(share, "extensions", "Sony_HBD-F1.xml")).read()
    m = re.search(r'<secondary slot="any">\s*(<WD2793.*?</WD2793>)\s*</secondary>', ext, re.S)
    if not m:
        raise SystemExit("endclose: the Sony_HBD-F1 extension's WD2793 block was not found")
    block = f'<primary slot="1">\n      <secondary slot="0">\n        {m.group(1)}\n      </secondary>\n    </primary>'
    if vg.count('<primary external="true" slot="1"/>') != 1:
        raise SystemExit("endclose: the VG-8020 config's external slot 1 was not found once")
    vg = vg.replace('<primary external="true" slot="1"/>', block)
    # the extension's ROM is named relative to the share's systemroms; the machine's own <rom>s resolve the same way
    out = os.path.join(openmsx_paths.find_user_share(None), "machines", VG_HBD + ".xml")
    openmsx_paths.publish(out, vg)


def reading(raw, dev):
    if raw is None:
        return "<NO OUTPUT>"
    rows = [raw[i:i + 40].strip() for i in range(0, len(raw), 40)]
    after = rows[next((i for i, r in enumerate(rows) if r.startswith('PRINT #1,"[X]"')), len(rows)) + 1:]
    text = " / ".join(r for r in after if r and r not in ("Ok", "ZB"))
    if "not OPEN" in text:
        return "CLOSED (File not OPEN)"
    if "[X]" in text:
        return "OPEN ([X] printed)"
    if dev == "disk" and not any(w in text for w in ("error", "Error", "not ")):
        return "OPEN (no error: the PRINT # went into the file)"
    return f"? {text!r}"


def main():
    compose_vg_hbd()
    got = {}
    for side, m in MACHINES:
        for dev, name in DEVICES:
            dsk = probe_tmp.tmp(f"endclose_{side}_{dev}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            raw = omsx_repl.run_cases(m, [("direct", ["NEW", f'10 OPEN "{name}" FOR OUTPUT AS #1:END', "RUN",
                                                       'PRINT #1,"[X]"'])],
                                      batch=False, diska=dsk, boot=14.0, reset=("", "SCREEN 0"), step=3.0)[0]
            got[(side, dev)] = reading(raw, dev)
    blind = [k for k, v in got.items() if v.startswith("<NO")]
    for dev, _ in DEVICES:
        print(f"ROW {dev:4s}  " + "  ".join(f"{side}=[{got[(side, dev)]}]" for side, _ in MACHINES))
    if blind:
        print(f"\nINSTRUMENT FAULT: no reading on {blind}")
        return 2
    # MEASURED 2026-11-26 (scratchpad/AE_endclose1.out): both references CLOSE, for a disk file and CRT: alike -- no
    # split, so no ruling is needed. zerobas leaves both open: D-ENDCLOSE, pinned as KNOWN. A reference moving means
    # the instrument did; zerobas closing means the fix landed and the pin must go.
    bad = [f"{side} {dev}" for side in ("VG", "CF") for dev, _ in DEVICES if not got[(side, dev)].startswith("CLOSED")]
    zb = {dev: got[("ZB", dev)] for dev, _ in DEVICES}
    fixed = [dev for dev, v in zb.items() if v.startswith("CLOSED")]
    odd = [dev for dev, v in zb.items() if not v.startswith(("CLOSED", "OPEN"))]
    if fixed:
        print(f"🔴 D-ENDCLOSE FIXED on {fixed}: drop the KNOWN pin")
    ok = not bad and not fixed and not odd
    print(f"\n{'PASS' if ok else 'FAIL'}: both references close every file at END"
          + (" (zerobas's open files pinned: D-ENDCLOSE)" if ok else f" -- references {bad}, zerobas odd {odd}"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
