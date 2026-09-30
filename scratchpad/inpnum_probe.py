"""D-INPNUM: does a NUMERIC INPUT target take a non-integer number?

Found 2026-09-29 while testing channel switching: numeric `INPUT #1,X` is Type
mismatch here (the file form's target parser is string-only), and console
INPUT's numeric path goes through `input_num_field`, a 16-bit INTEGER validator
-- so `1.5`, `40000` or `1E3` typed at `INPUT A` would read as ?Redo here.
Read off the code; this asks the machines.

  console (VG-8020 vs zerobas NODISK): `INPUT A` answered with each value, then
          A printed. A `?Redo` shows up as the prompt coming back and the
          second response (`7`) being the one read.
  file    (CF-3300 vs zerobas DISK): the value written with PRINT #1 (so as
          PRINT formats it), read back with `INPUT #1,X`.

    python3 -u scratchpad/inpnum_probe.py [console|file]
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl, t6enum_probe as t

TYPED = ["5", "-3", "1.5", "40000", "1E3", "-2.5E-2", " 7 ", "12X", "&H10", "1D2"]
WRITTEN = ["5", "-3", "1.5", "40000", "1E3", "-2.5E-2", "1/3", "123456789", "A%", "1#/3"]


# --- round 2: the EDGE rules a fix must reproduce, before one line is written ---
TYPED2 = ["1 2", "1-2", "+", "-", ".", "", "  ", "1E", "1E+", ".5", "5.", "&H1G", "1,2", "3!"]
# file lines, each written as a PRINT #1 argument list, read with INPUT #1,X,Y
WRITTEN2 = ['1;2', '1,2', '"12X"', '"  3"', '"1 2"', '""', '"&H10"', '"3,4"',
            '"5":PRINT #1,"6"', '-1;-2']


# --- round 3 (D-CHANSWITCH, 2026-09-29): what does a numeric INPUT # item
# CONSUME after the number? A LINE INPUT that follows shows the rest, and EOF
# shows whether a trailing " \r\n" went with it.
AFTER = [  # (name, the lines written with PRINT #1 -- each a PRINT argument list)
    ("blankcr", ['1', '"XY"']),          # " 1 \r\n" then "XY": INPUT X; LINE INPUT -> ?
    ("twoitems", ['1;2']),               # " 1  2 \r\n": INPUT X; LINE INPUT -> ?
    ("comma", ['"1,2"']),                # "1,2\r\n": INPUT X; LINE INPUT -> ?
    ("blanks", ['"1   ,2"']),            # blanks then a comma
    ("strafter", ['"AB ,CD"']),          # a STRING item's trailing blank + comma
]


def after_cases():
    out = []
    for k, lines in AFTER:
        w = ":".join(f"PRINT #1,{l}" for l in lines)
        out.append((k, ["NEW", "10 ON ERROR GOTO 90",
                        f'20 OPEN "N.TXT" FOR OUTPUT AS #1:{w}:CLOSE',
                        '30 OPEN "N.TXT" FOR INPUT AS #1',
                        '35 IF LEFT$("' + k + '",3)="str" THEN INPUT #1,X$ ELSE INPUT #1,X',
                        '40 E1=EOF(1):LINE INPUT #1,R$:CLOSE',
                        '50 PRINT CHR$(91);X;X$;"|";E1;"|";R$;"|";LEN(R$);E;CHR$(93):END',
                        "90 E=ERR:RESUME 50", "RUN"]))
    out.append(("eoflast", ["NEW", "10 ON ERROR GOTO 90",
                            '20 OPEN "N.TXT" FOR OUTPUT AS #1:PRINT #1,1:CLOSE',
                            '30 OPEN "N.TXT" FOR INPUT AS #1:INPUT #1,X:E1=EOF(1):CLOSE',
                            '50 PRINT CHR$(91);X;"|";E1;"|";E;CHR$(93):END',
                            "90 E=ERR:RESUME 50", "RUN"]))
    return out


def console_cases2():
    return [(v, ["NEW", "10 INPUT A", "20 PRINT CHR$(91);A;CHR$(93)", "RUN", v, "7"])
            for v in TYPED2]


def file_cases2():
    out = []
    for v in WRITTEN2:
        out.append((v, ["NEW", "10 ON ERROR GOTO 90",
                        f'20 OPEN "N.TXT" FOR OUTPUT AS #1:PRINT #1,{v}:CLOSE',
                        '30 OPEN "N.TXT" FOR INPUT AS #1:INPUT #1,X,Y:CLOSE',
                        "40 PRINT CHR$(91);X;Y;E;CHR$(93):END",
                        "90 E=ERR:RESUME 40", "RUN"]))
    return out


def console_cases():
    out = []
    for v in TYPED:
        out.append((v, ["NEW", "10 INPUT A", "20 PRINT CHR$(91);A;CHR$(93)", "RUN", v, "7"]))
    return out


def file_cases():
    out = []
    for v in WRITTEN:
        out.append((v, ["NEW", "10 ON ERROR GOTO 90", "15 A%=4",
                        f'20 OPEN "N.TXT" FOR OUTPUT AS #1:PRINT #1,{v}:CLOSE',
                        '30 OPEN "N.TXT" FOR INPUT AS #1:INPUT #1,X:CLOSE',
                        "40 PRINT CHR$(91);X;E;CHR$(93):END",
                        "90 E=ERR:RESUME 40", "RUN"]))
    return out


def run(machines, cases, disk):
    got = {}
    for m in machines:
        cf = m == "National_CF-3300"
        for k, prog in cases:
            raw = omsx_repl.run_cases(m, [("direct", prog)], batch=False,
                                      reset=("", "SCREEN 0", "CLS") if cf else ("CLS",),
                                      boot=14.0 if cf else 8.0, capture="screen", step=4.0,
                                      **({"diska": t._disk_image()} if disk else {}))[0] or ""
            r = re.findall(r"\[[^\]\"]*\]", raw)
            got[(m, k)] = " ".join(r[-1].split()) if r else "NO READING"
    a, b = machines
    print(f"{'value':12} {a[:20]:>22} {b[:20]:>22}")
    for k, _ in cases:
        x, y = got[(a, k)], got[(b, k)]
        print(f"{'  ' if x == y else '✗ '}{k!r:12} {x:>22} {y:>22}")


def main():
    which = sys.argv[1:] or ["console", "file"]
    if "console" in which:
        print("CONSOLE: INPUT A, typed value then 7 (a ?Redo reads the 7)")
        run(("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"), console_cases(), False)
    if "file" in which:
        print("FILE: PRINT #1,<v> then INPUT #1,X")
        run(("National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"), file_cases(), True)
    if "console2" in which:
        print("CONSOLE round 2: INPUT A, typed value then 7 (a ?Redo reads the 7)")
        run(("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"), console_cases2(), False)
    if "after" in which:
        print("FILE round 3: what a numeric item consumes (X X$ | EOF after | LINE INPUT rest | LEN ERR)")
        run(("National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"), after_cases(), True)
    if "file2" in which:
        print("FILE round 2: PRINT #1,<v> then INPUT #1,X,Y (X Y ERR)")
        run(("National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"), file_cases2(), True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
