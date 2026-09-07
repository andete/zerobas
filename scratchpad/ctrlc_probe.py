#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CTRLC -- Ctrl-C in the ORDINARY line editor, the rule D-AUTO's escape rides on.

D-AUTO measured that both references leave `AUTO` when Ctrl-C ($03) is typed and
zerobas does not, and its `a.noesc` control pinned the ESCAPE as the cause. That
raised the obvious next question, which this probe answers: is $03 an AUTO-mode
key, or is it a LINE-EDITOR key that AUTO merely inherits?

It is the line editor. Typing

    PRINT"ZC";<^C>1;"CZ"<Enter>

prints nothing on VG-8020 and nothing on CF-3300 -- the line is ABORTED, never
executed -- while zerobas printed `1`, because `cp 32 / jr c,rl_loop` in
read_line drops $03 as "some control character" and keeps building the line.

## The rows

  c.plain   the control: the SAME line with no $03. All three must read 1, or
            the fence and the typing say nothing about Ctrl-C.
  c.mid     $03 in the middle of the line -> refs abort.
  c.after   🎯 ABORT IS NOT A WEDGE. An aborted line is followed by an ordinary
            one; every machine must read 9. Without this row "no output" is
            equally consistent with "the REPL died", and a fix that HANGS the
            editor would score identically to the references.
"""
from __future__ import annotations

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
C = "\x03"

CASES = [
    ("c.plain", ['PRINT"ZC";1;"CZ"'],
     "CONTROL: no Ctrl-C -- every machine must read 1"),
    ("c.mid",   ['PRINT"ZC";' + C + '1;"CZ"'],
     "Ctrl-C mid-line -- refs ABORT the line (no reading)"),
    ("c.after", ['PRINT"ZC";' + C + '1;"CZ"', 'PRINT"ZC";9;"CZ"'],
     "CONTROL on the abort: an ordinary line AFTER an aborted one -- every "
     "machine must read 9, or 'no output' means 'the editor is wedged'"),
]


def run(side, prog):
    machine, boot, reset = SIDES[side]
    raw = "".join(omsx_repl.run_cases(
        machine, [("direct", list(reset) + prog)], batch=False,
        reset=(), boot=boot, step=6.0, cap_gap=25.0, timeout=300.0)[0] or "")
    # the fence is in the source the machine echoes: LAST match, and refuse any
    # match still carrying source punctuation [[trapsvc-echo-fence]]
    for g in reversed(re.findall(r"ZC\s*([^C]*)CZ", raw)):
        if any(ch in g for ch in '"$;'):
            continue
        try:
            return str(int(g))
        except ValueError:
            continue
    return "<ABORTED/no reading>"


def main() -> int:
    rows = []
    for tag, prog, note in CASES:
        got = {s: run(s, prog) for s in SIDES}
        rows.append((tag, note, got))
        print(f"  {tag:8s} " + "  ".join(f"{s}={got[s]:>20s}" for s in SIDES),
              flush=True)

    print(f"\n{'row':8s} {'vg8020':>20s} {'cf3300':>20s} {'zb':>20s}   verdict")
    dis, split = [], []
    for tag, note, g in rows:
        v, c, z = g["vg8020"], g["cf3300"], g["zb"]
        if v != c:
            verdict = "REFS SPLIT"; split.append(tag)
        elif z != v:
            verdict = "🔴 DIFF"; dis.append(tag)
        else:
            verdict = "SAME"
        print(f"{tag:8s} {v:>20s} {c:>20s} {z:>20s}   {verdict}")
        print(f"         {note}")
    bad = [t for t, _, g in rows if t == "c.plain" and g["zb"] != "1"]
    if bad:
        print("\n🔴 THE CONTROL c.plain DID NOT READ 1 -- the fence or the typing "
              "is broken, so every row below it says nothing about Ctrl-C.")
        return 2
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'}"
          + (f"; REFS-SPLIT: {split}" if split else "") + " ===")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
