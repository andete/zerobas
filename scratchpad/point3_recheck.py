#!/usr/bin/env python3
"""STALENESS RE-CHECK, not a slice: does POINT still answer wrongly in SCREEN 3?

`TODO.md` carries an item filed 2026-08-22 by the SCREEN 3 SCOUT, §5:

    SCREEN 3 : POINT(30,30) with nothing plotted reads 4 on the VG-8020 and the
    CF-3300 and 1 here, with no error on any side. POINT does not gate the mode.

⚠️ IT WAS FILED BEFORE SCREEN 3 EXISTED. D-SCREEN3 landed the multicolour
address model the same day and `gfx_point` now calls `gfx_is_mc` and branches to
`gfx_point_mc`. This project has found FOUR times that a loud open item had
already shipped, so the item is RE-MEASURED before it is ranked, not reasoned
about.

🔴 A SECOND CAUSE OF AGREEMENT IS EXCLUDED BY THE `.set` ROWS. An undrawn
multicolour cell reading 4 agrees with "the MC read path works" and with "the
SCREEN-2 read path happens to return 4 here" alike -- 4 is the power-on
background in both models. The `.set` rows PSET a colour first, at a coordinate
whose SCREEN-2 and multicolour addresses differ, so only a correct read returns
it. `.s2ctl` is the same question in SCREEN 2, where the answer has never been
in doubt: it separates "POINT is broken" from "this fixture is broken".
"""
from __future__ import annotations
import os, re, sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_M, boot=8.0, reset=("NEW",)),
}
_only = os.environ.get("PT3_SIDES")
if _only:
    SIDES = {k: v for k, v in SIDES.items() if k in _only.split(",")}

CASES = {
    # the filed row, verbatim
    "p3.undrawn":  ["SCREEN 3", "V=POINT(30,30):SCREEN 0:PRINT\"[\";V;\"]\":END"],
    # ...and one that cannot agree by accident
    "p3.set":      ["SCREEN 3:PSET(30,30),9",
                    "V=POINT(30,30):SCREEN 0:PRINT\"[\";V;\"]\":END"],
    # a second coordinate, off the 4x4 lattice corner, where the two address
    # models disagree about WHICH byte holds the pixel
    "p3.set2":     ["SCREEN 3:PSET(33,37),12",
                    "V=POINT(33,37):SCREEN 0:PRINT\"[\";V;\"]\":END"],
    # the control: the same shape in the mode whose read path was never in doubt
    "p2.s2ctl":    ["SCREEN 2:PSET(30,30),9",
                    "V=POINT(30,30):SCREEN 0:PRINT\"[\";V;\"]\":END"],
    "p2.undrawn":  ["SCREEN 2",
                    "V=POINT(30,30):SCREEN 0:PRINT\"[\";V;\"]\":END"],
}

BR = re.compile(r"\[([^\]]*)\]")

def _last_bracket(rx, text):
    """🔴 THE **LAST** `[...]`, NEVER THE FIRST (D-BRLAST, 2026-09-10).

    `rx.search` returns the FIRST bracket on screen, and that is the ECHO of the
    typed line `PRINT"[";V;"]"` -- itself a `[...]` -- so it yields `";V;"`, an
    artifact shaped like a reading. This family was protected only by accident:
    every fixture here enters a graphics mode, and the closing `SCREEN 0` clears
    the echo away. A fixture that never leaves SCREEN 0 has no defence at all,
    which is exactly how `ramfree_probe`'s rows failed -- and it looked like a
    property of those workouts rather than of the readout.

    The program's own output is always the LAST bracket printed. Returns a match
    object so `.group(1)` keeps working at the call sites.
    """
    m = None
    for m in rx.finditer(text):
        pass
    return m

ERR = re.compile(r"^\s*([A-Z][A-Za-z' ]+ error|Illegal function call|Overflow|"
                 r"Out of memory|Type mismatch|Subscript out of range)", re.M)


def face(cap):
    if cap is None:
        return "<NO CAPTURE>"
    m = _last_bracket(BR, cap)
    if m:
        return " ".join(m.group(1).split()) or "<empty>"
    e = ERR.search(cap)
    return f"<{e.group(1).strip()}>" if e else "<NO OUTPUT>"


def main() -> int:
    want = sys.argv[1:] or list(CASES)
    for label in want:
        body = ["10 ON ERROR GOTO 900"]
        body += [f"{20+10*k} {ln}" for k, ln in enumerate(CASES[label])]
        body += ['900 SCREEN 0:PRINT"[ERR";ERR;"]":END']
        row = {}
        for side, cfg in SIDES.items():
            caps = omsx_repl.run_cases(
                cfg["machine"], [("direct", list(cfg["reset"]) + body + ["RUN"])],
                batch=False, boot=cfg["boot"], step=8.0, cap_gap=10.0, timeout=300.0)
            row[side] = face(caps[0])
            print(f"  {side:7s} {label:11s} -> {row[side]!r}", flush=True)
        if "vg8020" in row and "cf3300" in row:
            agree = "refs-agree" if row["vg8020"] == row["cf3300"] else "REFS DIFFER"
            ref = row["vg8020"]
            zbm = ("zb=" + ("same" if row.get("zb") == ref else "DIFF")
                   if "zb" in row else "zb=<not run>")
        else:
            agree, zbm = "one-ref-only", "no ref this round"
        print(f"  ROW {label:11s} {agree:12s} {zbm}", flush=True)
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
