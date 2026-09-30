#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-VARPTRCH -- VARPTR(#n), built on D-FCBSHAPE's 265 B channel block.

The ADDRESS is machine-specific everywhere (D-VARPTRN), so every case reads an
axis that CAN agree: error-or-not, the ERR code, a DELTA between two addresses.
One case reads a raw address on purpose (`closed.1`) only to show it is an
address (non-zero) -- its value is printed as `ADDR`, never compared.

  stride    VARPTR(#2)-VARPTR(#1) at MAXFILES=2           (both refs: 265)
  shift     VARPTR(#1) at MAXFILES=1, then at 2 (two raw addresses: diff them)  (refs: 265 -- the FCB
            array hangs DOWN from $F380 and the 2 B pointer table sits BELOW it)
  edge      #0, #-1, #256, a string, a fraction, spaces, `#` alone
  hdr       PEEK(VARPTR(#1)) after OPEN "CRT:" FOR OUTPUT -- the FCB mode byte
            (refs: 2); D-FCBSHAPE's LEFT list says nothing writes it here yet
"""
from __future__ import annotations
import os, re, shutil, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

SIDES = {
    "vg8020": ("Philips_VG_8020", 14.0),
    "cf3300": ("National_CF-3300", 14.0),
    "zb":     ("C-BIOS_MSX1_EU_REPACK_DISK", 8.0),
    "zbnd":   ("C-BIOS_MSX1_EU_REPACK_NODISK", 8.0),
}
E = ['90 PRINT"[E";ERR;"]":END', "RUN"]
CASES = [
    ("closed.1", ['10 ON ERROR GOTO 90',
                  '20 PRINT"[";VARPTR(#1)<>0;"]"', "30 END"] + E),
    ("closed.2", ['10 ON ERROR GOTO 90',
                  '20 PRINT"[";VARPTR(#2);"]"', "30 END"] + E),
    ("stride",   ['10 ON ERROR GOTO 90', '20 MAXFILES=2',
                  '30 A=VARPTR(#1):B=VARPTR(#2)',
                  '40 PRINT"[";B-A;"]"', "50 END"] + E),
    ("stride3",  ['10 ON ERROR GOTO 90', '20 MAXFILES=3',
                  '30 A=VARPTR(#1):B=VARPTR(#3)',
                  '40 PRINT"[";B-A;"]"', "50 END"] + E),
    ("shift",    ['10 ON ERROR GOTO 90', '20 MAXFILES=1',
                  '30 PRINT"[";VARPTR(#1);"]"',
                  '40 MAXFILES=2',
                  '50 PRINT"[";VARPTR(#1);"]"', "60 END"] + E),
    ("ch0",      ['10 ON ERROR GOTO 90',
                  '20 PRINT"[";VARPTR(#0)<>0;"]"', "30 END"] + E),
    ("chneg",    ['10 ON ERROR GOTO 90',
                  '20 PRINT"[";VARPTR(#-1);"]"', "30 END"] + E),
    ("ch256",    ['10 ON ERROR GOTO 90',
                  '20 PRINT"[";VARPTR(#256);"]"', "30 END"] + E),
    ("chstr",    ['10 ON ERROR GOTO 90',
                  '20 PRINT"[";VARPTR(#"A");"]"', "30 END"] + E),
    ("chfrac",   ['10 ON ERROR GOTO 90', '20 MAXFILES=2',
                  '30 A=VARPTR(#1):B=VARPTR(#1.6)',
                  '40 PRINT"[";B-A;"]"', "50 END"] + E),
    ("spaces",   ['10 ON ERROR GOTO 90',
                  '20 PRINT"[";VARPTR( # 1 )<>0;"]"', "30 END"] + E),
    ("bare",     ['10 ON ERROR GOTO 90',
                  '20 PRINT"[";VARPTR(#);"]"', "30 END"] + E),
    ("noclose",  ['10 ON ERROR GOTO 90',
                  '20 PRINT"[";VARPTR(#1;"]"', "30 END"] + E),
    ("hdr",      ['10 ON ERROR GOTO 90',
                  '20 OPEN"CRT:"FOR OUTPUT AS#1',
                  '30 PRINT"[";PEEK(VARPTR(#1));"]"',
                  "40 END"] + E),
    ("typeint",  ['10 ON ERROR GOTO 90', '20 A#=VARPTR(#1)',
                  '30 PRINT"[";A#<0;"]"', "40 END"] + E),
]


def main() -> int:
    for _, lines in CASES:
        for ln in lines:
            if len(ln) > 38:
                print(f"INSTRUMENT FAULT: {len(ln)} cols: {ln!r}")
                return 2
    only = sys.argv[1:] or list(SIDES)
    out = {}
    for side in only:
        machine, boot = SIDES[side]
        kw = {}
        if side in ("cf3300", "zb"):
            tmp = tempfile.mkstemp(suffix=".dsk")[1]
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), tmp)
            kw["diska"] = tmp
        caps = omsx_repl.run_cases(machine, CASES, batch=False, boot=boot,
                                   reset=("", "SCREEN 0"), cap_gap=45.0,
                                   timeout=1800.0, **kw)
        vals = []
        for cap in caps:
            ms = re.findall(r"\[\s*(E?)\s*(-?\d+)\s*\]", cap or "")
            vals.append(" ".join(("ERR " + v) if e else v for e, v in ms)
                        if ms else "<NO OUTPUT>")
        out[side] = vals
    print(f"{'case':10s} " + " ".join(f"{s:>12s}" for s in only))
    for i, (name, _) in enumerate(CASES):
        print(f"{name:10s} " + " ".join(f"{out[s][i]:>12s}" for s in only))
    return 0


if __name__ == "__main__":
    sys.exit(main())
