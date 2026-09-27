"""D-RUNCLOSE: which statements CLOSE the files a program left open?

Found 2026-09-27 by D-KWT6 batch 8: kwsweep's stored disk rows (each one a RUN)
leaked channels into their neighbours on zerobas only -- 38 fake EXTRAs and four
older rows broken. Asked directly, one boot per case, on the disk-equipped
CF-3300 and zerobas's DISK build (a private disk image each):

  run-close  a program opens #1 and ends; a SECOND program writes #1 -> RUN
             closes every file on the reference: 59 File not OPEN
  end-close  a program opens #1 and ENDs; `PRINT #1` typed directly
  new-close  a program opens #1; `NEW`; `PRINT #1` typed directly

    python3 -u scratchpad/runclose_probe.py
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl, t6enum_probe as t

CASES = {
    "run-close": ["NEW", '10 OPEN "Z4.TXT" FOR OUTPUT AS #1', "RUN",
                  "NEW", "10 ON ERROR GOTO 90", '20 PRINT #1,"A"', '30 PRINT"[OK]":END',
                  '90 PRINT"[";ERR;ERL;"]":END', "RUN"],
    "end-close": ["NEW", '10 OPEN "Z2.TXT" FOR OUTPUT AS #1:END', "RUN",
                  'PRINT #1,"A":PRINT"[OK]"'],
    "new-close": ["NEW", '10 OPEN "Z3.TXT" FOR OUTPUT AS #1', "RUN", "NEW",
                  'PRINT #1,"A":PRINT"[OK]"'],
}


def main():
    print(f"{'case':10} {'CF-3300':>12} {'zerobas':>12}")
    got = {}
    for m, cf in (("National_CF-3300", True), ("C-BIOS_MSX1_EU_REPACK_DISK", False)):
        for k, lines in CASES.items():
            raw = omsx_repl.run_cases(m, [("direct", lines)], batch=False,
                                      reset=("", "SCREEN 0", "CLS") if cf else ("CLS",),
                                      boot=14.0 if cf else 8.0, capture="screen",
                                      diska=t._disk_image(), step=8.0, cap_gap=20.0)[0] or ""
            r = re.findall(r"\[[^\]\"]*\]", raw)
            got[(m, k)] = " ".join(r[-1].split()) if r else "NO READING"
    for k in CASES:
        a, b = got[("National_CF-3300", k)], got[("C-BIOS_MSX1_EU_REPACK_DISK", k)]
        print(f"{'  ' if a == b else '✗ '}{k:10} {a:>12} {b:>12}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
