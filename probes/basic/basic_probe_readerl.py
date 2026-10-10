# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-READERL (gate: readerl-acceptance): a DATA item READ refuses is a Syntax
error IN THE DATA LINE, as on the VG-8020 -- ERL, the printed `in <line>` and
`LIST .` all name it, in a program and from a READ typed at the prompt -- while
RESUME NEXT still goes on after the READ. Found 2026-10-09 by D-READFLT's rows
(zerobas named the READ line). On the way: after a refused item zerobas's DATA
line pointer had already moved to the program's end, so the next DATA line was
lost (`after`).

  trapped    10 ON ERROR GOTO 90 / 20 DATA 12X / 30 READ A / 90 PRINT ERR;ERL
  untrap     20 DATA 12X / 30 READ A / RUN         -> the printed message
  listdot    the same, then LIST .
  direct     20 DATA 12X, `READ A` typed, PRINT ERL
  directdot  10 PRINT / 20 DATA 12X, LIST 10, `READ A` typed, LIST .
  after      a refused READ A, RESUME NEXT, READ A$ (the item), READ B (next line)
  reraise    ON ERROR GOTO 0 in a handler (control: the message's line)

Prints `ROW <name> VG=[...] ZB=[...] <SAME|DIVERGES>`; exit 0 all agree, 1 a
divergence, 2 the VG-8020 gave no reading.
Clean-room: typed BASIC in, the text screen out. VG-8020 vs zerobas NODISK.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
        return None
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    if "NEW" in r:
        r = r[r.index("NEW") + 1:]
    return " | ".join(x for x in r if x and x.strip() not in ("Ok", "ZB"))


def main():
    only = sys.argv[1:] or list(CASES)
    bad, blind = [], []
    for name in only:
        got = {}
        for side, m in (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK")):
            got[side] = rows(omsx_repl.run_cases(m, [("direct", CASES[name])], batch=False,
                                                 reset=("", "SCREEN 0:WIDTH 40"),
                                                 step=3.0)[0])
        if got["VG"] is None:
            verdict = "NO-REFERENCE"
            blind.append(name)
        elif got["VG"] == got["ZB"]:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad.append(name)
        print(f"ROW {name} VG=[{got['VG']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: the VG-8020 gave no reading on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: a refused DATA item names its own line "
          f"({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
