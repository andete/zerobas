#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BASICINT2 (2026-10-16, Demonia `Syntax error in 50`): what do the BASIC-ROM
internals $72E9 and $72D4 do? Demonia's machine code calls $72E9 once (HL=$A000,
DE=$A600; it returns 2.3 s later) and then $72D4 ~3000 times (HL stepping, a byte
back in A every ~3 ms) -- a tape read. Black-box, our own stub and our own tape:

  read   POKE a stub that calls $72E9, then $72D4 sixteen times into $D100.. ;
         the tape is our own ASCII file "D" -- its 10-byte header id ($EA x 10),
         the 6-byte name, then the data block. PEEK the 16 bytes back.
  notape the same stub with NO cassette inserted: what does $72E9 answer?
  break  no cassette, Ctrl-STOP after 15 s inside $72E9: the error it raises
  stop   DATA past the block: read 40 bytes from a short tape (the header block is
         16 bytes, the data block ~260): does $72D4 cross into the next block?

The VG-8020's printed lines are the oracle (no ROM byte is read).
"""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "probes", "lib"))
import omsx_repl
from cas_encode import build_cas_ascii

STUB = lambda n: [0xCD, 0xE9, 0x72, 0x21, 0x00, 0xD1, 0x06, n, 0xCD, 0xD4, 0x72, 0x77, 0x23,
                  0x10, 0xF9, 0xC9]


def prog(n, on_error=True):
    data = ",".join(str(b) for b in STUB(n))
    return ["NEW",
            "10 CLEAR 1000,&HD000" + (":ON ERROR GOTO 100" if on_error else ""),
            f"20 FOR I=0 TO 15:READ X:POKE &HD000+I,X:NEXT:FOR I=0 TO {n - 1}:POKE &HD100+I,0:NEXT",
            "30 DEFUSR=&HD000:A=USR(0)",
            f'40 FOR J=0 TO {n - 1} STEP 8:S$="":FOR I=J TO J+7:S$=S$+" "+HEX$(PEEK(&HD100+I)):NEXT',
            '50 PRINT"[B";J;S$:NEXT:END',
            f"60 DATA {data}",
            '100 PRINT"[E";ERR;ERL;"]":END',
            "RUN"]


def main():
    tmp = tempfile.mkdtemp(prefix="bint_")
    tape = os.path.join(tmp, "d.cas")
    open(tape, "wb").write(build_cas_ascii("D", "ABCDEFGH\r\n"))
    cases = [("read", prog(16), tape), ("notape", prog(16), None), ("stop", prog(40), tape),
             # Ctrl-STOP while $72E9 waits for a leader that never comes
             ("break", prog(16) + ["@WAIT15", "@BREAK", "@WAIT5"], None)]
    for name, p, cas in cases:
        for m in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"):
            kw = dict(batch=False, reset=("", "SCREEN 0:WIDTH 40"), step=3.0, run_gap=40.0)
            if cas:
                kw["cassette"] = cas
            scr = omsx_repl.run_cases(m, [("direct", p)], **kw)[0]
            r = [scr[i:i + 40].strip() for i in range(0, len(scr), 40)] if scr else ["<NO OUTPUT>"]
            keep = [x for x in r if x.startswith("[") or "rror" in x]
            print(f"{name:6} {m:30} {' | '.join(keep) or '<nothing matched>'}", flush=True)


if __name__ == "__main__":
    main()
