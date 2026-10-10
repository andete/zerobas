# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FCBSHAPE FCB #0 (2026-10-10), measure first: does the reference keep FCB #0
at every MAXFILES, MAXFILES=0 included -- VARPTR(#0) an address, and the
MAXFILES 0 -> 1 step 267 B like the others?

  m0   MAXFILES=0: FRE(0), VARPTR(#0)
  m1   MAXFILES=1: FRE(0), VARPTR(#0), VARPTR(#1)
  m2   MAXFILES=2: FRE(0), VARPTR(#0), VARPTR(#1), VARPTR(#2)

Each row traps errors (ON ERROR prints ERR). VG-8020, CF-3300, zerobas NODISK.
Clean-room: typed BASIC in, the text screen out.
"""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402


def prog(n):
    vp = ";".join(f'"V{i}";VARPTR(#{i})' for i in range(0, max(n, 0) + 1))
    return ["NEW", f"MAXFILES={n}", "10 ON ERROR GOTO 90",
            f'20 PRINT "F";FRE(0);{vp}', "30 END", '90 PRINT "E";ERR:RESUME NEXT', "RUN"]


def rows(scr):
    if scr is None:
        return "<NO CAPTURE>"
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    if "RUN" in r:
        r = r[r.index("RUN") + 1:]
    return " | ".join(x for x in r if x and x.strip() not in ("Ok", "ZB"))


for m in sys.argv[1:] or ["Philips_VG_8020", "National_CF-3300", "C-BIOS_MSX1_EU_REPACK_NODISK"]:
    for n in (0, 1, 2):
        kw = {}
        if "CF-3300" in m or "DISK" in m and "NODISK" not in m:
            dsk = probe_tmp.tmp(f"fcb0_{m}_{n}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            kw = dict(diska=dsk, boot=14.0)
        scr = omsx_repl.run_cases(m, [("direct", prog(n))], batch=False,
                                  reset=("", "SCREEN 0:WIDTH 40"), step=3.0, **kw)[0]
        print(f"{m:30s} m{n} [{rows(scr)}]", flush=True)
