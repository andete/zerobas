# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RESNEXTOVF (gate: resnext-acceptance): RESUME NEXT continues with the
statement after the one that failed, whatever constants that statement holds.
Found 2026-10-09 by the numbers concept page: after a trapped Overflow in
`PRINT 1E62*9:PRINT "A"` the VG-8020 printed A and zerobas skipped it. The
statement scan RESUME NEXT uses (sub/errtrap.asm scan_stmt_end) read a numeric
constant's value bytes as text, so a $00 in them ended the "line" early.

Each row: 10 ON ERROR GOTO 100 / 20 <stmt>:PRINT "A" / 30 PRINT "B":END /
100 PRINT "E";ERR:RESUME NEXT.
  mulovf  PRINT 1E62*9       asgovf  X=1E62*9         strovf  PRINT CINT(40000)
  colpay  PRINT 58*9.87654E62    (58 is $0F $3A: a value byte that reads as
                                  ':' -- the float after it has no $00 byte)
  hexpay  PRINT &H100*9.87654E62  ($0C 00 01)
  dblovf  X#=1D62*1D62       ($1F + 8 value bytes)
  divzero PRINT 1/0          error6  ERROR 6          sqrneg  PRINT SQR(-1)
  undef   GOTO 999           (controls: no constant with a zero byte)

Prints `ROW <name> VG=[...] ZB=[...] <SAME|DIVERGES>`; exit 0 all agree, 1 a
divergence, 2 the VG-8020 gave no reading.
Clean-room: typed BASIC in, the text screen out. VG-8020 vs zerobas NODISK.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

CASES = {
    "mulovf": "PRINT 1E62*9",
    "asgovf": "X=1E62*9",
    "strovf": "PRINT CINT(40000)",
    "colpay": "PRINT 58*9.87654E62",
    "hexpay": "PRINT &H100*9.87654E62",
    "dblovf": "X#=1D62*1D62",
    "divzero": "PRINT 1/0",
    "error6": "ERROR 6",
    "sqrneg": "PRINT SQR(-1)",
    "undef": "GOTO 999",
}


def rows(scr):
    if scr is None:
        return None
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    if "RUN" in r:
        r = r[r.index("RUN") + 1:]
    return " | ".join(x for x in r if x and x.strip() not in ("Ok", "ZB"))


def main():
    only = sys.argv[1:] or list(CASES)
    bad, blind = [], []
    for name in only:
        lines = ["NEW", "10 ON ERROR GOTO 100", f'20 {CASES[name]}:PRINT "A"',
                 '30 PRINT "B":END', '100 PRINT "E";ERR:RESUME NEXT', "RUN"]
        got = {}
        for side, m in (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK")):
            got[side] = rows(omsx_repl.run_cases(m, [("direct", lines)], batch=False,
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
    print(f"\n{'PASS' if not bad else 'FAIL'}: RESUME NEXT after a fault "
          f"({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
