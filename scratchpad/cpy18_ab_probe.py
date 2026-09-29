"""D-CPY18's A/B oracle: the carve is a pure refactor of the sub-ROM math's copy
calls, so every result must be BIT-IDENTICAL to the pre-carve ROM -- a stronger
test than math-acceptance's differential against the VG-8020, which carries
expected divergences.

Prints every function the six tenants serve (SQR ATN SIN COS TAN EXP LOG ^ and
RND's sequence) at double precision over ordinary, edge and error arguments.
Run it on the carved build and on HEAD's build and diff the two files.

    python3 -u scratchpad/cpy18_ab_probe.py > <file>
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

ZB = "C-BIOS_MSX1_EU_REPACK_NODISK"
ARGS = ["0#", "1#", "2#", ".5#", "1D-10", "123.456789#", "-3.7#", "1D60", "9.87654321D-40"]
FNS = ["SQR(ABS({}))", "ATN({})", "SIN({})", "COS({})", "TAN({})",
       "EXP({}/100)", "LOG(ABS({})+1D-60)", "ABS({})^1.5#", "2#^{}"]
EXTRA = ["SQR(2)", "ATN(1)*4", "SIN(1)", "EXP(1)", "LOG(10)", "1.5^2.5", "(-8)^(1/3)",
         "10^-5", "RND(-3)", "RND(1)", "RND(1)", "SQR(-1)", "LOG(0)", "EXP(200)"]


def cases():
    out = []
    for f in FNS:
        for a in ARGS:
            out.append(f.format(a))
    return out + EXTRA


def main():
    exprs = cases()
    progs = []
    for i in range(0, len(exprs), 6):
        chunk = exprs[i:i + 6]
        lines = ["NEW", "10 ON ERROR GOTO 90"]
        for j, e in enumerate(chunk):
            lines.append(f"{20 + j * 10} E=0:A#={e}:PRINT CHR$(91);{i + j};A#;E;CHR$(93)")
        lines += ["80 END", "90 E=ERR:A#=0:RESUME NEXT", "RUN"]
        progs.append(("direct", lines))
    raws = omsx_repl.run_cases(ZB, progs, batch=False, reset=("CLS",), boot=8.0,
                               step=3.0, run_gap=60.0, capture="screen")
    got = {}
    for raw in raws:
        for m in re.findall(r"\[\s*(\d+)\s+([^\]]*?)\s*\]", raw or ""):
            got[int(m[0])] = m[1]
    for i, e in enumerate(exprs):
        print(f"{i:3} {e:24} {got.get(i, 'NO READING')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
