#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TAPELOAD class B2 (Harry Fox): which tape file-NAME forms does BLOAD match?

Harry Fox's line-50 load matches its second file on the VG-8020 and, on zerobas,
SKIPS it and every later file (the sub-ROM header search's binary skip, csd_bin)
until the tape ends -- so the name comparison differs. The requested name is in
the game's program, which is not read; instead OUR OWN tape (cas_encode: binary
file "AB", then binary file "ZZ") is searched with several name forms, and the
row is the screen: does `BLOAD ...` print Found:AB (and [OK]) or skip it?
  up      "CAS:AB"     (the control)
  low     "cas:AB"     lowercase device
  mixed   "Cas:AB"
  sp      "CAS: AB"    a space after the colon
  lowname "CAS:ab"     lowercase name vs an uppercase header
  trail   "CAS:AB  "   trailing spaces
PREDICTED, before the run: `low` (a lowercase device) separates the machines.
"""
import os, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
from cas_encode import build_cas                    # noqa: E402

FORMS = {"up": "CAS:AB", "low": "cas:AB", "mixed": "Cas:AB", "sp": "CAS: AB",
         "lowname": "CAS:ab", "trail": "CAS:AB  ",
         # run 2 (the first six forms match alike; `sp` / `lowname` skip alike):
         "kana": 'CAS:"+CHR$(177)+CHR$(178)+"',      # header name $B1 $B2 (tape KN)
         "expr": 'CAS:"+N$+"',                       # N$="AB" built at run time
         "long": "CAS:ABCDEFGH",                       # vs a 6-char header "ABCDEF" (tape LG)
         # run 3 (Harry Fox's search wants $41 -- BLOAD + a NAME -- and the header
         # IS $D0, so it is the name; every ordinary form above matches alike):
         "zpad": "CAS:AB",                             # header "AB" padded with $00
         "prefix": "CAS:ABC",                          # request shorter than the header "ABCDEF"
         # run 4 (Harry Fox still asks for a different name with an identical program):
         "bare": "AB",                                 # NO device: the diskless cassette
         "bare_r": 'AB",R:REM "'}                      # bare + ,R (the REM eats the tail quote)
TAPE = build_cas("AB", 0xD000, 0xD000, bytes([0xC9])) + build_cas("ZZ", 0xD000, 0xD000, bytes([0xC9]))
_KN = build_cas("KN", 0xD000, 0xD000, bytes([0xC9]))      # cas_encode encodes ASCII only:
assert _KN.count(b"KN    ") == 1                            # patch the 2 header-name bytes
TAPES = {"kana": _KN.replace(b"KN    ", b"\xB1\xB2    ") + build_cas("ZZ", 0xD000, 0xD000, bytes([0xC9])),
         "long": build_cas("ABCDEF", 0xD000, 0xD000, bytes([0xC9])) + build_cas("ZZ", 0xD000, 0xD000, bytes([0xC9])),
         "prefix": build_cas("ABCDEF", 0xD000, 0xD000, bytes([0xC9])) + build_cas("ZZ", 0xD000, 0xD000, bytes([0xC9]))}
_ZP = build_cas("AB", 0xD000, 0xD000, bytes([0xC9]))
assert _ZP.count(b"AB    ") == 1
TAPES["zpad"] = _ZP.replace(b"AB    ", b"AB\x00\x00\x00\x00") + build_cas("ZZ", 0xD000, 0xD000, bytes([0xC9]))
MACHINES = (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK"))


def rows(scr):
    if scr is None:
        return None
    r = [scr[i:i + 40].strip() for i in range(0, len(scr), 40)]
    return " | ".join(x for x in r if x.startswith(("Found", "Skip", "[")) or "rror" in x)


def main():
    tmp = tempfile.mkdtemp(prefix="casname_")
    for name in (sys.argv[1:] or list(FORMS)):
        path = os.path.join(tmp, f"{name}.cas")
        open(path, "wb").write(TAPES.get(name, TAPE))
        got = {}
        for side, m in MACHINES:
            lines = ['N$="A"+"B"', f'BLOAD"{FORMS[name]}":PRINT"[OK]"']
            got[side] = rows(omsx_repl.run_cases(m, [("direct", lines)], batch=False,
                                                 reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                                                 run_gap=25.0, cassette=path)[0])
        print(f"ROW {name} VG=[{got['VG']}] ZB=[{got['ZB']}] "
              f"{'SAME' if got['VG'] == got['ZB'] else 'DIVERGES'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
