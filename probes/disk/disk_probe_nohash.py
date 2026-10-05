#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-INPUTDNOHASH (gate: nohash-acceptance): which file-number forms take an
OPTIONAL `#`, and does a number the tokeniser left as ASCII still evaluate?

Each case runs on a fresh test720 copy, on the CF-3300 and on ours, and prints
one fenced reading `R<...>#` (quoted text is the echoed SOURCE, never output --
the echo fence), plus ERR/ERL when the line raised.

  inputd     A$=INPUT$(5,1)            -- the filed divergence
  inputd_sp  A$=INPUT$(5, #1)          -- spaces after the comma, with `#`
  inputd_nsp A$=INPUT$(5, 1)           -- spaces after the comma, without
  close      CLOSE 1                   -- then a re-OPEN on 1 must work
  getput     OPEN"R.DAT"AS 2 LEN=8 : FIELD 2,8 AS F$ : LSET F$="ABCDEFGH" :
             PUT 2,1 : LSET F$="" : GET 2,1      -- all four without `#`
  openas     OPEN"HI.TXT"FOR INPUT AS 1          -- AS without `#`

Fixed 2026-10-05: INPUT$'s `#` was REQUIRED and had to follow the comma directly
(inputd*: Type mismatch / Syntax error); and `AS 1` without `#` stores the 1 as
an ASCII digit, which the evaluator refused (openas*: Syntax error) -- D-ASCIINUM,
basic/expr.asm ev_f_nonlet. CLOSE/FIELD/GET/PUT already agreed.

Exit 0 all agree; 1 a divergence; 2 the CF-3300 gave no reading for a case.

    python3 -u probes/disk/disk_probe_nohash.py
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402

TRAP = "ON ERROR GOTO 900"
CASES = {
    "inputd": ['OPEN"HI.TXT"FOR INPUT AS#1', "A$=INPUT$(5,1)", "CLOSE#1", 'PRINT"R";A$;"#"'],
    "inputd_sp": ['OPEN"HI.TXT"FOR INPUT AS#1', "A$=INPUT$(5, #1)", "CLOSE#1", 'PRINT"R";A$;"#"'],
    "inputd_nsp": ['OPEN"HI.TXT"FOR INPUT AS#1', "A$=INPUT$(5, 1)", "CLOSE#1", 'PRINT"R";A$;"#"'],
    "inputd_2": ["MAXFILES=2", 'OPEN"HI.TXT"FOR INPUT AS#2', "A$=INPUT$(3,2)", "CLOSE#2",
                 'PRINT"R";A$;"#"'],
    "close": ['OPEN"HI.TXT"FOR INPUT AS#1', "CLOSE 1", 'OPEN"HI.TXT"FOR INPUT AS#1',
              "A$=INPUT$(2,#1)", "CLOSE#1", 'PRINT"R";A$;"#"'],
    # GET/PUT/FIELD without `#`, on channel 1 (MAXFILES defaults to 1); the
    # OPEN keeps its `#` so this case isolates the three statements
    "getput": ['OPEN"R.DAT"AS#1 LEN=8', "FIELD 1,8 AS F$", 'LSET F$="ABCDEFGH"', "PUT 1,1",
               'LSET F$=""', "GET 1,1", 'PRINT"R";F$;"#"', "CLOSE#1"],
    "getput_h": ['OPEN"R.DAT"AS#1 LEN=8', "FIELD#1,8 AS F$", 'LSET F$="ABCDEFGH"', "PUT#1,1",
                 'LSET F$=""', "GET#1,1", 'PRINT"R";F$;"#"', "CLOSE#1"],
    # OPEN ... AS without `#`: the tokeniser leaves `1` as an ASCII digit after
    # the letter run `AS` + space, on the VG-8020 too (scratchpad/asnum_crunch.py)
    "openas": ['OPEN"HI.TXT"FOR INPUT AS 1', "A$=INPUT$(2,#1)", "CLOSE#1", 'PRINT"R";A$;"#"'],
    "openas_ex": ["MAXFILES=2", 'OPEN"HI.TXT"FOR INPUT AS 1+1', "A$=INPUT$(2,#2)", "CLOSE#2",
                  'PRINT"R";A$;"#"'],
    "openas_12": ['OPEN"HI.TXT"FOR INPUT AS 12', 'PRINT"R";"OPENED";"#"'],
    "openas_len": ['OPEN"R.DAT"AS 1 LEN=8', "FIELD#1,8 AS F$", 'LSET F$="QRSTUVWX"', "PUT#1,1",
                   'LSET F$=""', "GET#1,1", 'PRINT"R";F$;"#"', "CLOSE#1"],
}


def prog(body):
    """A numbered program: the case body as lines 10.., an error trap that
    prints the code and line in the same fence, then RUN."""
    lines = ["NEW", f"5 {TRAP}"]
    lines += [f"{10 + 10 * i} {s}" for i, s in enumerate(body)]
    lines += ["890 END", '900 PRINT"R<ERR";ERR;"@";ERL;">#":END', "RUN"]
    return lines


def main():
    out = {}
    for tag, machine in (("CF-3300", "National_CF-3300"),
                         ("OURS", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))):
        for name, body in CASES.items():
            dsk = probe_tmp.tmp(f"nohash_{name}_{tag}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            raw = omsx_repl.run_cases(machine, [("direct", prog(body))], batch=False,
                                      reset=("", "SCREEN 0"), boot=14.0, step=3.0,
                                      diska=dsk)[0] or ""
            scr = re.sub(r"\s+", " ", raw)
            m = re.findall(r"\bR([^#]*)#", re.sub(r'"[^"\n]*"', "", scr))
            out[(tag, name)] = m[-1].strip() if m else None
            print(f"== {tag:8} {name:10} {out[(tag, name)]!r}")
    print()
    bad = 0
    for name in CASES:
        a, b = out[("CF-3300", name)], out[("OURS", name)]
        if a is None:
            print(f"INSTRUMENT FAULT: the CF-3300 gave no reading for {name} -- no reference")
            return 2
        bad += a != b
        print(f"{'AGREE   ' if a == b else 'DIVERGES'} {name:10} CF-3300 {a!r}  ours {b!r}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: {len(CASES) - bad}/{len(CASES)} file-number forms agree with the CF-3300")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
