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


def cases():
    only = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--only=")), None)
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


def main():
    machines = [REF] + ([ZB] if "--zb" in sys.argv else [])
    cs = list(cases())
    res = {m: omsx_repl.run_cases(m, [("direct", program(st)) for *_, st in cs],
                                  batch=False, reset=("CLS",), boot=8.0,
                                  capture="screen")
           for m in machines}
    sets = {}
    print(f"{'keyword':6} {'case':22} " + " ".join(f"{m[:12]:>14}" for m in machines))
    for i, (kw, form, a, st) in enumerate(cs):
        vals = [reading(res[m][i]) for m in machines]
        print(f"{kw:6} {st:22} " + " ".join(f"{str(v):>14}" for v in vals))
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
