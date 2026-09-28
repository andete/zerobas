"""D-NAMEEXIST: NAME onto an existing file, and the rename that must still work.

T6 batch 8 found `NAME "N1.TXT" AS "N2.TXT"` with both files present raising 65
File already exists on the CF-3300 and SUCCEEDING on zerobas (two directory
entries of one name). The fix looks the new name up first -- with fat_find, which
records its hit in the very cells the rename then stamps, so the ordinary rename
is the regression row here, not a control. One boot per case, the CF-3300 against
zerobas's DISK build, a private disk image each:

  exists   N1 and N2 both present; NAME N1 AS N2           -> 65
  rename   M1 written with "HI"; NAME M1 AS M3; read M3    -> HI, and M1 is gone (53)
  nosuch   NAME a missing file                             -> 53

    python3 -u scratchpad/nameexist_probe.py
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl, t6enum_probe as t

CASES = {
    "exists": ["NEW", "10 ON ERROR GOTO 90",
               '20 OPEN "N1.TXT" FOR OUTPUT AS #1:CLOSE:OPEN "N2.TXT" FOR OUTPUT AS #1:CLOSE',
               '30 NAME "N1.TXT" AS "N2.TXT":PRINT"[OK]":END',
               '90 PRINT"[";ERR;ERL;"]":END', "RUN"],
    "rename": ["NEW", "10 ON ERROR GOTO 90",
               '20 OPEN "M1.TXT" FOR OUTPUT AS #1:PRINT #1,"HI":CLOSE',
               '30 NAME "M1.TXT" AS "M3.TXT"',
               '40 OPEN "M3.TXT" FOR INPUT AS #1:INPUT #1,A$:CLOSE',
               '50 OPEN "M1.TXT" FOR INPUT AS #1:PRINT"[";A$;"STILL]":END',
               '90 PRINT"[";A$;ERR;ERL;"]":END', "RUN"],
    "nosuch": ["NEW", "10 ON ERROR GOTO 90", '20 NAME "NOSUCH.TXT" AS "B.TXT":PRINT"[OK]":END',
               '90 PRINT"[";ERR;ERL;"]":END', "RUN"],
}


def main():
    got = {}
    for m, cf in (("National_CF-3300", True), ("C-BIOS_MSX1_EU_REPACK_DISK", False)):
        for k, lines in CASES.items():
            raw = omsx_repl.run_cases(m, [("direct", lines)], batch=False,
                                      reset=("", "SCREEN 0", "CLS") if cf else ("CLS",),
                                      boot=14.0 if cf else 8.0, capture="screen",
                                      diska=t._disk_image(), step=8.0, cap_gap=20.0)[0] or ""
            r = re.findall(r"\[[^\]\"]*\]", raw)
            got[(m, k)] = " ".join(r[-1].split()) if r else "NO READING"
    print(f"{'case':8} {'CF-3300':>16} {'zerobas':>16}")
    for k in CASES:
        a, b = got[("National_CF-3300", k)], got[("C-BIOS_MSX1_EU_REPACK_DISK", k)]
        print(f"{'  ' if a == b else '✗ '}{k:8} {a:>16} {b:>16}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
