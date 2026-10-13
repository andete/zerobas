#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LISTLPTR: how does LIST show a `$0D` line POINTER?

The VG-8020 rewrites a jump's `$0E <line number>` into `$0D <pointer>` in place
when it runs (lptr_bytes, measured: `10 GOTO 20` stores `0E 14 00` at $8007, and
after RUN `0D 0A 80` -- $800A, the byte BEFORE line 20 at $800B). A program saved
after it ran -- a BASIC cartridge -- carries the pointer form, and zerobas's
detokeniser prints the pointer as if it were the number.

  run   VG-8020 only: RUN, then LIST (the reference's own path)
  poke  both: the same three bytes POKEd in, then LIST; and RUN, which must
        still work (zerobas reads `$0D` at GOTO since D-BASICROM)

Prediction (2026-10-13): VG-8020 `10 GOTO 20` both ways; zerobas
`10 GOTO 32778` (the pointer as a number) -- RUN still fine.
"""
import os, sys
os.environ.setdefault("ZEROBAS_REFCACHE", "0")
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(_R, "probes", "lib")]
import omsx_repl                                   # noqa: E402

PROG = ["NEW", "10 GOTO 20", "20 END"]
POKE = "POKE &H8007,13:POKE &H8008,10:POKE &H8009,128"
CASES = [("run", ("Philips_VG_8020",), PROG + ["RUN", "CLS", "LIST"]),
         ("poke", ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"),
          PROG + [POKE, "CLS", "LIST", 'RUN:PRINT"RAN"'])]


def listed(raw):
    s = (raw or "").replace("\n", "")
    rows = [s[i:i + 40].strip() for i in range(0, len(s), 40)]
    return [r for r in rows if r.startswith(("10 ", "20 ")) or "RAN" in r]


def main():
    for name, machines, lines in CASES:
        for m in machines:
            raw = omsx_repl.run_cases(m, [("direct", lines)], batch=False, reset=("",),
                                      run_gap=4.0)[0]
            print(f"{name:5s} {m:30s} {listed(raw)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
