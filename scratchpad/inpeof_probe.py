#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO S9 prep: LINE INPUT# past the end of a TAPE data file, diskless.

seq_end (basic/files.asm) raises whatever DISKOP_ERR holds before it tests for
55, and on a diskless machine nothing writes DISKOP_ERR -- so reading past the
end of a CAS: file may raise a stale code where the VG-8020 says `Input past
end` (55). Our own tape: one ASCII file "D" holding one line. Rows:
  eof    OPEN"CAS:D", two LINE INPUT# (the second is past the end), at power-on
  eofv   the same after `POKE <DISKOP_ERR>,165` -- what a load over the
         workspace leaves there (the address read from build/basic-reloc.sym)
  eofm   the POKE between the two reads (added after eofv read 55: MISS)
PREDICTED, before the run: VG-8020 `[E 55  20 ][HELLO]` on both rows; zerobas
`eof` SAME iff DISKOP_ERR powers on 0 (unknown), `eofv` `[E 165 ...]`.
VG-8020 vs zerobas NODISK, typed BASIC in, the text screen out.
"""
import os, re, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                         # noqa: E402
from cas_encode import build_cas_ascii                   # noqa: E402

def sym(name):
    for ln in open(os.path.join(REPO, "build", "basic-reloc.sym")):
        m = re.match(rf"{name}\s+EQU\s+0*([0-9A-F]+)H", ln)
        if m:
            return int(m.group(1), 16)
    raise SystemExit(f"no {name} in the sym")

ERRCELL = sym("DISKOP_ERR")
BODY = ['20 OPEN"CAS:D"FOR INPUT AS#1:LINE INPUT#1,A$:LINE INPUT#1,B$',
        '30 PRINT"[";A$;"]":END', '100 PRINT"[E";ERR;ERL;"]";:RESUME 30', "RUN"]
CASES = {"eof": ["NEW", "10 ON ERROR GOTO 100"] + BODY,
         "eofv": ["NEW", f"10 ON ERROR GOTO 100:POKE &H{ERRCELL:04X},165"] + BODY,
         # after the OPEN and the first read, so nothing on the tape path can clear it first
         "eofm": ["NEW", "10 ON ERROR GOTO 100",
                  f'20 OPEN"CAS:D"FOR INPUT AS#1:LINE INPUT#1,A$:POKE &H{ERRCELL:04X},165:LINE INPUT#1,B$']
                 + BODY[1:]}

def main():
    cas = os.path.join(tempfile.mkdtemp(prefix="inpeof_"), "t.cas")
    open(cas, "wb").write(build_cas_ascii("D", "HELLO\r\n"))
    print(f"DISKOP_ERR = ${ERRCELL:04X} on zerobas (the VG-8020 row pokes the same address: free RAM there)")
    for tag, prog in CASES.items():
        got = {}
        for side, m in (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK")):
            cap = omsx_repl.run_cases(m, [("direct", prog)], batch=False,
                                      reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                                      run_gap=40.0, cassette=cas)[0]
            rows = [cap[i:i + 40].strip() for i in range(0, len(cap or ""), 40)]
            got[side] = " | ".join(r for r in rows if r.startswith("[") or "rror" in r) or "<NO OUTPUT>"
        print(f"ROW {tag:5} VG=[{got['VG']}] ZB=[{got['ZB']}] {'SAME' if got['VG'] == got['ZB'] else 'DIFFERS'}", flush=True)
    return 0

if __name__ == "__main__":
    sys.exit(main())
