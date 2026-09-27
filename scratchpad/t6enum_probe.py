"""D-KWT6 S2 — ENUMERATE the reference's error set per keyword form (T6's denominator).

Joost's T6 ruling (2026-09-27): a keyword proves T6 when, for each documented
form, it has one row per DISTINCT error the reference raises for that form. This
probe measures that set on the VG-8020 by applying a FIXED FAULT BATTERY to each
form's argument and trapping what comes back:

    10 ON ERROR GOTO 90
    20 <the case>
    30 PRINT"[OK]":END
    90 PRINT"[";ERR;ERL;"]":END

`ERR`/`ERL` are the reference's own BASIC variables -- the code AND the line,
read directly, no message table to go stale. A case that raises nothing prints
`[OK]` and adds nothing to the set.

THE BATTERY IS THE BOUND, and it is stated here rather than implied: per argument
of a numeric function -- wrong type (a string), missing, one extra argument, and
the range edges below; per string argument -- wrong type (a number), missing,
extra, empty. A code no case elicits is not in the set; widening the battery is
how the set grows, and the output says which case produced each code so the T6
rows can be written from it.

Clean room: typed BASIC and the screen. Fresh boot per case (one error must not
leave state for the next).  `--zb` runs the same cases on zerobas for comparison.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"

NUM = ['"A"', "", "1,2"]            # type, missing, extra -- every numeric arg
STR = ["5", "", '"A","B"', '""']    # type, missing, extra, empty -- every string arg

# keyword -> (form, printable expression template with {a}, extra argument cases)
BATCH = {
    "ABS":  ("magnitude",    "ABS({a})",  NUM + ["-1E38"]),
    "SGN":  ("sign",         "SGN({a})",  NUM + ["-1E38"]),
    "INT":  ("floor",        "INT({a})",  NUM + ["-1E38"]),
    "SQR":  ("square-root",  "SQR({a})",  NUM + ["-1", "0"]),
    "LOG":  ("logarithm",    "LOG({a})",  NUM + ["0", "-1"]),
    # 🔴 EXP(99) was the first cut and read OK on both: e^99 is ~1E43, inside
    # MSX's ~1E63 range -- my arithmetic, not the machine. 150 is past it.
    "EXP":  ("exponential",  "EXP({a})",  NUM + ["99", "-99", "150"]),
    "ASC":  ("code-of",      "ASC({a})",  STR),
    "CHR$": ("code-to-char", "CHR$({a})", NUM + ["256", "-1", "70000"]),
    "LEN":  ("length",       "LEN({a})",  STR),
    "PEEK": ("address-read", "PEEK({a})", NUM + ["65536", "-32769", "70000"]),
}


# --- BATCH 2 (2026-09-27): MULTI-ARGUMENT functions and STATEMENTS -------------
# Each ARGUMENT gets its own faults: wrong type (N gets "A", S gets 5) and the
# range edges listed for it; then the call MISSING its last argument, with NO
# arguments, and with one EXTRA argument. A statement (stmt=True) is typed bare.
# keyword -> (form, stmt?, [(kind, valid, [edges])])
N, S = "N", "S"
BATCH2 = {
    "LEFT$":   ("prefix",          False, [(S, '"AB"', []), (N, "1", ["-1", "256", "70000"])]),
    "RIGHT$":  ("suffix",          False, [(S, '"AB"', []), (N, "1", ["-1", "256", "70000"])]),
    "STRING$": ("repeat",          False, [(N, "2", ["-1", "256"]),
                                           ("X", '"A"', ['""', "256", "-1"])]),
    "HEX$":    ("to-hex",          False, [(N, "1", ["70000", "-70000"])]),
    "OCT$":    ("to-octal",        False, [(N, "1", ["70000", "-70000"])]),
    "BIN$":    ("to-binary",       False, [(N, "1", ["70000", "-70000"])]),
    "SPACE$":  ("pad",             False, [(N, "1", ["-1", "256"])]),
    "MKI$":    ("int-to-string",   False, [(N, "1", ["32768", "-32769"])]),
    "CVI":     ("string-to-int",   False, [(S, '"AB"', ['""', '"A"'])]),
    "STR$":    ("number-to-string", False, [(N, "1", [])]),
    "CINT":    ("to-integer",      False, [(N, "1", ["32768", "-32769"])]),
    "FIX":     ("truncate",        False, [(N, "1", ["-1E38"])]),
    "CSNG":    ("to-single",       False, [(N, "1", ["1E38"])]),
    "CDBL":    ("to-double",       False, [(N, "1", ["1E38"])]),
    "SIN":     ("sine",            False, [(N, "1", ["1E38"])]),
    "COS":     ("cosine",          False, [(N, "1", ["1E38"])]),
    "TAN":     ("tangent",         False, [(N, "1", ["1E38"])]),
    "ATN":     ("arctangent",      False, [(N, "1", ["1E38"])]),
    "VPEEK":   ("address-read",    False, [(N, "1", ["16384", "-1", "70000"])]),
    # &H9000, not a work-area address: the `extra` case pokes BEFORE its Syntax
    # error, and $E800 is zerobas's private workspace. $9000 is free program/
    # variable space on both machines at this program size.
    "POKE":    ("address-value",   True,  [(N, "&H9000", ["65536", "-32769"]),
                                           (N, "1", ["256", "-1"])]),
    "VPOKE":   ("address-value",   True,  [(N, "1", ["16384", "-1", "70000"]),
                                           (N, "1", ["256", "-1"])]),
    "SOUND":   ("register-value",  True,  [(N, "8", ["14", "-1", "256"]),
                                           (N, "0", ["256", "-1"])]),
}


# --- BATCH 3 (2026-09-27): DISK BASIC functions -- `--disk` runs the CF-3300
# against zerobas's DISK build, the pairing kwsweep's NEEDS-DISK: rows use. Batch
# 2 showed the diskless VG-8020 is the wrong oracle here (MKI$("A") read 5).
BATCH3 = {
    "MKI$": ("int-to-string",    False, [(N, "1", ["32768", "-32769"])]),
    "CVI":  ("string-to-int",    False, [(S, '"AB"', ['""', '"A"'])]),
    "MKS$": ("single-to-string", False, [(N, "1", [])]),
    "CVS":  ("string-to-single", False, [(S, '"ABCD"', ['""', '"ABC"'])]),
    "MKD$": ("double-to-string", False, [(N, "1", [])]),
    "CVD":  ("string-to-double", False, [(S, '"ABCDEFGH"', ['""', '"ABCDEFG"'])]),
    "DSKF": ("free-space",       False, [(N, "0", ["9", "-1", "256"])]),
}


# --- BATCH 4 (2026-09-27): STATEMENTS and MULTI-FORM keywords ------------------
# Their errors are SCENARIOS (NEXT without FOR, RETURN without GOSUB, Out of DATA),
# not argument faults, so each (keyword, form) lists hand-written ONE-LINE cases:
# set-up goes on the same line with colons so ERL stays the line under test.
# RETURN's line form needs a live GOSUB to reach its own error (8), and gets one
# by recursing into its own line: `IF X=0 THEN X=1:GOSUB 20 ELSE RETURN 99`.
# VAL and FRE are NOT here: their "forms" are argument CONTENT/type, which no
# syntax fault can tell apart.
BATCH4 = {
    "INSTR": [
        ("search", ['PRINT INSTR("AB",5)', 'PRINT INSTR("AB")', "PRINT INSTR()",
                    'PRINT INSTR("AB","B","C")']),
        ("search-from", ['PRINT INSTR(0,"AB","B")', 'PRINT INSTR(256,"AB","B")',
                         'PRINT INSTR(70000,"AB","B")', 'PRINT INSTR(1,5,"B")',
                         'PRINT INSTR(1,"AB",5)', 'PRINT INSTR(1,"AB","B","C")',
                         'PRINT INSTR(1,"AB")'])],
    "MID$": [
        ("substring-3arg", ["PRINT MID$(5,1,1)", 'PRINT MID$("AB",0,1)',
                            'PRINT MID$("AB",256,1)', 'PRINT MID$("AB",1,-1)',
                            'PRINT MID$("AB",1,256)', 'PRINT MID$("AB","A",1)',
                            'PRINT MID$("AB",1,"A")', 'PRINT MID$("AB",1,1,1)',
                            'PRINT MID$("AB",70000,1)']),
        ("substring-to-end", ["PRINT MID$(5,1)", 'PRINT MID$("AB",0)',
                              'PRINT MID$("AB")', 'PRINT MID$("AB","A")', "PRINT MID$()"]),
        ("assign", ['A$="AB":MID$(A$,0)="X"', 'A$="AB":MID$(A$,1)=5',
                    'A$="AB":MID$(A$,3)="X"', 'A$="AB":MID$(A$,1,-1)="X"',
                    'A$="AB":MID$(A$,1,1)', 'MID$(5,1)="X"', 'A$="AB":MID$(A$)="X"',
                    'A$="AB":MID$(A$,256)="X"'])],
    "NEXT": [
        ("bare", ["NEXT", "FOR I=1 TO 2:NEXT:NEXT"]),
        ("named", ["NEXT I", "FOR I=1 TO 2:NEXT J", "FOR I=1 TO 2:NEXT A$",
                   "FOR I=1 TO 2:NEXT 5"]),
        ("comma-list", ["FOR I=1 TO 2:FOR J=1 TO 2:NEXT J,K", "NEXT I,J",
                        "FOR I=1 TO 2:FOR J=1 TO 2:NEXT J,"])],
    "RETURN": [
        ("bare", ["RETURN"]),
        ("line", ["RETURN 99", "IF X=0 THEN X=1:GOSUB 20 ELSE RETURN 99",
                  'IF X=0 THEN X=1:GOSUB 20 ELSE RETURN "A"'])],
    "RESTORE": [
        ("bare", ["RESTORE,", "RESTORE 1,2"]),
        ("line", ["RESTORE 99", 'RESTORE "A"', "RESTORE -1", "RESTORE 70000"])],
    "GOTO": [("jump", ["GOTO 99", "GOTO", 'GOTO "A"', "GOTO -1", "GOTO 70000"])],
    "READ": [("read-data", ["READ A", "READ A:DATA X", "READ 5", "READ",
                            "READ A:DATA 1E99"])],
    "SWAP": [("exchange", ["SWAP A,B$", "SWAP A", "SWAP", "SWAP A,5"])],
    "ERASE": [("free-array", ["ERASE A", "ERASE", "ERASE 5", "DIM A(2):ERASE A,A"])],
    "DIM": [
        ("one-dimensional", ["DIM A(2):DIM A(2)", "DIM A(-1)", 'DIM A("X")',
                             "DIM A(70000)", "DIM A(10000)", "DIM 5"]),
        ("multi-dimensional", ["DIM B(2,2):DIM B(2,2)", "DIM B(-1,2)", 'DIM B(2,"X")',
                               "DIM B(200,200)"])],
}


# --- BATCH 5 (2026-09-27): one-form OPERATORS, bare statements and readers ------
# OUT's `extra` case writes its port BEFORE the Syntax error, so it uses &H2F, an
# unused port. ERROR's valid form raises its own argument, so only MALFORMED
# forms are faulted. REM is absent: a comment has no errors, and a zero
# denominator proves nothing.
def _op(kw):
    return [f'PRINT 1 {kw} "A"', f"PRINT 1 {kw}", f"PRINT 70000 {kw} 1",
            f"PRINT 1 {kw} 70000"]


BATCH5 = {
    "AND": [("bitwise-and", _op("AND"))],
    "OR": [("bitwise-or", _op("OR"))],
    "XOR": [("bitwise-xor", _op("XOR"))],
    "EQV": [("equivalence", _op("EQV"))],
    "IMP": [("implication", _op("IMP"))],
    "NOT": [("bitwise-not", ['PRINT NOT "A"', "PRINT NOT", "PRINT NOT 70000"])],
    "MOD": [("modulo", ["PRINT 5 MOD 0", 'PRINT 5 MOD "A"', "PRINT 5 MOD",
                        "PRINT 70000 MOD 2"])],
    "BEEP": [("no-argument", ["BEEP 1", "BEEP,"])],
    "CLS": [("no-argument", ["CLS 1", "CLS,"])],
    "TRON": [("toggle", ["TRON 1", "TRON,"])],
    "TROFF": [("toggle", ["TROFF 1", "TROFF,"])],
    "END": [("terminate", ["END 1", "END,"])],
    "CSRLIN": [("row-read", ["PRINT CSRLIN(1)", "A=CSRLIN 1"])],
    "ERL": [("error-line", ["PRINT ERL(1)", "A=ERL 1"])],
    "ERR": [("error-code", ["PRINT ERR(1)", "A=ERR 1"])],
    "ERROR": [("raise", ["ERROR 0", "ERROR 256", 'ERROR "A"', "ERROR", "ERROR -1",
                         "ERROR 70000", "ERROR 1,1"])],
    "GOSUB": [("call", ["GOSUB 99", "GOSUB", 'GOSUB "A"', "GOSUB -1", "GOSUB 70000"])],
    "INKEY$": [("poll-key", ["PRINT INKEY$(1)", "A=INKEY$"])],
    "INP": [("port-read", ['PRINT INP("A")', "PRINT INP()", "PRINT INP(256)",
                           "PRINT INP(-1)", "PRINT INP(1,2)"])],
    "LET": [("assign", ['LET A="X"', "LET A$=5", "LET 5=1", "LET", "LET A"])],
    "OUT": [("port-value", ['OUT "A",1', 'OUT &H2F,"A"', "OUT 256,1", "OUT &H2F,256",
                            "OUT &H2F", "OUT", "OUT &H2F,1,1"])],
    "POINT": [("pixel-read", ['PRINT POINT("A",1)', "PRINT POINT(1)", "PRINT POINT()",
                              "PRINT POINT(1,1,1)"])],
    "POS": [("column-read", ['PRINT POS("A")', "PRINT POS()", "PRINT POS(1,2)"])],
    "LPOS": [("column-read", ['PRINT LPOS("A")', "PRINT LPOS()", "PRINT LPOS(1,2)"])],
    "RND": [("reseeded-draw", ['PRINT RND("A")', "PRINT RND()", "PRINT RND(1,2)"])],
}


def _call(kw, stmt, args):
    a = ",".join(args)
    return f"{kw} {a}".rstrip() if stmt else f"PRINT {kw}({a})"


def batch2_cases(kw, form, stmt, spec):
    valid = [v for _k, v, _e in spec]
    for i, (kind, _v, edges) in enumerate(spec):
        bad = ['"A"'] if kind == N else (["5"] if kind == S else [])
        for x in bad + edges:
            yield kw, form, x, _call(kw, stmt, valid[:i] + [x] + valid[i + 1:])
    if len(valid) > 1:
        yield kw, form, "missing-last", _call(kw, stmt, valid[:-1])
    yield kw, form, "no-args", _call(kw, stmt, [])
    yield kw, form, "extra", _call(kw, stmt, valid + [valid[-1]])


def cases():
    only = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--only=")), None)
    if "--batch=4" in sys.argv or "--batch=5" in sys.argv:
        for kw, formlist in (BATCH5 if "--batch=5" in sys.argv else BATCH4).items():
            if only and kw not in only.split(","):
                continue
            for form, stmts in formlist:
                for st in stmts:
                    yield kw, form, st, st
        return
    if "--batch=2" in sys.argv or "--batch=3" in sys.argv:
        b = BATCH3 if "--batch=3" in sys.argv else BATCH2
        for kw, (form, stmt, spec) in b.items():
            if only and kw not in only.split(","):
                continue
            yield from batch2_cases(kw, form, stmt, spec)
        return
    for kw, (form, tpl, args) in BATCH.items():
        if only and kw not in only.split(","):
            continue
        for a in args:
            yield kw, form, a, f"PRINT {tpl.format(a=a)}"


def program(stmt):
    return ["NEW", "10 ON ERROR GOTO 90", f"20 {stmt}", '30 PRINT"[OK]":END',
            '90 PRINT"[";ERR;ERL;"]":END', "RUN"]


def reading(raw):
    rows = [(raw or "")[i * omsx_repl.COLS:(i + 1) * omsx_repl.COLS]
            for i in range(omsx_repl.ROWS)]
    runi = [i for i, r in enumerate(rows) if r.strip() == "RUN"]
    out = "".join(rows[runi[-1] + 1:]) if runi else ""
    m = re.findall(r"\[\s*(\d+)\s+(\d+)\s*\]|\[OK\]", out)
    if not m:
        return None
    last = m[-1]
    return "OK" if last == ("", "") else (int(last[0]), int(last[1]))


def _disk_image():
    import shutil, tempfile
    fh = tempfile.NamedTemporaryFile(suffix=".dsk", delete=False)
    fh.close()
    shutil.copy(os.path.join(REPO, "disk", "test720.dsk"), fh.name)
    return fh.name


def main():
    disk = "--batch=3" in sys.argv
    ref, zb = (("National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK") if disk else (REF, ZB))
    machines = [ref] + ([zb] if "--zb" in sys.argv else [])
    cs = list(cases())
    res = {}
    for m in machines:
        kw = {}
        if disk:
            # a PRIVATE writable copy per machine; the CF-3300 boots SCREEN 1 and
            # needs kwsweep's MACH_RESET_PRE / MACH_BOOT (an Enter, SCREEN 0; 14 s)
            kw = dict(diska=_disk_image(), step=8.0, cap_gap=20.0)
        cf = m.startswith("National")
        res[m] = omsx_repl.run_cases(m, [("direct", program(st)) for *_, st in cs],
                                     batch=False,
                                     reset=("", "SCREEN 0", "CLS") if cf else ("CLS",),
                                     boot=14.0 if cf else 8.0, capture="screen", **kw)
    sets = {}
    print(f"{'keyword':7} {'case':44} " + " ".join(f"{m[:12]:>14}" for m in machines))
    for i, (kw, form, a, st) in enumerate(cs):
        vals = [reading(res[m][i]) for m in machines]
        print(f"{kw:7} {st:44} " + " ".join(f"{str(v):>14}" for v in vals))
        v = vals[0]
        if isinstance(v, tuple):
            sets.setdefault(kw, {}).setdefault(form, {}).setdefault(v[0], st)
        elif v is None:
            print(f"   ⚠️ {kw} {st!r}: NO READING on the reference -- not scored")
    print("\n# the reference's error set per keyword form (code: first case)")
    for kw, forms in sets.items():
        for form, codes in forms.items():
            print(f"{kw:6} {form:14} " + "  ".join(f"{c}: {s}" for c, s in sorted(codes.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
