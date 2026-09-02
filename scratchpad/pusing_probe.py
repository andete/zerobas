#!/usr/bin/env python3
r"""D-PUSING — `PRINT USING`'s format-specifier surface, after floats landed.

Review tier, arc-covered group. `ex_print_using`'s claimed cover is
`spec-print-hash-using.md` -- which is the FILE form. Verifying that name:

  * `basic_probe_printusing.py` (the SCREEN probe) is RETIRED, allowlisted in
    probe-reach-allow.txt: its vehicle was a cartridge boot on a real VG-8020 and
    the repack image cannot be a cartridge. The retirement says "the SUBJECT
    survives in spec-print-hash-using.md + disk_probe_printusing_file" -- and
    BOTH of those are the file form.
  * What actually runs covers three format strings: `"## "`, `"###"`, `"[!]"`.
    So `#`, `!` and literals. MSX's specifier set is far wider.

🔴 AND THE IMPLEMENTATION'S OWN HEADER MAY BE STALE. basic/printusing.asm says:
"the float-only format specs -- the decimal point '.', exponential '^^^^', and
the '+'/'-'/','/'**'/'$$' embellishments -- ARRIVE WITH PHASE-3 FLOATS. The '_'
literal-escape is likewise deferred." **Floats have since landed** (SNG/DBL
tokens, the float-pack arc is CONCLUDED, `PRINT 1.5` works), so the condition
that justified deferring them is satisfied and the paragraph was never revisited.
[[a-fix-falsifies-the-justification-beside-it]]

🎯 READOUT: THE RAW SCREEN, NOT THE HARNESS BRACKET. The shared fixture emits
`60 CLS:PRINT"[";<expr>;"]"`, and PRINT USING is a STATEMENT whose output that
CLS would wipe -- the same blindness D-PRINTZONE hit an hour earlier. Rows print
between two markers on one line and the screen is read directly.
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
    # 🟢 CONTROLS: the three specifiers something actually runs today
    ("c.hash",   'PRINT USING"###";5'),
    ("c.hash2",  'PRINT USING"## ";1;2'),
    ("c.bang",   'PRINT USING"!";"AB"'),
    ("c.lit",    'PRINT USING"[#]";7'),
    # --- the specifiers the header defers to "Phase-3 floats" ---------------
    ("f.dot",    'PRINT USING"##.##";1.5'),
    ("f.dotint", 'PRINT USING"##.##";5'),
    ("f.comma",  'PRINT USING"#,###";1234'),
    ("f.plus",   'PRINT USING"+##";5'),
    ("f.minus",  'PRINT USING"##-";5'),
    ("f.dollar", 'PRINT USING"$$##";5'),
    ("f.star",   'PRINT USING"**##";5'),
    ("f.exp",    'PRINT USING"##.##^^^^";1.5'),
    ("f.under",  'PRINT USING"_##";5'),
    # --- string fields the header does NOT defer ----------------------------
    ("s.amp",    'PRINT USING"&";"ABC"'),
    ("s.slash",  'PRINT USING"\\   \\";"ABCDE"'),
]

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
print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>20}" for s in sides) + "   verdict")
diff = []
for lab, _ in CASES:
    vals = [res[s][lab] for s in sides]
    same = len(set(vals)) == 1
    if not same: diff.append(lab)
    print(f"{lab:<{w}}  " + "  ".join(f"{v:>20}" for v in vals)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF: {len(diff)}/{len(CASES)}  " + " ".join(diff))
