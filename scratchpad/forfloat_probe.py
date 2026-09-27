"""D-FORFLOAT: what does a FOR loop do when its values are not small integers?

Found 2026-09-27 while building D-DIMRESERVE's stack probe: `FOR A=L TO H` with
L/H near 56700 printed -8836... on zerobas and 56700... on the VG-8020. zerobas's
FOR frame keeps limit and step as int16 (basic/program.asm ex_for, "D-D: a
float-valued loop is deferred", docs/spec-basic-forvar.md §5.3), so any loop whose
init / limit / step is fractional or outside -32768..32767 is not the reference's.

Each row prints its loop values and the variable after the loop; W bounds a
runaway (a loop the reference would end but zerobas might not).

    python3 -u scratchpad/forfloat_probe.py
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
ROWS = [
    ("big",      "FOR A=56700 TO 56702"),
    ("step25",   "FOR A=0 TO 1 STEP .25"),
    ("halfinit", "FOR A=.5 TO 3"),
    ("fraclim",  "FOR A=1 TO 2.5"),
    ("negfrac",  "FOR A=1 TO 0 STEP -.5"),
    ("edge",     "FOR A=1 TO 32767 STEP 16384"),
    ("edgeint",  "FOR A%=1 TO 32767 STEP 16384"),
    ("intfrac",  "FOR A%=1 TO 3 STEP .5"),
    ("intinit",  "FOR A%=1.7 TO 3"),
    ("single",   "FOR A!=0 TO 1 STEP .1"),
    ("double",   "FOR A#=0 TO 1 STEP .1"),
    ("hugestep", "FOR A=0 TO 100000 STEP 40000"),
    ("neg",      "FOR A=-40000 TO -39999"),
    ("bodyfrac", "FOR A=1 TO 3:A=A+.5"),
    ("forint",   "FOR A=1 TO 3"),                 # control: must agree today
]


def prog(stmt):
    return ["NEW", "10 ON ERROR GOTO 90:W=0",
            # 🔴 the markers are built with CHR$ so the ECHOED SOURCE cannot match
            # them -- the first run read "RUNAWAY" and a `<...>` body off the typed
            # line on every row ([[trapsvc-echo-fence]])
            f'20 {stmt}:PRINT CHR$(123);A;A%;A!;A#;CHR$(125);:W=W+1:IF W>12 THEN PRINT"R"+"UNAWAY":END',
            '30 NEXT:PRINT CHR$(91);A;A%;A!;A#;W;CHR$(93):END',
            '90 PRINT"[ERR";ERR;ERL;"]":END', "RUN"]


def reading(raw):
    raw = raw or ""
    body = " ".join(re.findall(r"\{([^}]*)\}", raw))
    tail = re.findall(r"\[([^\]\"]*)\]", raw)
    # a runaway reads `NO END`: the in-loop "RUNAWAY" print sits at the end of a
    # screen-wrapping line and never reached the capture intact, so it is not read
    return " ".join(body.split()) + " | " + (" ".join(tail[-1].split()) if tail else "NO END")


def main():
    res = {m: omsx_repl.run_cases(m, [("direct", prog(s)) for _k, s in ROWS], batch=False,
                                  reset=("CLS",), boot=8.0, step=3.0, run_gap=20.0,
                                  capture="screen")
           for m in (REF, ZB)}
    agree = 0
    for i, (k, s) in enumerate(ROWS):
        r, z = reading(res[REF][i]), reading(res[ZB][i])
        same = r == z
        agree += same
        print(f"{'  ' if same else '✗ '}{k:9} {s}")
        print(f"     VG-8020: {r}")
        if not same:
            print(f"     zerobas: {z}")
    print(f"AGREE {agree}/{len(ROWS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
