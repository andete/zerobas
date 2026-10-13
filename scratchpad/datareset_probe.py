#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DATARESET, measured: what does `Out of DATA` do to the DATA position?

Found while measuring DATPTR for Joost's official-cell rule (datptr_probe.py:
after `Out of DATA` the VG-8020's DATPTR reads TXTTAB-1, the unpositioned
value). If the position REWINDS, a READ after RESUME NEXT starts over.

  resume-read   READ A,B past a one-item DATA, RESUME NEXT, READ C
  err-twice     the same, counting the handler's runs
  restore-ood   RESTORE 60 first: does it rewind to the top or to line 60?
  ptr-after     DATPTR after the out-of-data error that followed RESTORE 60

Prediction: the VG-8020 rewinds (C = 5, the handler runs once); zerobas stays
exhausted (C = 0, twice). Typed BASIC; the published DATPTR address.
BEFORE the fix (2026-10-13, read off the run; the .out is the AFTER run):
  resume-read VG `5 5` / zerobas `5 0`; err-twice VG `5 1` / zerobas `5 2`;
  restore-ood VG `7 7` / zerobas `7 0`; ptr-after VG 32806 / zerobas 0.
  🔮 HIT on both predictions. After: the three behaviour rows agree; ptr-after
  still differs (DATPTR is not zerobas's cell yet -- the next official-cell move).
"""
import os, sys
os.environ["ZEROBAS_REFCACHE"] = "0"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

P = "PEEK(&HF6C8)+256*PEEK(&HF6C9)"
CASES = {
    "resume-read": ["10 ON ERROR GOTO 100", "20 READ A,B", '30 READ C:?"["A;C"]":END',
                    "40 DATA 5", "100 RESUME NEXT", "RUN"],
    "err-twice": ["10 ON ERROR GOTO 100", "20 READ A,B", "30 READ C", '40 ?"["A;E"]":END',
                  "50 DATA 5", "100 E=E+1:RESUME NEXT", "RUN"],
    "restore-ood": ["10 ON ERROR GOTO 100", "20 RESTORE 60:READ A,B", '30 READ C:?"["A;C"]":END',
                    "50 DATA 5", "60 DATA 7", "100 RESUME NEXT", "RUN"],
    "ptr-after": ["10 ON ERROR GOTO 100", "20 RESTORE 60:READ A,B", "50 DATA 5", "60 DATA 7",
                  f'100 ?"["{P}"]":END', "RUN"],
}


def main():
    for n, lines in CASES.items():
        for m in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"):
            raw = omsx_repl.run_cases(m, [("direct", ["NEW"] + lines)], batch=False,
                                      reset=("", "SCREEN 0"), run_gap=6.0)[0]
            print(f"{n:12s} {m[:28]:28s} {omsx_repl.result_span(raw) if raw else None}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
