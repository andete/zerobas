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
from cas_encode import build_cas, build_cas_ascii, build_cas_basic_csave   # noqa: E402

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
         "bare_r": 'AB",R:REM "',
         # run 5 (2026-10-17: a per-position witness says Harry Fox's line-50 name
         # differs in positions 5 and 6 only -- a separator inside the name?):
         "dot": "CAS:ABCD.EF",                         # header "ABCD.E" (the first six)
         "dot2": "CAS:AB.C",                           # header "AB.C"
         "dotx": "CAS:ABCD.E",                         # header "ABCD.E", request exactly six
         # run 5b: the VG-8020 SKIPS all three -- is the name cut at the dot?
         "dotsp": "CAS:ABCD.EF",                       # header "ABCD" (space padded)
         "dot2sp": "CAS:AB.C",                         # header "AB"
         "dotlong": "CAS:ABCDEFGH.IJ",                 # header "ABCDEF"
         # run 5c: which verbs cut at the dot? SAVE"CAS:" does, CSAVE does not
         # (probes/basic/basic_probe_cassave.py sav-cas-dot / csave-dot). A form
         # starting with '!' is the whole typed line.
         "bbare": "AB.C",                              # bare BLOAD, header "AB"
         "open": '!OPEN"CAS:AB.C" FOR INPUT AS #1:PRINT"[OK]"',   # ASCII header "AB"
         "run": '!RUN"CAS:AB.C"',                      # ASCII header "AB", prints [OK]
         "cload": '!CLOAD"AB.C":PRINT"[OK]"',          # tokenised header "AB"
         "cloadraw": '!CLOAD"AB.C":PRINT"[OK]"',       # tokenised header "AB.C"
         "lead": "CAS:.AB",                            # nothing before the dot: tape "AB", "ZZ"
         "leadopen": '!OPEN"CAS:.AB" FOR INPUT AS #1:PRINT"[OK]"',   # the same, in main
         # run 7: LOAD and MERGE take the same `dev:name` (ASCII header "AB")
         "load": '!LOAD"CAS:AB.C":PRINT"[OK]"',
         "merge": '!MERGE"CAS:AB.C":PRINT"[OK]"'}                      # bare + ,R (the REM eats the tail quote)
TAPE = build_cas("AB", 0xD000, 0xD000, bytes([0xC9])) + build_cas("ZZ", 0xD000, 0xD000, bytes([0xC9]))
_KN = build_cas("KN", 0xD000, 0xD000, bytes([0xC9]))      # cas_encode encodes ASCII only:
assert _KN.count(b"KN    ") == 1                            # patch the 2 header-name bytes
TAPES = {"kana": _KN.replace(b"KN    ", b"\xB1\xB2    ") + build_cas("ZZ", 0xD000, 0xD000, bytes([0xC9])),
         "long": build_cas("ABCDEF", 0xD000, 0xD000, bytes([0xC9])) + build_cas("ZZ", 0xD000, 0xD000, bytes([0xC9])),
         "prefix": build_cas("ABCDEF", 0xD000, 0xD000, bytes([0xC9])) + build_cas("ZZ", 0xD000, 0xD000, bytes([0xC9]))}
_ZP = build_cas("AB", 0xD000, 0xD000, bytes([0xC9]))
assert _ZP.count(b"AB    ") == 1
for _k, _h in (("dot", "ABCD.E"), ("dot2", "AB.C"), ("dotx", "ABCD.E"), ("dotsp", "ABCD"),
               ("dot2sp", "AB"), ("dotlong", "ABCDEF")):
    TAPES[_k] = build_cas(_h, 0xD000, 0xD000, bytes([0xC9])) + build_cas("ZZ", 0xD000, 0xD000, bytes([0xC9]))
_ZZ = build_cas("ZZ", 0xD000, 0xD000, bytes([0xC9]))
TAPES["bbare"] = build_cas("AB", 0xD000, 0xD000, bytes([0xC9])) + _ZZ
TAPES["open"] = build_cas_ascii("AB", "1\r\n") + _ZZ
TAPES["run"] = build_cas_ascii("AB", '10 PRINT"[OK]"\r\n') + _ZZ
TAPES["load"] = build_cas_ascii("AB", '10 REM\r\n') + _ZZ
TAPES["merge"] = build_cas_ascii("AB", '10 REM\r\n') + _ZZ
TAPES["cload"] = build_cas_basic_csave("AB", bytes([0, 0])) + _ZZ
TAPES["cloadraw"] = build_cas_basic_csave("AB.C", bytes([0, 0])) + _ZZ
TAPES["zpad"] = _ZP.replace(b"AB    ", b"AB\x00\x00\x00\x00") + build_cas("ZZ", 0xD000, 0xD000, bytes([0xC9]))
MACHINES = (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK"))


def rows(scr):
    if scr is None:
        return None
    r = [scr[i:i + 40].strip() for i in range(0, len(scr), 40)]
    return " | ".join(x for x in r if x.startswith(("Found", "Skip", "[")) or "rror" in x
                      or "file name" in x)          # run 6: `Bad file name` has no "rror"


def main():
    tmp = tempfile.mkdtemp(prefix="casname_")
    for name in (sys.argv[1:] or list(FORMS)):
        path = os.path.join(tmp, f"{name}.cas")
        open(path, "wb").write(TAPES.get(name, TAPE))
        got = {}
        for side, m in MACHINES:
            f = FORMS[name]
            lines = ['N$="A"+"B"', f[1:] if f.startswith("!") else f'BLOAD"{f}":PRINT"[OK]"']
            got[side] = rows(omsx_repl.run_cases(m, [("direct", lines)], batch=False,
                                                 reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                                                 run_gap=25.0, cassette=path)[0])
        print(f"ROW {name} VG=[{got['VG']}] ZB=[{got['ZB']}] "
              f"{'SAME' if got['VG'] == got['ZB'] else 'DIVERGES'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
