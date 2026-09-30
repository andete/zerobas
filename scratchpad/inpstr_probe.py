"""D-INPSTR: how does a STRING INPUT item treat blanks and quotes -- on file
(INPUT #) and console (INPUT) -- and what does it leave for the next read?

Filed under D-CHANSWITCH: `INPUT #1,A$` of " 5 " (what PRINT #1,5 writes) is
"5 " on the CF-3300 and " 5 " here (chanloop_run3.out, `one1s`). Before a line
is changed, the whole rule: leading / trailing / embedded blanks, a quoted
item, a comma after blanks -- and (the D-CHANSWITCH lesson,
[[a-reader-is-tested-by-what-it-leaves]]) what a following LINE INPUT reads.

A$ is printed with every blank shown as `_`, so the screen reading keeps them.

    python3 -u scratchpad/inpstr_probe.py [file|console]
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl, t6enum_probe as t

Q = 'CHR$(34)'
SHOW = ('B$="":FOR I=1 TO LEN(A$):C$=MID$(A$,I,1):IF C$=" " THEN C$="_"',
        'B$=B$+C$:NEXT')
# (name, the PRINT #1 argument list that writes the file)
FILE = [("num", '5'), ("lead", '"  AB"'), ("trail", '"AB  "'), ("embed", '"A B"'),
        ("both", '"  AB  "'), ("quoted", Q + '+"  AB  "+' + Q), ("comma", '"  AB  ,CD"'),
        ("empty", '""'), ("qcomma", Q + '+"A,B"+' + Q)]
TYPED = ["  AB", "AB  ", "  AB  ", "A B", '"  AB  "', '"A,B"', "  AB  ,CD"]


def show_lines(first):
    return [f"{first} {SHOW[0]}", f"{first + 1} {SHOW[1]}"]


def file_cases():
    out = []
    for k, w in FILE:
        out.append((k, ["NEW", "10 ON ERROR GOTO 90",
                        f'20 OPEN "S.TXT" FOR OUTPUT AS #1:PRINT #1,{w}:PRINT #1,"NX":CLOSE',
                        '30 OPEN "S.TXT" FOR INPUT AS #1:INPUT #1,A$:LINE INPUT #1,R$:CLOSE']
                   + show_lines(40)
                   + ['60 PRINT CHR$(91);B$;"|";LEN(A$);"|";R$;E;CHR$(93):END',
                      "90 E=ERR:RESUME 60", "RUN"]))
    return out


def console_cases():
    out = []
    for v in TYPED:
        out.append((v, ["NEW", "10 INPUT A$"] + show_lines(40)
                    + ['60 PRINT CHR$(91);B$;"|";LEN(A$);CHR$(93):END', "RUN", v]))
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
            got[(m, k)] = r[-1] if r else "NO READING"
    a, b = machines
    print(f"{'case':10} {a[:20]:>26} {b[:20]:>26}")
    for k, _ in cases:
        x, y = got[(a, k)], got[(b, k)]
        print(f"{'  ' if x == y else '✗ '}{k!r:10} {x:>26} {y:>26}")


def main():
    which = sys.argv[1:] or ["file", "console"]
    if "file" in which:
        print("FILE: PRINT #1,<w>:PRINT #1,\"NX\" then INPUT #1,A$ and LINE INPUT #1,R$ -> [A$ with _ | LEN | R$ ERR]")
        run(("National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"), file_cases(), True)
    if "console" in which:
        print("CONSOLE: INPUT A$ typed -> [A$ with _ | LEN]")
        run(("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"), console_cases(), False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
