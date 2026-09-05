#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-UNARYPLUS — unary `+`, and the rows the FIX would move without being asked.

The filed entry measured six forms (`A=+1`, `PRINT +1`, `A=(+1)`, `B=1:A=+B`,
`IF +1 THEN A=2`, `A=1++2`) — all **ERR 2** here, all legal on both references —
and prices one missing arm at `ev_f`: `cp PLUS_TOKEN / jp z,ev_f_pos`, with
`ev_f_pos: inc ix / jp ev_f` beside `ev_f_neg`.

🔴 THAT ARM DOES NOT ONLY AFFECT THE SIX. `ev_f` is the FACTOR decoder, so a
`PLUS_TOKEN` test there fires wherever a factor may begin — including in front of
a STRING, where the entry says nothing and the references have never been read.
D-CSAVEEXPR (earlier today) is the lesson: an edit's real surface is the set of
inputs the old code treated differently, and each of those needs a row FIRST
[[a-fix-falsifies-the-justification-beside-it]].

So the `x.` rows below are not about the fix's purpose; they are about its blast
radius, and they are read BEFORE any byte changes:

    x.str      B$=+A$      unary + on a STRING
    x.strlit   B$=+"X"     ...on a string LITERAL
    x.prstr    PRINT +A$   ...in the PRINT factor position
    x.dbl      A=++1       TWO unary pluses -- the identity arm re-enters ev_f,
                           so this must not become an infinite regress
    x.mixed    A=+-1       plus then minus
    x.pow      A=+2^2      ⭐ does `+` bind like unary MINUS (which calls ev_pw,
                           giving -2^2 = -4) or looser? Identity makes both
                           readings 4, so this row cannot separate them -- it is
                           here to record that, not to settle it.

Controls: `c.neg` (unary minus, correct on all three today) and `c.plain`.
Read through `ON ERROR` + `ERR`, plus the VALUE, because "no error" and "the
right answer" are different questions and a fix could buy the first without the
second.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

SIDES = {
    "vg8020": ("Philips_VG_8020", 8.0, ("NEW",)),
    "cf3300": ("National_CF-3300", 14.0, ("", "SCREEN 0", "NEW")),
    "zb": (os.environ.get("ZEROBAS_BASIC_MACHINE",
                          "C-BIOS_MSX1_EU_REPACK_DISK"), 8.0, ("NEW",)),
}
# (label, setup, expression printed, why)
CASES = [
    ("c.plain",  'A=1',        'A',      'CONTROL: no unary operator at all'),
    ("c.neg",    'A=-1',       'A',      'CONTROL: unary MINUS, correct on all three'),
    ("f.let",    'A=+1',       'A',      'the filed form'),
    ("f.var",    'B=1:A=+B',   'A',      'unary + on a VARIABLE'),
    ("f.paren",  'A=(+1)',     'A',      'inside parentheses'),
    ("f.bin",    'A=1++2',     'A',      'binary + then unary +'),
    ("x.dbl",    'A=++1',      'A',      '\U0001f534 TWO unary pluses -- the identity arm '
                                         're-enters ev_f'),
    ("x.mixed",  'A=+-1',      'A',      'plus then minus'),
    ("x.pow",    'A=+2^2',     'A',      'binding vs `^` (identity makes both readings 4)'),
    ("x.str",    'A$="X":B$=+A$', 'B$',  '\U0001f534 unary + on a STRING -- unmeasured, and '
                                         'the fix reaches it'),
    ("x.strlit", 'B$=+"X"',    'B$',     '...on a string LITERAL'),
    ("x.prstr",  'A$="X"',     '+A$',    '...in the PRINT factor position'),
]


def run(side, setup, expr):
    machine, boot, reset = SIDES[side]
    prog = ['10 ON ERROR GOTO 90', f'20 {setup}',
            f'30 PRINT"ZQ0|";{expr};"|QZ":END',
            # \U0001f534 THE LEADING `PRINT:` IS LOAD-BEARING. `PRINT +A$` errors PART
            # WAY THROUGH line 30's PRINT, which has already emitted `ZQ0|` and
            # left the cursor mid-row -- so without a fresh line the handler's
            # text lands on the SAME row and the fence reads `ZQ0|ZQ 13 ||QZ` as
            # a SUCCESS whose value is `ZQ 13 |`. Measured: that is exactly what
            # x.prstr reported before this line existed.
            '90 PRINT:PRINT"ZQ";ERR;"||QZ":END', 'RUN']
    raw = "".join(omsx_repl.run_cases(
        machine, [("direct", list(reset) + prog)], batch=False, reset=(),
        boot=boot, step=6.0, cap_gap=10.0, timeout=300.0)[0] or "")
    # \U0001f534 TWO FENCE FAULTS, AND THE FIRST DRAFT HAD BOTH.
    # (1) `result_span_after_echo(raw, "RUN")` returns None on zerobas: its
    #     prompt `ZB` has no trailing newline, so the echo row reads `ZBRUN` and
    #     the anchor never matches. Every row came back `<NO READING>` and the
    #     probe printed "0 row(s) differ" -- a clean-looking result from an
    #     instrument that read nothing [[readout-blind-to-its-own-subject]].
    # (2) Searching the WHOLE screen instead is worse, not better: rows 7-8 are
    #     the ECHOED SOURCE, which contains the fence verbatim
    #     (`ZB30 PRINT"ZQ0|";A;"|QZ"`), so a run that printed nothing would read
    #     the TYPED LINE as a value [[trapsvc-echo-fence]].
    # So: consider only rows whose own text BEGINS with the fence. The output
    # line does; an echo never can, because the prompt and line number precede it.
    rows = [raw[r * 40:(r + 1) * 40].strip() for r in range(len(raw) // 40)]
    m = [mm for r in rows if r.startswith("ZQ")
         for mm in re.findall(r"^ZQ\s*(\d+)\s*\|(.*?)\|\s*QZ", r)]
    if not m:
        return "<NO READING>"
    err, val = m[-1]
    val = " ".join(val.split())
    return f"ok {val}" if err == "0" else f"ERR {err}"


def main():
    only = ""
    for i, a in enumerate(sys.argv):
        if a == "--only" and i + 1 < len(sys.argv):
            only = a and sys.argv[i + 1]
    cases = [c for c in CASES if not only or c[0] in only.split(",")]
    if not cases:
        sys.exit(f"--only {only} matches no row")
    w = max(len(c[0]) for c in cases)
    print(f"\n{'row':<{w}} {'vg8020':>12} {'cf3300':>12} {'zb':>12}   statement")
    diff = blind = 0
    for lab, setup, expr, why in cases:
        v = [run(s, setup, expr) for s in ("vg8020", "cf3300", "zb")]
        blind += sum(1 for c in v if c == "<NO READING>")
        tag = "refs agree" if v[0] == v[1] else "\U0001f534 REFS SPLIT"
        d = v[1] != v[2]
        diff += d
        print(f"{lab:<{w}} {v[0]:>12} {v[1]:>12} {v[2]:>12}   "
              f"{setup} / PRINT {expr}   {tag}"
              + ("  \U0001f534 zb DIFF" if d else ""))
        print(f"{'':<{w}}   {why}")
    print(f"\n{diff} row(s) where zerobas differs from the CF-3300.")
    # \U0001f534 A RUN THAT READ NOTHING IS NOT A RUN THAT AGREED. The first draft of
    # this probe reported "0 row(s) differ" with every cell `<NO READING>`,
    # because the echo anchor never matched zerobas's prompt. REFUSE instead.
    if blind:
        print(f"\U0001f534 {blind} of {3 * len(cases)} cell(s) read <NO READING> -- "
              f"that is the INSTRUMENT, not the machines. This run is refused.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
