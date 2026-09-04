#!/usr/bin/env python3
r"""D-MISSOPERR — the ERR CODE behind `Missing operand`, which is filed unmeasured.

The `SAVE`/`LOAD`/`BLOAD`-with-no-argument entry says the reference prints
`Missing operand in 10` and that *"the MSX ERR code for it is not measured, only
the wording"*. A message needs a code before it can be priced, so this reads it.

🎯 `ON ERROR` + `ERR` IS THE WHOLE INSTRUMENT. The original measurement had to
read the screen directly because the probe's classifier could not name the
message; a numeric `ERR` needs no classifier and cannot be misread as
`<NO OUTPUT>`.

Controls: `c.ok` must print 0 (no error at all), and `c.syn` is a REAL syntax
error, so if `Missing operand` shares ERR 2 the pair says "same code, different
wording" rather than "the probe cannot tell them apart".
"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

SIDES = {
    "vg8020": ("Philips_VG_8020", 8.0, ("NEW",)),
    "cf3300": ("National_CF-3300", 14.0, ("", "SCREEN 0", "NEW")),
    "zb": ("C-BIOS_MSX1_EU_REPACK_DISK", 8.0, ("NEW",)),
}
CASES = [
    ("m.save",  'SAVE',      'the filed row n.savebare'),
    ("m.load",  'LOAD',      'the filed row n.loadbare'),
    ("m.bload", 'BLOAD',     'the filed row n.bloadbare'),
    ("m.let",   'A$=',       "D-MISS-1's LET mirror, named in the same entry"),
    ("m.letop", 'A$=+',      'the second LET mirror'),
    ("c.syn",   'PRINT)',    'CONTROL: a REAL syntax error'),
    ("c.ok",    'A=1',       'CONTROL: no error at all -> 0'),
]


def run(side, stmt):
    machine, boot, reset = SIDES[side]
    prog = ['10 ON ERROR GOTO 90', f'20 {stmt}', '30 PRINT"<0>":END',
            '90 PRINT"<";ERR;">":END', 'RUN']
    raw = omsx_repl.run_cases(machine, [("direct", list(reset) + prog)],
                              batch=False, reset=(), boot=boot, step=6.0,
                              cap_gap=10.0, timeout=300.0)[0] or ""
    m = re.findall(r"<([^<>]*)>", "".join(raw))
    return " ".join(m[-1].split()) if m else "<NO OUTPUT>"


w = 8
print(f"\n{'row':<{w}} {'vg8020':>8} {'cf3300':>8} {'zb':>8}   statement")
for lab, st, why in CASES:
    v = [run(s, st) for s in ("vg8020", "cf3300", "zb")]
    tag = "refs agree" if v[0] == v[1] else "🔴 REFS SPLIT"
    zb = "" if v[1] == v[2] else "   zb DIFF"
    print(f"{lab:<{w}} {v[0]:>8} {v[1]:>8} {v[2]:>8}   {st:<8} {tag}{zb}   {why}")
print("\nread: the CODE is what a message-table entry needs; the WORDING is already filed.")
