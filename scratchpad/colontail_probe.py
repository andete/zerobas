#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-COLONTAIL — does every statement CONTINUE its line? The class D-DATACOLON found one member of.

D-DATACOLON (2026-08-31) measured that bare `RESTORE`'s `ret` ended the WHOLE
LINE, because the dispatcher enters handlers by push/ret -- so `RESTORE:C=9`
skipped `C=9`. One verb was fixed. **The CLASS was never swept**, and it is a
structural property every statement handler must have: end with `jp exec_stmt`,
not `ret`.

\U0001f3af THE METHOD IS THE ONE THAT JUST FOUND D-MERGEXPR: ask a rule that should
hold across a whole class, then check every member, rather than reading one verb
and hoping. Here the rule is *"a statement continues its line"* and the test is
one line per verb.

    <VERB> <minimal legal args> : PRINT"ZQ";1;"QZ"

If the fence prints, the verb continued its line. If it does not, the verb
swallowed the rest -- which is the D-DATACOLON defect, in whatever verb it is.

⚠️ ONLY VERBS WITH A LEGAL, SIDE-EFFECT-TOLERABLE MINIMAL FORM ARE HERE, and none
needs a disk. A verb whose minimal form ERRORS would abort the line on BOTH
machines and read as agreement while measuring nothing
[[an-unnamed-outcome-reads-as-no-outcome]].

⚠️ BOOT PER CASE (`batch=False`). These verbs change machine STATE -- `SCREEN`,
`WIDTH`, `COLOR`, `KEY`, `TRON` -- and in a batched run one case's state is the
next case's environment. `TRON` in particular would trace every later line.

\U0001f534 `c.ctl` IS THE ROW THAT MAKES A BLANK MEAN SOMETHING: a bare
`PRINT"ZQ";1;"QZ"` with no verb in front. If it does not print, the fence or the
typing is broken and every blank below it is apparatus, not a finding.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "zb": dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                      "C-BIOS_MSX1_EU_REPACK_DISK"),
               boot=10.0, reset=("NEW",)),
}
FENCE = 'PRINT"ZQ";1;"QZ"'

# (tag, the statement to put before the colon)
VERBS = [
    ("c.ctl",      None),                 # no verb at all -- the control
    ("restore",    "RESTORE"),            # D-DATACOLON's own verb: the positive precedent
    ("cls",        "CLS"),
    ("tron",       "TRON"),
    ("troff",      "TROFF"),
    ("beep",       "BEEP"),
    ("motoroff",   "MOTOR OFF"),
    ("keyoff",     "KEY OFF"),
    ("width",      "WIDTH 40"),
    ("color",      "COLOR 15,4,4"),
    ("screen",     "SCREEN 0"),
    ("sound",      "SOUND 0,0"),
    ("poke",       "POKE&HC000,0"),
    ("vpoke",      "VPOKE 0,0"),
    ("defint",     "DEFINT Z"),
    ("clear",      "CLEAR"),
    ("maxfiles",   "MAXFILES=1"),
    ("time",       "TIME=0"),
    ("locate",     "LOCATE 0,0"),
    # 🔴 THE FIRST CUT OF THESE TWO MEASURED NOTHING, AND AGREED WHILE DOING IT.
    # `OUT &H99,0` writes the VDP CONTROL port, which latches half a register
    # write and leaves the display in a state where the fence cannot be read;
    # `WAIT &H99,0,0` has an AND-mask of 0, so `(INP xor 0) and 0` is 0 forever --
    # the row asked the machine to hang and both machines obliged. Blank on both
    # is what "the verb swallowed the line" looks like too
    # [[an-unnamed-outcome-reads-as-no-outcome]].
    ("out",        "OUT &HA0,0"),        # PSG register-select: harmless
    ("wait",       "WAIT &H99,128"),     # D-WAIT's own VBLANK form, known to return
    ("swap",       "SWAP A,B"),
    ("erase",      "ERASE Q"),
    ("randomize",  "RANDOMIZE 1"),   # in NEXTLINE: see the note above PRE
    ("lprintempty", None),                # placeholder removed below
]
VERBS = [v for v in VERBS if v[0] != "lprintempty"]

PRE = {"erase": "5 DIM Q(2)", "swap": "5 A=1:B=2"}

# 🎯 THE SEPARATOR FOR A ROW THAT BLANKS ON BOTH. "The verb ended the LINE"
# and "the verb BLOCKED" are the same blank. NEXTLINE puts the fence on its own
# numbered line instead of after a colon: if it prints, the verb ended the line
# and the program went on; if it does not, the verb never returned at all.
NEXTLINE = {"randomize"}


def value(scr):
    if scr is None:
        return None
    for g in reversed(re.findall(r"ZQ\s*([0-9]*)\s*QZ", scr)):
        if any(ch in g for ch in '"$;'):
            continue
        try:
            return int(g)
        except ValueError:
            continue
    return None


def main() -> int:
    out = {}
    for tag, verb in VERBS:
        prog = ([PRE[tag]] if tag in PRE else []) + (
            [f'10 {verb}', f'20 {FENCE}'] if tag in NEXTLINE else
            [f'10 {verb}:{FENCE}' if verb else f'10 {FENCE}'])
        row = {}
        for side, c in SIDES.items():
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + prog + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0,
                run_gap=12.0, cap_gap=4.0, timeout=420.0)[0] or "")
            row[side] = value(raw)
        out[tag] = row
        f = {s: ("continued" if row[s] == 1 else
                 ("SWALLOWED" if row[s] is None else f"?{row[s]}")) for s in SIDES}
        mark = "" if f["vg8020"] == f["zb"] else "   \U0001f534 DIFF"
        print(f"  {tag:11s} {str(verb):16s} vg={f['vg8020']:10s} "
              f"zb={f['zb']:10s}{mark}", flush=True)

    if out.get("c.ctl", {}).get("vg8020") != 1 or out.get("c.ctl", {}).get("zb") != 1:
        print(f"\n\U0001f534 THE CONTROL DID NOT PRINT ({out.get('c.ctl')}) -- the "
              f"fence or the typing is broken, and every SWALLOWED below is "
              f"apparatus rather than a finding.")
        return 2
    dis = [k for k, v in out.items() if v["vg8020"] != v["zb"]]
    both = [k for k, v in out.items()
            if k != "c.ctl" and v["vg8020"] is None and v["zb"] is None]
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    if both:
        print(f"    NB {both} blank on BOTH. For `randomize` the reason is "
              f"ESTABLISHED and it is not the colon rule: with the fence on its "
              f"OWN numbered line it is still blank, so `RANDOMIZE 1` never "
              f"RETURNS on either machine -- it blocks, agreeing, and this "
              f"instrument cannot say anything about its line handling. Any "
              f"OTHER tag appearing here has not been explained and must be "
              f"before it is read as agreement.")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
