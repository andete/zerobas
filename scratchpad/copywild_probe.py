"""D-COPYWILD: what does a WILDCARD COPY do on the reference?

🔴 FENCE FIXED 2026-09-28 (round 5): every `[` is printed as CHR$(91). Before, a
case that printed NOTHING read the TYPED ECHO of its own `PRINT"[|OK]"` -- the
reading regex excludes a bracket holding a quote, and `[|OK]` holds none. That is
how `x_cwild` read "OK" where copy-acceptance's fenced survey reads ERR 5 on the
CF-3300 (scratchpad/copy_survey.out) -- [[trapsvc-echo-fence]]. Rounds 1-4 are
suspect wherever they read a bare `[|OK]` or `[X1|OK]`-shaped value.

scratchpad/copynameopen_run.out's `c_wild` read 5 (Illegal function call) for
`COPY "A*.TXT" TO "C*.TXT"` on zerobas. Before porting anything, ask the CF-3300
what a wildcard COPY copies and what it names each copy -- one boot per case, a
private writable image each, trapped by ON ERROR. The copies are read back by
name, so a reading says both WHAT was made and what it is CALLED:

  w_star    A1 ("X1"), A2 ("X2"); COPY "A*.TXT" TO "C*.TXT"; read C1, C2
  w_quest   the same with "A?.TXT" TO "D?.TXT"; read D1, D2
  w_ext     COPY "A1.*" TO "E1.*"; read E1.TXT
  w_plain   COPY "A*.TXT" TO "F.TXT"; read F.TXT (both into one name?)
  w_none    COPY "Z*.TXT" TO "C*.TXT" with no Z file           -> 53?
  w_keep    COPY "A*.TXT" TO "G*.TXT"; is A1 still there? (a COPY, not a move)

    python3 -u scratchpad/copywild_probe.py [case ...]
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl, t6enum_probe as t

TAIL = ['90 PRINT CHR$(91);"";A$;"|";B$;ERR;ERL;"]":END', "RUN"]
MK = ('20 OPEN "A1.TXT" FOR OUTPUT AS #1:PRINT #1,"X1":CLOSE:'
      'OPEN "A2.TXT" FOR OUTPUT AS #1:PRINT #1,"X2":CLOSE')


def rd(var, name):
    return f'OPEN "{name}" FOR INPUT AS #1:INPUT #1,{var}:CLOSE'


def prog(*body):
    return ["NEW", "10 ON ERROR GOTO 90", MK] + list(body) + TAIL


CASES = {
    "w_star": prog('30 COPY "A*.TXT" TO "C*.TXT"',
                   '40 ' + rd("A$", "C1.TXT") + ':' + rd("B$", "C2.TXT") + ':PRINT CHR$(91);"";A$;"|";B$;"OK]":END'),
    "w_quest": prog('30 COPY "A?.TXT" TO "D?.TXT"',
                    '40 ' + rd("A$", "D1.TXT") + ':' + rd("B$", "D2.TXT") + ':PRINT CHR$(91);"";A$;"|";B$;"OK]":END'),
    "w_ext": prog('30 COPY "A1.*" TO "E1.*"', '40 ' + rd("A$", "E1.TXT") + ':PRINT CHR$(91);"";A$;"|OK]":END'),
    "w_plain": prog('30 COPY "A*.TXT" TO "F.TXT"', '40 ' + rd("A$", "F.TXT") + ':PRINT CHR$(91);"";A$;"|OK]":END'),
    "w_none": prog('30 COPY "Z*.TXT" TO "C*.TXT":PRINT CHR$(91);"|OK]":END'),
    "w_keep": prog('30 COPY "A*.TXT" TO "G*.TXT"', '40 ' + rd("A$", "A1.TXT") + ':PRINT CHR$(91);"";A$;"|OK]":END'),
    # --- round 4: D-COPY's `c.wild` (docs/spec-basic-copy.md) measured
    # `COPY"*.BAS"TO"Z.BAS"` = ERR 5 over the FIXTURE's three .BAS files, while
    # w_plain (two FRESHLY WRITTEN A*.TXT to a plain F.TXT) never completed. Which
    # separates them -- fresh files, or the destination's shape? No line-20 writes.
    "x_cwild": ["NEW", "10 ON ERROR GOTO 90", '30 COPY "*.BAS" TO "Z.BAS":PRINT CHR$(91);"|OK]":END'] + TAIL,
    "x_multi": ["NEW", "10 ON ERROR GOTO 90", '30 COPY "PROG*.BAS" TO "Q*.BAS"',
                '40 OPEN "Q.BAS" FOR INPUT AS #1:B$=STR$(LOF(1)):CLOSE:PRINT CHR$(91);"|";B$;"OK]":END'] + TAIL,
}


def main():
    only = sys.argv[1:] or list(CASES)
    got = {}
    for m, cf in (("National_CF-3300", True), ("C-BIOS_MSX1_EU_REPACK_DISK", False)):
        for k in only:
            raw = omsx_repl.run_cases(m, [("direct", CASES[k])], batch=False,
                                      reset=("", "SCREEN 0", "CLS") if cf else ("CLS",),
                                      boot=14.0 if cf else 8.0, capture="screen",
                                      diska=t._disk_image(), step=8.0,
                                      cap_gap=float(os.environ.get("COPYWILD_GAP", "20")))[0] or ""
            r = re.findall(r"\[[^\]\"]*\]", raw)
            got[(m, k)] = " ".join(r[-1].split()) if r else "NO READING"
    print(f"{'case':8} {'CF-3300':>20} {'zerobas':>20}")
    for k in only:
        a, b = got[("National_CF-3300", k)], got[("C-BIOS_MSX1_EU_REPACK_DISK", k)]
        print(f"{'  ' if a == b else '✗ '}{k:8} {a:>20} {b:>20}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
