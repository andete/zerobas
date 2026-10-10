# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-READERL measurement (2026-10-10): which line a bad DATA item's error names,
and what goes with it, on the VG-8020 and zerobas NODISK.

  trapped   10 ON ERROR GOTO 90 / 20 DATA 12X / 30 READ A / 40 END /
            90 PRINT ERR;ERL:END
  untrap    20 DATA 12X / 30 READ A / RUN            -> the message as printed
  listdot   the same, then `LIST .`                  -> which line `.` is
  direct    20 DATA 12X, then `READ A` typed, `PRINT ERL`

Clean-room: typed BASIC in, the text screen out.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

CASES = {
    "trapped": ["NEW", "10 ON ERROR GOTO 90", "20 DATA 12X", "30 READ A", "40 END",
                "90 PRINT ERR;ERL:END", "RUN"],
    "untrap": ["NEW", "20 DATA 12X", "30 READ A", "RUN"],
    "listdot": ["NEW", "20 DATA 12X", "30 READ A", "RUN", "LIST ."],
    "direct": ["NEW", "20 DATA 12X", "READ A", "PRINT ERL"],
    "directdot": ["NEW", "10 PRINT", "20 DATA 12X", "LIST 10", "READ A", "LIST ."],
    "after": ["NEW", "10 ON ERROR GOTO 90", "20 DATA 12X", "25 DATA 5", "30 READ A",
              "40 READ A$:READ B:PRINT A$;B:END", "90 RESUME NEXT", "RUN"],
    "reraise": ["NEW", "10 ON ERROR GOTO 100", "20 ERROR 7", "30 END",
                "100 ON ERROR GOTO 0", "RUN"],
}


def rows(scr):
    if scr is None:
        return "<NO CAPTURE>"
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    if "NEW" in r:
        r = r[r.index("NEW") + 1:]
    return " | ".join(x for x in r if x and x.strip() not in ("Ok", "ZB"))


for name, lines in [(k, CASES[k]) for k in (sys.argv[1:] or CASES)]:
    got = {}
    for side, m in (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK")):
        got[side] = rows(omsx_repl.run_cases(m, [("direct", lines)], batch=False,
                                             reset=("", "SCREEN 0:WIDTH 40"), step=3.0)[0])
    print(f"{'==' if got['VG'] == got['ZB'] else '✗ '} {name}\n    VG [{got['VG']}]\n    ZB [{got['ZB']}]",
          flush=True)
