#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CASOFS2X measure-first (2026-10-19): does tape `BLOAD"CAS:T",R,offset` run the code
at exec + offset (the reference?) or exec + 2 x offset (found by reading zerobas's
bload-body.inc: load_done falls into bl_apply_ofs after the offset was applied)?

OUR OWN tape (cas_encode): a 6-byte routine, start = exec = &HD000, that stores 42 in
&HD3F0. Before the load a DECOY is POKEd at &HD200 that stores 99 there. With offset
&H100 the routine lands at &HD100: exec + offset runs it (42); exec + 2 x offset runs
the decoy (99). Rows:
  plain   BLOAD"CAS:T",R            (no offset: the routine at &HD000 -> 42)
  ofsr    BLOAD"CAS:T",R,&H100       the subject
  ofsdat  BLOAD"CAS:T",&H100         no ,R: where did the bytes land? (PEEK &HD100)
Prints ROW <name> VG=[...] ZB=[...] <verdict>. VG-8020 vs zerobas NODISK.
"""
import os, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
from cas_encode import build_cas                    # noqa: E402

CODE = bytes([0x3E, 42, 0x32, 0xF0, 0xD3, 0xC9])    # ld a,42 / ld (&HD3F0),a / ret
DECOY = "FOR I=0 TO 5:POKE &HD200+I,VAL(MID$(\"062099050240211201\",I*3+1,3)):NEXT"
ARM = "POKE &HD3F0,0:POKE &HD100,0:" + DECOY
CASES = {
    "plain":  [ARM, 'BLOAD"CAS:T",R:PRINT"[";PEEK(&HD3F0);"]"'],
    "ofsr":   [ARM, 'BLOAD"CAS:T",R,&H100:PRINT"[";PEEK(&HD3F0);"]"'],
    "ofsdat": [ARM, 'BLOAD"CAS:T",&H100:PRINT"[";PEEK(&HD100);PEEK(&HD3F0);"]"'],
}


def rows(scr):
    if scr is None:
        return None
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    keep = [x for x in r if x.startswith("[") or "error" in x.lower()]
    return " | ".join(keep)


def main():
    tmp = tempfile.mkdtemp(prefix="casofs_")
    path = os.path.join(tmp, "t.cas")
    open(path, "wb").write(build_cas("T", 0xD000, 0xD000, CODE))
    for name, lines in CASES.items():
        got = {}
        for side, m in (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK")):
            got[side] = rows(omsx_repl.run_cases(m, [("direct", lines)], batch=False,
                                                 reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                                                 run_gap=30.0, cassette=path)[0])
        v = "NO-REFERENCE" if not got["VG"] else ("SAME" if got["VG"] == got["ZB"] else "DIVERGES")
        print(f"ROW {name} VG=[{got['VG']}] ZB=[{got['ZB']}] {v}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
