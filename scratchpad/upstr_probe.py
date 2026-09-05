#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-UPSTR — the DECLINE paths the string unary-plus arm reaches, and nothing else.

`scratchpad/uplus_probe.py` scores what the fix is FOR (12 rows, all green). This
scores what it might BREAK, which is a different question and has its own rows.

🔴 `str_eval_one` IS A DETECTOR AS WELL AS AN EVALUATOR, AND ITS CALLERS
CARRY ON PARSING FROM HL AFTER A DECLINE. basic/graphics.asm's PAINT colour arm
does `call str_eval_one / jp c,gfx_typeerr / call gfx_eval_int16`;
basic/print.asm's `(` case says the contract out loud -- *"str_eval left HL
unmoved on failure, so this restores the same cursor exp_num would see
un-gated"*. So the obvious shape for the arm (consume the `+` and fall back into
str_eval_one, mirroring `ev_f_pos`'s loop) would have handed every one of those a
cursor moved past a `+` they had not consumed.

🎯 AND THE CASE THAT WOULD HAVE HIDDEN IT IS THE OBVIOUS ONE. `PAINT(x,y),+1`
and `PRINT +1` give the SAME ANSWER whether or not the `+` was wrongly eaten,
because unary plus is the identity and the numeric factor decoder has its own
`+` arm since D-UNARYPLUS. Two rules coincide on every row anybody would think to
write [[two-rules-that-coincide-on-every-row-you-have]], so the rows here are
chosen for where they SEPARATE: an operand after the `+` that is not a bare
literal, a relational operator after a unary-plus string, a concatenation tail
after one, and a `+` with nothing behind it at all.

Every row reads all three machines. A row that AGREES is only evidence if it
could have disagreed -- `d.paren` and `c.plain` are here as the controls that
say the instrument is looking at the right thing.
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
    ("c.plain",   'A=5',            'A',         'CONTROL: no unary operator at all'),
    ("d.num",     '',               '+1',        'PRINT declines to the numeric path'),
    ("d.numvar",  'A=5',            '+A',        '...on a numeric VARIABLE'),
    ("d.numexpr", 'A=5',            '+A*2',      '🎯 an operand the `+` must not eat into: '
                                                 'a wrongly-advanced cursor still reads 10, so '
                                                 'this row is the SHAPE, not the separator'),
    ("d.dblnum",  '',               '++1',       'two pluses, both declining'),
    ("d.paren",   'A=5',            '(A+1)',     'CONTROL: the `(` arm still declines to '
                                                 'exp_num (p.numprint\'s subject)'),
    ("d.negplus", '',               '+(-3)',     'plus in front of a parenthesised negative'),
    ("s.concat",  'A$="X":B$=+A$+"Y"', 'B$',     '🔴 str_concat_tail AFTER a unary plus'),
    ("s.relop",   'A$="X"',         '+A$="X"',   '🔴 exp_strvar re-parses via eval when a '
                                                 'relop follows -- from the operand START, '
                                                 'which is now the `+`'),
    ("s.prconcat", 'A$="X"',        '+A$+"Y"',   'concat in the PRINT item position'),
    ("s.dblstr",  'A$="X":B$=++A$', 'B$',        '🔴 str_eval_plus RECURSES where ev_f_pos '
                                                 'loops: two frames deep'),
    ("e.bare",    'A$=+',           '"UNREACHED"', '🔴 a `+` with NOTHING behind it -- the '
                                                 'decline with the cursor at end of line'),
    ("g.paint",   'SCREEN 2:PAINT(10,10),+99', '"UNREACHED"',
                                                 '🔴 the PAINT colour DETECTOR. An '
                                                 'OUT-OF-RANGE colour on purpose: it errors '
                                                 'in gfx_store_colour_checked BEFORE any '
                                                 'flood, which is what makes the row '
                                                 'readable at all -- `+1` on a blank SCREEN '
                                                 '2 paints the whole screen and the first '
                                                 'cut read <NO READING> on ALL THREE. What '
                                                 'it separates is the CODE: 5 means `+99` '
                                                 'reached gfx_eval_int16 as a number, 13 '
                                                 'would mean str_eval_one had claimed it'),
]


def run(side, setup, expr):
    machine, boot, reset = SIDES[side]
    prog = ['10 ON ERROR GOTO 90', f'20 {setup}',
            f'30 PRINT"ZQ0|";{expr};"|QZ":END',
            # 🔴 THE LEADING `PRINT:` IS LOAD-BEARING. `PRINT +A$` errors PART
            # WAY THROUGH line 30's PRINT, which has already emitted `ZQ0|` and
            # left the cursor mid-row -- so without a fresh line the handler's
            # text lands on the SAME row and the fence reads `ZQ0|ZQ 13 ||QZ` as
            # a SUCCESS whose value is `ZQ 13 |`. Measured: that is exactly what
            # x.prstr reported before this line existed.
            # 🔴 `SCREEN 0` IN THE HANDLER, ADDED AFTER g.paint READ <NO
            # READING> ON ALL THREE MACHINES TWICE. The row leaves the machine in
            # SCREEN 2, and the fence is a TEXT-row scan: the handler's own
            # output is drawn as a graphics pattern the reader cannot see. It
            # looked like a paint that never finished -- the second cut swapped
            # the colour for an out-of-range one that errors BEFORE any flood,
            # and the cells stayed blank, which is what said the mode was the
            # cause and the flood was not.
            '90 SCREEN 0:PRINT:PRINT"ZQ";ERR;"||QZ":END', 'RUN']
    raw = "".join(omsx_repl.run_cases(
        machine, [("direct", list(reset) + prog)], batch=False, reset=(),
        boot=boot, step=6.0, cap_gap=10.0, timeout=300.0)[0] or "")
    # 🔴 TWO FENCE FAULTS, AND THE FIRST DRAFT HAD BOTH.
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
        tag = "refs agree" if v[0] == v[1] else "🔴 REFS SPLIT"
        d = v[1] != v[2]
        diff += d
        print(f"{lab:<{w}} {v[0]:>12} {v[1]:>12} {v[2]:>12}   "
              f"{setup} / PRINT {expr}   {tag}"
              + ("  🔴 zb DIFF" if d else ""))
        print(f"{'':<{w}}   {why}")
    print(f"\n{diff} row(s) where zerobas differs from the CF-3300.")
    # 🔴 A RUN THAT READ NOTHING IS NOT A RUN THAT AGREED. The first draft of
    # this probe reported "0 row(s) differ" with every cell `<NO READING>`,
    # because the echo anchor never matched zerobas's prompt. REFUSE instead.
    if blind:
        print(f"🔴 {blind} of {3 * len(cases)} cell(s) read <NO READING> -- "
              f"that is the INSTRUMENT, not the machines. This run is refused.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
