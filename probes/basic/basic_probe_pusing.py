#!/usr/bin/env python3
r"""D-PUFLOAT — the FULL contract of PRINT USING's six missing float specifiers.

D-PUSING found them (15 rows, 10 DIFF) and filed the item UNPRICED, saying the
slice "needs its own rows before any byte". These are those rows.

🔴 THE FILED "10 DIFF" IS NOT 10 DEFECTS, AND THE ITEM'S OWN PROSE SAYS SO WHILE
ITS HEADLINE DOES NOT. Three of the ten are REFERENCES-DISAGREE:

    f.dollar  `PRINT USING"$$##";5`   vg8020 `  $5`   cf3300 `$$ 5`
    s.amp     `PRINT USING"&";"ABC"`  vg8020 `ABC`    cf3300 `ERR 5`
    s.slash   `\   \` with "ABCDE"    vg8020 `ABCDE`  cf3300 `ERR 5`

Re-measured 2026-09-03: the split still stands. 🎯 AND ZEROBAS TAKES A DIFFERENT
SIDE IN EACH -- it matches the CF-3300 on `$$` and the VG-8020 on `&`/`\ \`.
Each is individually defensible; the COMBINATION is not obviously either
machine, and that is worth naming rather than averaging. Those rows are carried
here as NO-ORACLE: printed, never scored, never counted as defects.

So the real set is 7 rows over SIX specifiers: `.` `,` `+` `-` `**` `^^^^`.

🔴 AND THE `c.*` CONTROLS WERE TOO NARROW TO NOTICE THE BIGGEST PROBLEM. Every
one of them used a SMALL INTEGER, so all three agreed -- and that agreement read
as "the plain `#` field is already right". It is not: `PRINT USING"#######"` with
1234567 answers **0** here and 1234567 on both references, and `USING"#####"`
with 1.5 answers **1** where both references ROUND to 2. Neither involves a
specifier. `pu_do_number` calls `eval` for a 16-bit DE and formats it with
`pu_fmt_int`, so the whole numeric field is integer-only and truncating.
🎯 THAT REFRAMES THE REMAINING WORK: `.` `,` and `^^^^` are not three independent
slices but ONE -- PRINT USING needs a FLOAT renderer, and that renderer fixes
`c.over16` and `c.round` on the way past.

⚠️ THIS PROBE DOES NOT SCORE ZEROBAS AT ALL YET. Its job is to establish what the
REFERENCES do across each specifier's corners -- rounding, negatives, overflow,
and the combinations -- because the implementation does not exist and every zb
cell would simply read the integer formatter's answer. A row set written against
one example per specifier is how a formatter ships correct on the example and
wrong on the case beside it. The `agree` column is the ORACLE: it says the two
references agree, which is what makes a row usable as a target at all.
"""
import argparse, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

SIDES = {
    "vg8020": ("Philips_VG_8020", 8.0, ("NEW",)),
    "cf3300": ("National_CF-3300", 14.0, ("", "SCREEN 0", "NEW")),
    "zb": (os.environ.get("ZEROBAS_BASIC_MACHINE",
                          "C-BIOS_MSX1_EU_REPACK_DISK"), 8.0, ("NEW",)),
}

CASES = [
    # 🟢 CONTROLS: the integer field, which already works -------------------
    ("c.hash",     'PRINT USING"###";5'),
    ("c.neg",      'PRINT USING"###";-5'),
    ("c.over",     'PRINT USING"##";12345'),
    # 🔴 THE CONTROLS ABOVE ALL USED SMALL INTEGERS, AND THAT IS WHY THIS HID.
    # They agreed, and agreement was read as "the plain `#` field is fine". These
    # four say otherwise, and none of them involves a SPECIFIER at all:
    ("c.max",      'PRINT USING"#######";32767'),      # the int16 ceiling: agrees
    ("c.over16",   'PRINT USING"#######";1234567'),    # past it: refs 1234567, here 0
    ("c.round",    'PRINT USING"#####";1.5'),          # refs ROUND to 2, here 1
    ("c.round2",   'PRINT USING"#####";2.5'),          # which way at the tie?
    ("c.negmax",   'PRINT USING"#######";-32768'),

    # --- '.' the decimal point --------------------------------------------
    ("d.basic",    'PRINT USING"##.##";1.5'),
    ("d.int",      'PRINT USING"##.##";5'),
    ("d.neg",      'PRINT USING"##.##";-1.5'),
    ("d.round",    'PRINT USING"##.#";1.25'),
    ("d.round2",   'PRINT USING"##.#";1.35'),
    ("d.roundup",  'PRINT USING"##.";1.5'),
    ("d.lead",     'PRINT USING".##";.5'),
    # `.##` prints `.50` but `#.##` prints `0.50`, so the leading zero is NOT a
    # property of the value -- it belongs to the format's INTEGER COLUMN. These
    # pin what a leading `.` field does when there is no such column at all.
    ("d.leadover", 'PRINT USING".##";1.5'),
    ("d.leadone",  'PRINT USING".#";.5'),
    ("d.leadzer",  'PRINT USING".##";0'),
    ("d.leadneg",  'PRINT USING".##";-.5'),
    ("d.leadrnd",  'PRINT USING".#";.25'),
    ("d.leadzero", 'PRINT USING"#.##";.5'),
    ("d.over",     'PRINT USING"#.##";12.5'),
    ("d.wide",     'PRINT USING"####.####";3.14159'),
    ("d.zero",     'PRINT USING"##.##";0'),
    # The two CARRY-GROWTH cases. Rounding at N places can make the number gain
    # an integer digit, which moves the point one column right -- the shape the
    # renderer's `inc c` exists for, and the shape the reverted D-PUDOT attempt
    # got wrong. Both existed only as MODEL predictions until this row set;
    # neither is exercised by any other d.* row, so without them the knife arm
    # for that branch would be a designed no-op.
    ("d.grow",     'PRINT USING"##.";9.5'),
    ("d.growfrac", 'PRINT USING"##.#";9.99'),

    # --- ',' the thousands separator ---------------------------------------
    ("m.basic",    'PRINT USING"#,###";1234'),
    ("m.small",    'PRINT USING"#,###";123'),
    ("m.big",      'PRINT USING"##,###,###";1234567'),
    ("m.dot",      'PRINT USING"#,###.##";1234.5'),
    ("m.neg",      'PRINT USING"#,###";-1234'),
    # Three cases the original five cannot answer, all load-bearing for the
    # SCANNER (where a `,` may legally sit) rather than the renderer.
    # 🎯 `m.pos` SEPARATES TWO RULES that agree on every other row: commas every
    # three digits FROM THE RIGHT, versus commas at the positions the format's own
    # `,` characters occupy. Here they differ in LENGTH -- every-3 gives
    # `12,345,678` (10) which OVERFLOWS a 9-wide field, format-positions gives
    # `1234,5678` (9) which fits. `m.small` separates them too, less loudly.
    ("m.pos",      'PRINT USING"####,####";12345678'),
    ("m.trail",    'PRINT USING"##,";5'),
    ("m.lead",     'PRINT USING",##";5'),
    # 🎯 THE ALIAS ROW. PU_DEC / PU_COMMAS share PU_WP, `pu_fmt_int`'s scratch,
    # on the argument that a field with `.` or `,` never takes the pu_fmt_int
    # path. ONE format string with BOTH a plain field and a `.` field is the
    # statement that breaks first if that ever stops holding.
    ("x.mixed",    'PRINT USING"## ##.##";5;1.5'),

    # --- '+' explicit sign --------------------------------------------------
    ("p.lead",     'PRINT USING"+##";5'),
    ("p.leadneg",  'PRINT USING"+##";-5'),
    ("p.trail",    'PRINT USING"##+";5'),
    ("p.trailneg", 'PRINT USING"##+";-5'),
    ("p.dot",      'PRINT USING"+##.##";1.5'),

    # --- '-' trailing minus -------------------------------------------------
    ("n.pos",      'PRINT USING"##-";5'),
    ("n.neg",      'PRINT USING"##-";-5'),
    ("n.dot",      'PRINT USING"##.##-";-1.5'),

    # --- '**' asterisk fill --------------------------------------------------
    ("a.basic",    'PRINT USING"**##";5'),
    ("a.neg",      'PRINT USING"**##";-5'),
    ("a.full",     'PRINT USING"**##";1234'),
    ("a.dot",      'PRINT USING"**#.##";1.5'),

    # --- '^^^^' exponential --------------------------------------------------
    ("e.basic",    'PRINT USING"##.##^^^^";1.5'),
    ("e.big",      'PRINT USING"#.#^^^^";1234'),
    ("e.small",    'PRINT USING"#.#^^^^";.001'),
    ("e.neg",      'PRINT USING"##.##^^^^";-1.5'),
    ("e.zero",     'PRINT USING"##.##^^^^";0'),
    # The five original `e.*` rows do NOT pin the normalisation rule. `##.##`
    # yields `1.50E+00` (ONE integer digit) but `#.#` yields `0.1E+04` (ZERO), so
    # "always one integer digit" and "one column is the sign" both fit the five.
    # 🎯 `e.wide` SEPARATES THEM: with 3 integer slots, "int_slots - 1 digits"
    # predicts ` 15.00E-01` and "always one digit" predicts `  1.50E+00`.
    ("e.wide",     'PRINT USING"###.##^^^^";1.5'),
    ("e.negtight", 'PRINT USING"#.#^^^^";-1234'),
    ("e.round",    'PRINT USING"#.#^^^^";.0999'),
    ("e.car3",     'PRINT USING"##.##^^^";1.5'),
    ("e.car5",     'PRINT USING"##.##^^^^^";1.5'),
    # The renderer plan reads `flt_fmt`'s DECIMAL TEXT and shifts the point
    # symbolically, so it needs to know (a) whether `^^^^` is legal with no `.`
    # at all, and (b) what happens when flt_fmt would itself go exponential --
    # the case where the text being parsed is not a plain digit run.
    ("e.nodot",    'PRINT USING"##^^^^";1.5'),
    ("e.huge",     'PRINT USING"##.##^^^^";1.5E+10'),
    ("e.tiny",     'PRINT USING"##.##^^^^";1.5E-10'),
    # What `flt_fmt` itself produces for these values -- i.e. the exact TEXT the
    # exponent renderer will be parsing. If it is already exponential for the big
    # and small ones, the renderer cannot assume a plain digit run.
    ("f.big",      'PRINT 1.5E+10'),
    ("f.small",    'PRINT 1.5E-10'),
    ("f.frac",     'PRINT .0999'),
    # Does `^^^^` COMBINE with the other specifiers? The answer decides whether
    # the exponent path may reuse PU_COMMAS for its own scratch, which is the
    # same alias question §13.2 got wrong once already -- so it is measured.
    ("e.comma",    'PRINT USING"#,###.##^^^^";1234.5'),
    ("e.sign",     'PRINT USING"+##.##^^^^";1.5'),
    ("e.star",     'PRINT USING"**##.##^^^^";1.5'),
    # A point with ZERO places AND an exponent. The n formula subtracts a column
    # for the point, so this is the one shape where "no places" and "no point"
    # stop coinciding -- measured rather than reasoned about.
    ("e.dot0",     'PRINT USING"##.^^^^";1.5'),

    # --- ⚠️ NO-ORACLE: printed, never scored --------------------------------
    ("x.dollar",   'PRINT USING"$$##";5'),
    ("x.amp",      'PRINT USING"&";"ABC"'),
    ("x.slash",    'PRINT USING"\\   \\";"ABCDE"'),
]

# rows whose two references DISAGREE: carried for the record, never scored
NO_ORACLE = {"x.dollar", "x.amp", "x.slash"}


def run(side, stmt):
    machine, boot, reset = SIDES[side]
    prog = ['10 ON ERROR GOTO 90', '20 PRINT"<";', f'30 {stmt};',
            '40 PRINT">":END', '90 PRINT"<ERR";ERR;">"', 'RUN']
    raw = omsx_repl.run_cases(machine, [("direct", list(reset) + prog)],
                              batch=False, reset=(), boot=boot, step=5.0,
                              cap_gap=10.0, timeout=300.0)[0] or ""
    m = re.findall(r"<([^<>]*)>", "".join(raw))
    return repr(m[-1]) if m else "<NO OUTPUT>"


# --- EXPECT: the reference answer for every row with an oracle ---------------
# 🎯 THE GATE RUNS ZEROBAS ONLY, AGAINST THESE. A gate measures with the refcache
# OFF, and re-booting both references for 67 rows is ~140 extra boots -- twenty
# minutes, on a battery whose tent-pole is seven. The references do not change;
# zerobas does, and a regression in zerobas is what this exists to catch.
#
# ⚠️ SO THESE PINS CAN ROT, and the mitigation is that they are never hand-typed:
# `--refresh` re-measures both references and rewrites this block, and the plain
# (no-argument) run still boots all three sides and scores the references against
# each other. Measured 2026-09-04, 67 rows with an oracle, 0 divergent.
EXPECT = {
    'c.hash'        : "'  5'",
    'c.neg'         : "' -5'",
    'c.over'        : "'%12345'",
    'c.max'         : "'  32767'",
    'c.over16'      : "'1234567'",
    'c.round'       : "'    2'",
    'c.round2'      : "'    3'",
    'c.negmax'      : "' -32768'",
    'd.basic'       : "' 1.50'",
    'd.int'         : "' 5.00'",
    'd.neg'         : "'-1.50'",
    'd.round'       : "' 1.3'",
    'd.round2'      : "' 1.4'",
    'd.roundup'     : "' 2.'",
    'd.lead'        : "'.50'",
    'd.leadover'    : "'%1.50'",
    'd.leadone'     : "'.5'",
    'd.leadzer'     : "'.00'",
    'd.leadneg'     : "'%-.50'",
    'd.leadrnd'     : "'.3'",
    'd.leadzero'    : "'0.50'",
    'd.over'        : "'%12.50'",
    'd.wide'        : "'   3.1416'",
    'd.zero'        : "' 0.00'",
    'd.grow'        : "'10.'",
    'd.growfrac'    : "'10.0'",
    'm.basic'       : "'1,234'",
    'm.small'       : "'  123'",
    'm.big'         : "' 1,234,567'",
    'm.dot'         : "'1,234.50'",
    'm.neg'         : "'%-1,234'",
    'm.pos'         : "'%12,345,678'",
    'm.trail'       : "'  5'",
    'm.lead'        : "', 5'",
    'x.mixed'       : "' 5  1.50'",
    'p.lead'        : "' +5'",
    'p.leadneg'     : "' -5'",
    'p.trail'       : "' 5+'",
    'p.trailneg'    : "' 5-'",
    'p.dot'         : "' +1.50'",
    'n.pos'         : "' 5 '",
    'n.neg'         : "' 5-'",
    'n.dot'         : "' 1.50-'",
    'a.basic'       : "'***5'",
    'a.neg'         : "'**-5'",
    'a.full'        : "'1234'",
    'a.dot'         : "'**1.50'",
    'e.basic'       : "' 1.50E+00'",
    'e.big'         : "'0.1E+04'",
    'e.small'       : "'0.1E-02'",
    'e.neg'         : "'-1.50E+00'",
    'e.zero'        : "' 0.00E+00'",
    'e.wide'        : "' 15.00E-01'",
    'e.negtight'    : "'-.1E+04'",
    'e.round'       : "'0.1E+00'",
    'e.car3'        : "' 1.50^^^'",
    'e.car5'        : "' 1.50E+00^'",
    'e.nodot'       : "' 2E+00'",
    'e.huge'        : "' 1.50E+10'",
    'e.tiny'        : "' 1.50E-10'",
    'f.big'         : "' 15000000000 '",
    'f.small'       : "' 1.5E-10 '",
    'f.frac'        : "' .0999 '",
    'e.comma'       : "' 1234.50E+00'",
    'e.sign'        : "'+15.00E-01'",
    'e.star'        : "'*150.00E-02'",
    'e.dot0'        : "' 2.E+00'",
}

# rows the references answer differently from each other are NOT in EXPECT at all
# (NO_ORACLE above); they are printed by the survey run and invisible to the gate.


def survey(sides):
    """Boot every side and score the REFERENCES against each other."""
    res = {s: {lab: run(s, st) for lab, st in CASES} for s in sides}
    w = max(len(l) for l, _ in CASES)
    print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>22}" for s in sides) + "   oracle")
    agree = disagree = 0
    for lab, _ in CASES:
        vals = [res[s][lab] for s in sides]
        if lab in NO_ORACLE:
            tag = "NO-ORACLE (refs split; recorded, not scored)"
        elif len(sides) >= 2 and vals[0] == vals[1]:
            tag = "refs agree -> usable target"; agree += 1
        else:
            tag = "🔴 REFS DISAGREE -- not a target"; disagree += 1
        print(f"{lab:<{w}}  " + "  ".join(f"{v:>22}" for v in vals) + f"   {tag}")
    print(f"\nreferences agree on {agree} row(s); disagree on {disagree}; "
          f"{len(NO_ORACLE)} carried as NO-ORACLE")
    return res


def gate(side):
    """Score `side` against EXPECT. rc=1 on any divergence or missing capture."""
    w = max(len(l) for l, _ in CASES)
    bad, blank, missing = [], [], []
    print(f"\n{'row':<{w}}  {'expected':>22}  {side:>22}   verdict")
    for lab, st in CASES:
        if lab not in EXPECT:
            continue                        # NO-ORACLE: nothing to hold it to
        got, want = run(side, st), EXPECT[lab]
        if got == "<NO OUTPUT>":
            blank.append(lab); tag = "🔴 UNREADABLE"
        elif got == want:
            tag = "ok"
        else:
            bad.append(lab); tag = "🔴 DIVERGES"
        print(f"{lab:<{w}}  {want:>22}  {got:>22}   {tag}")
    # ⚠️ A ROW THAT VANISHES FROM `CASES` WOULD OTHERWISE PASS SILENTLY: the loop
    # scores what it finds, so a deleted row is a row that cannot fail. Compare
    # the two sets rather than trusting the walk.
    missing = sorted(set(EXPECT) - {l for l, _ in CASES})
    if missing:
        print(f"🔴 {len(missing)} PINNED ROW(S) NO LONGER IN THE CASE TABLE: "
              + " ".join(missing))
    print(f"\nscored {len(EXPECT) - len(missing)}  divergent {len(bad)}  "
          f"unreadable {len(blank)}  vanished {len(missing)}")
    print("PUSING: PASS" if not (bad or blank or missing)
          else f"PUSING: RED ({len(bad) + len(blank) + len(missing)})")
    return bad + blank + missing


def refresh():
    """Re-measure both references and rewrite the EXPECT block in this file."""
    res = survey(["vg8020", "cf3300"])
    keep = [(l, res["vg8020"][l]) for l, _ in CASES
            if l not in NO_ORACLE and res["vg8020"][l] == res["cf3300"][l]]
    # ⚠️ `v` IS ALREADY A repr() -- run() returns repr(text) so a leading space
    # survives the readout. Writing it bare drops one quote layer and every pin
    # then mismatches by exactly those quotes, which reads as "all 67 rows
    # diverge" rather than as a formatting fault.
    body = "".join(f"    {l!r:16}: {v!r},\n" for l, v in keep)
    src = open(__file__).read()
    a = src.index("EXPECT = {\n") + len("EXPECT = {\n")
    b = src.index("}\n", a)
    open(__file__, "w").write(src[:a] + body + src[b:])
    print(f"\nEXPECT rewritten: {len(keep)} row(s) with an oracle")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sides", nargs="?", default="vg8020,cf3300,zb")
    ap.add_argument("--gate", action="store_true",
                    help="score zerobas against EXPECT; rc=1 on any red")
    ap.add_argument("--refresh", action="store_true",
                    help="re-measure the references and rewrite EXPECT")
    a = ap.parse_args()
    if a.refresh:
        refresh(); return 0
    if a.gate:
        return 1 if gate("zb") else 0
    survey(a.sides.split(","))
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
