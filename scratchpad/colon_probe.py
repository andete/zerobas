"""D-SAVECOLON: does a disk verb let the rest of its LINE run?

Found 2026-09-28 by scratchpad/errkeep2_probe.py round 2: `SAVE "X.BAS":PRINT
"[OK]"` and `BSAVE "X.BIN",&HC000,&HC010:PRINT"[OK]"` print `[OK]` on the CF-3300
and fail on zerobas even on a WRITABLE disk -- do_save reads the `:` after the
name as "trailing junk" and goes to load_error, and a handler that `ret`s ends the
whole line besides. The same verb on a line of its own works on both. This asks
every disk verb the same question, one boot per case, the CF-3300 against
zerobas's DISK build, a private writable image each:

  <verb>:PRINT"[OK]"      must print [OK] and reach the END after it

plus what the reference does with real junk after SAVE's name (junk5): its ERR
and ERL, and whether the file was written anyway (RESUME 40 then OPEN it).

    python3 -u scratchpad/colon_probe.py [case ...]
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl, t6enum_probe as t

TAIL = ['90 PRINT"[";ERR;ERL;"]":END', "RUN"]


def prog(*body):
    return ["NEW", "10 ON ERROR GOTO 90"] + list(body) + TAIL


OK = ':PRINT"[OK]":END'
CASES = {
    "save": prog('30 SAVE "X.BAS"' + OK),
    "save_sp": prog('30 SAVE "X.BAS" ' + OK),
    "asave": prog('30 SAVE "X.BAS",A' + OK),
    "bsave": prog('30 BSAVE "X.BIN",&HC000,&HC010' + OK),
    "bsave_x": prog('30 BSAVE "X.BIN",&HC000,&HC010,&HC000' + OK),
    "bload": prog('20 BSAVE "Y.BIN",&HC000,&HC010', '30 BLOAD "Y.BIN"' + OK),
    "copy": prog('30 COPY "HI.TXT" TO "HK.TXT"' + OK),
    "name": prog('30 NAME "HI.TXT" AS "HK.TXT"' + OK),
    "kill": prog('20 BSAVE "Y.BIN",&HC000,&HC010', '30 KILL "Y.BIN"' + OK),
    "files": prog('30 FILES "HI.TXT"' + OK),
    "open": prog('30 OPEN "Y.TXT" FOR OUTPUT AS #1' + OK),
    "close": prog('20 OPEN "Y.TXT" FOR OUTPUT AS #1', '30 CLOSE #1' + OK),
    # junk after SAVE's name: the reference's ERR/ERL, and was the file written?
    "junk5": ["NEW", "10 ON ERROR GOTO 90", '30 SAVE "J.BAS" 5',
              '40 OPEN "J.BAS" FOR INPUT AS #1:PRINT"[";E;"WRITTEN]":END',
              '90 IF ERL=30 THEN E=ERR:RESUME 40', '95 PRINT"[";E;ERR;ERL;"]":END',
              "RUN"],
}


def main():
    only = sys.argv[1:] or list(CASES)
    got = {}
    for m, cf in (("National_CF-3300", True), ("C-BIOS_MSX1_EU_REPACK_DISK", False)):
        for k in only:
            raw = omsx_repl.run_cases(m, [("direct", CASES[k])], batch=False,
                                      reset=("", "SCREEN 0", "CLS") if cf else ("CLS",),
                                      boot=14.0 if cf else 8.0, capture="screen",
                                      diska=t._disk_image(), step=8.0, cap_gap=20.0)[0] or ""
            r = re.findall(r"\[[^\]\"]*\]", raw)
            got[(m, k)] = " ".join(r[-1].split()) if r else "NO READING"
    print(f"{'case':9} {'CF-3300':>18} {'zerobas':>18}")
    for k in only:
        a, b = got[("National_CF-3300", k)], got[("C-BIOS_MSX1_EU_REPACK_DISK", k)]
        print(f"{'  ' if a == b else '✗ '}{k:9} {a:>18} {b:>18}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
