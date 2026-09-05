#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-SCRARITY — does SCREEN's five-argument bound count COMMAS or VALUES?

D-SCRSLOT measured `SCREEN 1,,,,,1` as **ERR 2** on both references and ACCEPTED
here, and priced a fix. It did not measure the case that says WHERE the bound
lives, and the two candidate rules agree on every row it has
[[two-rules-that-coincide-on-every-row-you-have]]:

  RULE A  the bound is on the COMMA COUNT -- a 6th argument SLOT is ERR 2
          whether or not anything is in it.
  RULE B  the bound is on a VALUE's slot index -- only a 6th argument that is
          actually PRESENT is ERR 2.

`SCREEN 1,,,,,1` has a value in slot 6, so BOTH rules fire and the row cannot
choose. Implementing the wrong one ships a regression that no filed row can see:
zerobas counts at the comma (`ex_screen`, basic/screen.asm) precisely because an
omitted argument never reaches `spr_extra_arg`, so rule A is one instruction
there and rule B is not.

🎯 THE SEPARATOR IS `SCREEN 1,,,,,` -- six slots, the sixth EMPTY, at end of
line. Under rule A that is ERR 2. Under rule B the 6th slot holds nothing, so
the bound is silent and what answers instead is the rule that a comma PROMISES
an argument: **ERR 24**, which both references already give for `SCREEN 2,`.
So the row reads 2 or 24 and those are different rules, not different wordings.

⚠️ THE STATEMENT MUST END THE LINE. `SCREEN 1,,,,,:SCREEN 0` is a DIFFERENT
question -- the `:` after a trailing comma is the `SCREEN 2,:` case, already
measured as ERR 24 -- so the mode reset gets its own line number and never
shares one with the subject.

⚠️ AND THE HANDLER MUST LEAVE GRAPHICS MODE BEFORE IT PRINTS. Every row seeds
`SCREEN 1`; the fence is a TEXT-row scan, so without the `SCREEN 0` the answer is
drawn where the reader cannot see it and every cell reads <NO READING> -- measured
this session on a PAINT row that looked like a hung flood and was not.
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

CASES = [
    ("c.plain",   "SCREEN 1",          "CONTROL: the bare mode, no trailing list"),
    ("c.one",     "SCREEN 1,1",        "CONTROL: slot 2 present (sprite size 1)"),
    ("c.trail",   "SCREEN 1,",         "CONTROL: a comma promising nothing -- the "
                                       "ERR 24 rule the separator leans on"),
    ("a.s5val",   "SCREEN 1,,,,1",     "CONTROL: 5 slots, 5th PRESENT -- inside the "
                                       "bound, must be accepted"),
    ("a.s5omit",  "SCREEN 1,,,,",      "CONTROL: 5 slots, 5th EMPTY -- inside the "
                                       "bound, so this reads the promise rule alone"),
    ("a.s6val",   "SCREEN 1,,,,,1",    "the FILED row: 6 slots, 6th present -- ERR 2 "
                                       "on both refs, accepted here. BOTH rules fire"),
    ("a.s6omit",  "SCREEN 1,,,,,",     "🎯 THE SEPARATOR: 6 slots, 6th EMPTY. "
                                       "2 = the bound counts COMMAS; 24 = it counts "
                                       "VALUES and the promise rule answers instead"),
    ("a.s7val",   "SCREEN 1,,,,,,1",   "7 slots, 7th present -- both rules fire again; "
                                       "here to show the bound does not un-fire"),
    ("b.b1",      "SCREEN 1,,,1",      "CONTROL (D-SCRSLOT): baud 1 accepted"),
    ("b.b0",      "SCREEN 1,,,0",      "the filed slot-3 row: ERR 5 there, accepted here"),
    ("b.b3",      "SCREEN 1,,,3",      "...and its upper twin"),
]


def run(side, stmt):
    machine, boot, reset = SIDES[side]
    prog = ['10 ON ERROR GOTO 90',
            '20 SCREEN 1',
            f'30 {stmt}',
            '40 SCREEN 0',
            '50 PRINT"ZQ0|NOERR|QZ":END',
            '90 SCREEN 0:PRINT:PRINT"ZQ";ERR;"||QZ":END',
            'RUN']
    raw = "".join(omsx_repl.run_cases(
        machine, [("direct", list(reset) + prog)], batch=False, reset=(),
        boot=boot, step=6.0, cap_gap=10.0, timeout=300.0)[0] or "")
    # Only rows whose own text BEGINS with the fence: an ECHO of the source can
    # never start with it, because the prompt and line number precede it.
    for line in raw.splitlines():
        t = line.strip()
        if t.startswith("ZQ0|") and "|QZ" in t:
            return "ok"
        if t.startswith("ZQ") and "||QZ" in t:
            m = re.match(r"ZQ\s*(-?\d+)\s*\|\|QZ", t)
            if m:
                return f"ERR {int(m.group(1))}"
    return "<NO READING>"


def main():
    w = 10
    print(f"\n{'row':<{w}} {'vg8020':<14} {'cf3300':<14} {'zb':<14}  statement")
    blind = 0
    diff = []
    for lab, stmt, why in CASES:
        v = [run(s, stmt) for s in ("vg8020", "cf3300", "zb")]
        blind += sum(1 for x in v if x == "<NO READING>")
        split = "refs agree" if v[0] == v[1] else "🔴 REFS SPLIT"
        zb = ""
        if v[1] != v[2]:
            zb = "  🔴 zb DIFF"
            diff.append(lab)
        print(f"{lab:<{w}} {v[0]:<14} {v[1]:<14} {v[2]:<14}  {stmt:<18} "
              f"{split}{zb}")
        print(f"{'':<{w}} {why}")
    print(f"\n{len(diff)} row(s) where zerobas differs from the CF-3300: {diff}")
    if blind:
        # 🔴 A BLIND CELL IS THE INSTRUMENT, NOT A MACHINE, AND IT MUST NOT BE
        # SCORED. Refusing is what stops "0 rows differ" being printed by a probe
        # that read nothing [[readout-blind-to-its-own-subject]].
        print(f"🔴 {blind} cell(s) read <NO READING> -- that is the INSTRUMENT. "
              f"This run is refused.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
