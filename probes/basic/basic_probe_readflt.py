# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-READFLT (gate: readflt-acceptance): what READ makes of a NUMERIC DATA item.

READ used to parse a numeric item with an int16 scanner, so `DATA 1.5` / `2E3`
/ `-.25` were Syntax error and `DATA 40000` read back as -25536 -- where the
VG-8020 reads every one. Since D-READFLT the item goes through VAL's parser
(inp_num, the one INPUT uses). The rows pin what that must keep:

  frac big exp neg dbl int   the values themselves
  intovf e99                 Overflow: 99999 into A%, 1E99 (were D-READINTOVF,
                             D-READOVF)
  junk quote                 Syntax error: `12X`, `"5"`
  empty spaces hex sign      an empty item is 0; leading/trailing blanks;
                             &H / &B; a bare `-` / `.` is 0
  again                      a refused item is NOT consumed: READ refuses it again
  dbltyp                     the value is stored in the target's own type

KNOWN (filed, not this slice): junk / quote / again -- the reference names the
DATA line in `Syntax error in <line>` (ERL 20), zerobas the READ line
(D-READERL). They are reported, and do not fail the gate.

Each row prints `ROW <name> VG=[...] ZB=[...] <verdict>` (the knives read ZB).
Exit 0 every unknown row agrees; 1 a divergence; 2 the VG-8020 gave no reading.
Clean-room: typed BASIC in, the text screen out. VG-8020 vs zerobas NODISK.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

H = "10 ON ERROR GOTO 90"
CASES = {
    "frac":   [H, "20 DATA 1.5", "30 READ A:PRINT A"],
    "big":    [H, "20 DATA 40000", "30 READ A:PRINT A"],
    "exp":    [H, "20 DATA 2E3", "30 READ A:PRINT A"],
    "neg":    [H, "20 DATA -.25", "30 READ A:PRINT A"],
    "dbl":    [H, "20 DATA 1.23456789012", "30 READ A#:PRINT A#"],
    "int":    [H, "20 DATA 42", "30 READ A:PRINT A"],
    "intovf": [H, "20 DATA 99999", "30 READ A%:PRINT A%"],
    "e99":    [H, "20 DATA 1E99", "30 READ A:PRINT A"],
    "junk":   [H, "20 DATA 12X", "30 READ A:PRINT A"],
    "quote":  [H, '20 DATA "5"', "30 READ A:PRINT A"],
    "empty":  [H, "20 DATA ,7", "30 READ A,B:PRINT A;B"],
    "spaces": [H, "20 DATA   1.5  ,2", "30 READ A,B:PRINT A;B"],
    "hex":    [H, "20 DATA &H10,&B101", "30 READ A,B:PRINT A;B"],
    "sign":   [H, "20 DATA -,.", "30 READ A,B:PRINT A;B"],
    "again":  [H, "20 DATA HELLO,7", "30 READ A:PRINT A", "40 READ B:PRINT B", "50 END",
               '90 PRINT "ERR";ERR;"IN";ERL:RESUME NEXT'],
    "dbltyp": [H, "20 DATA 1.23456789012", "30 READ A!:PRINT A!"],
}
TAIL = ["40 END", '90 PRINT "ERR";ERR;"IN";ERL:END']
KNOWN = {"junk": "D-READERL", "quote": "D-READERL", "again": "D-READERL"}


def out(scr):
    if scr is None:
        return None
    rows = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    if "RUN" in rows:
        rows = rows[rows.index("RUN") + 1:]
    return " | ".join(r for r in rows if r and r not in ("Ok", "ZB"))


def main():
    only = sys.argv[1:] or list(CASES)
    bad, blind = [], []
    for name in only:
        lines = CASES[name]
        prog = ["NEW"] + lines + ([] if any(x.startswith("90 ") for x in lines) else TAIL) + ["RUN"]
        got = {}
        for side, m in (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK")):
            got[side] = out(omsx_repl.run_cases(m, [("direct", prog)], batch=False,
                                                reset=("", "SCREEN 0:WIDTH 40"), step=3.0)[0])
        if got["VG"] is None:
            blind.append(name)
            verdict = "NO-REFERENCE"
        elif got["VG"] == got["ZB"]:
            verdict = "SAME"
        elif name in KNOWN:
            verdict = f"KNOWN ({KNOWN[name]})"
        else:
            verdict = "DIVERGES"
            bad.append(name)
        print(f"ROW {name} VG=[{got['VG']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: the VG-8020 gave no reading on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: READ of a numeric DATA item "
          f"({len(only) - len(bad)}/{len(only)}; known: {', '.join(sorted(set(KNOWN) & set(only))) or '-'})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
