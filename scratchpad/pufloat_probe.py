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
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    ("d.leadzero", 'PRINT USING"#.##";.5'),
    ("d.over",     'PRINT USING"#.##";12.5'),
    ("d.wide",     'PRINT USING"####.####";3.14159'),
    ("d.zero",     'PRINT USING"##.##";0'),

    # --- ',' the thousands separator ---------------------------------------
    ("m.basic",    'PRINT USING"#,###";1234'),
    ("m.small",    'PRINT USING"#,###";123'),
    ("m.big",      'PRINT USING"##,###,###";1234567'),
    ("m.dot",      'PRINT USING"#,###.##";1234.5'),
    ("m.neg",      'PRINT USING"#,###";-1234'),

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


sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
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
print("done")
