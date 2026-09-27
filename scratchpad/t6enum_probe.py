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
    print(f"{'keyword':7} {'case':30} " + " ".join(f"{m[:12]:>14}" for m in machines))
    for i, (kw, form, a, st) in enumerate(cs):
        vals = [reading(res[m][i]) for m in machines]
        print(f"{kw:7} {st:30} " + " ".join(f"{str(v):>14}" for v in vals))
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
