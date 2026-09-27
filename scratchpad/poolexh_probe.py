"""D-STACKFLOOR follow-up: after GOSUB recursion runs out of memory, how deep an
expression can the program still evaluate -- here and on the reference?

ramfree-acceptance's n.deep went RED on the D-STACKFLOOR build: it recurses
`GOSUB` until Out of memory, RESUMEs into its check with every frame still
standing, and the check's `((P+i) AND 255)` now refuses (ERR 7) and RESUMEs into
itself for ever. With the pool exhausted the stack sits within ~256 B of the
arrays, and the evaluator guard keeps STK_EVAL_RESERVE (128) of that.

This asks both machines the same question, portably: recurse to Out of memory,
RESUME with the frames standing, then evaluate parentheses nested 1, 2, 3, ...
deep; the reading is the deepest that completed (and the error that stopped it).

    python3 -u scratchpad/poolexh_probe.py
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
MAXD = 16


def prog(kind):
    P = lambda n: "(" * n + "1" + "+1)" * n
    lines = ["NEW", "10 ON ERROR GOTO 900", "15 D=0:F=0:X=0:N=0",
             "20 GOSUB 1010" if kind == "gosub" else "20 GOTO 30"]
    for d in range(1, MAXD + 1):
        lines.append(f"{29 + d} D={d}:X={P(d)}")
    lines += ['80 PRINT CHR$(91);"ALL";D;N;CHR$(93):END',
              '900 IF F=0 THEN F=1:RESUME 30',
              '910 PRINT CHR$(91);"STOP";D-1;ERR;N;CHR$(93):END',
              "1010 N=N+1:GOSUB 1010", "RUN"]
    return lines


def reading(raw):
    m = re.findall(r"\[([^\]\"]*)\]", raw or "")
    return " ".join(m[-1].split()) if m else "NO READING"


def main():
    kinds = ["control", "gosub"]
    res = {m: omsx_repl.run_cases(m, [("direct", prog(k)) for k in kinds], batch=False,
                                  reset=("CLS",), boot=8.0, step=3.0, run_gap=60.0,
                                  capture="screen")
           for m in (REF, ZB)}
    print("reads [ALL d frames] (every depth fitted) or [STOP deepest-that-fitted ERR frames]")
    for i, k in enumerate(kinds):
        print(f"  {k:8} VG-8020 {reading(res[REF][i]):24} zerobas {reading(res[ZB][i])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
