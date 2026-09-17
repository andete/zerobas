#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DSPFNK -- does C-BIOS actually PAINT the function-key line on our target?

This one fact decides whether `KEY`'s ~10 B fix is a fix or a regression
(TODO.md's KEY item; D-KEYON pinned the rule). `key_on` already calls the BIOS
`DSPFNK` and `key_off` calls `ERAFNK`, so the feature is WIRED -- what did not
move is `CON_LASTROW`, a compile-time 23. If DSPFNK paints, moving that bound to
22 under `KEY ON` matches the reference and nothing is lost. If it paints
NOTHING, the same change reserves a row for a line that is never drawn: the
measured observable would agree while the SCREEN got worse, one usable row traded
for nothing [[rows-going-green-is-not-the-fix]].

⚠️ READ THE NAME TABLE, NOT A GUESS AT IT: `BASE(0)` gives the SCREEN 0 name
table and a row is **40 bytes**, so row 23 starts at +920. A fixed absolute
offset is the mistake D-KWOSK already made here.
🔴 THE READING IS A COUNT AND A POSITION, NOT A CHARACTER. Printing the row's
bytes as text makes blanks invisible and the two machines' widths differ
(LINLEN 37 vs 39), so each row reports how many cells are NON-BLANK and where the
first one is -- a shape that cannot agree by both sides being empty.
⚠️ EVERY CASE HAS ITS `KEY OFF` TWIN, because the question is what `KEY ON`
CHANGES.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = ("C-BIOS_MSX1_EU_REPACK_DISK", "Philips_VG_8020")


def lines(seq) -> list[str]:
    """(label|None, text) with `@name` resolved to that line's number; refuses an
    unresolved one. A label that resolves to the WRONG line is still possible --
    see playxrec_probe.py -- so the loops below spin on their OWN line."""
    nums = {lab: 10 * (i + 1) for i, (lab, _) in enumerate(seq) if lab}
    out = []
    for _, text in seq:
        for lab, n in nums.items():
            text = text.replace("@" + lab, str(n))
        if "@" in text:
            sys.exit(f"REFUSE: unresolved label in {text!r}")
        assert len(text) <= 34, (len(text), text)
        out.append(text)
    return out


def scan(keystate: str, *extra: str):
    """`keystate`, then count the non-blank cells of name-table row 23."""
    body = [(None, "ON ERROR GOTO @err")]
    body += [(None, e) for e in extra]
    body += [(None, keystate),
             (None, "B=BASE(0)+920"),
             (None, "N=0:F=-1"),
             ("lp", "FOR I=0 TO 39"),
             (None, "V=VPEEK(B+I)"),
             (None, "IF V=32 OR V=0 THEN @nx"),
             (None, "N=N+1:IF F<0 THEN F=I"),
             ("nx", "NEXT"),
             (None, 'CLS:PRINT"<K";N;F;">":END'),
             ("err", 'PRINT"<E";ERR;">":END')]
    return lines(body)


CASES = [
    ("on_default",  scan("KEY ON")),
    ("off_default", scan("KEY OFF")),
    # with a macro ASSIGNED, so a painted line has something distinctive in it
    ("on_assigned",  scan("KEY ON", 'KEY 1,"ZQZQZQ"')),
    ("off_assigned", scan("KEY OFF", 'KEY 1,"ZQZQZQ"')),
    # the control: row 22 is ordinary text space and must look the same on both
    # sides once cleared -- if THIS disagrees, the instrument is wrong, not KEY
    ("ctl_row22",   lines([(None, "ON ERROR GOTO @err"), (None, "CLS"),
                           (None, "B=BASE(0)+880"), (None, "N=0:F=-1"),
                           ("lp", "FOR I=0 TO 39"), (None, "V=VPEEK(B+I)"),
                           (None, "IF V=32 OR V=0 THEN @nx"),
                           (None, "N=N+1:IF F<0 THEN F=I"), ("nx", "NEXT"),
                           (None, 'PRINT"<K";N;F;">":END'),
                           ("err", 'PRINT"<E";ERR;">":END')])),
]


def main() -> int:
    for mach in MACHINES:
        print("===", mach, flush=True)
        specs = [("stored", ls) for _, ls in CASES]
        try:
            raws = omsx_repl.run_cases(mach, specs, batch=False, cap_gap=10.0)
        except Exception as exc:                       # noqa: BLE001
            print(f"  🔴 APPARATUS FAILURE on {mach}: "
                  f"{str(exc).splitlines()[0][:150]}", flush=True)
            continue
        for (name, _), raw in zip(CASES, raws):
            txt = " ".join("".join(raw or "").split())
            i = txt.rfind("<K")
            j = txt.find(">", i + 1)
            cell = txt[i:j + 1] if i >= 0 and j > i else (
                txt[txt.rfind("<E"):txt.rfind("<E") + 9]
                if "<E" in txt else "<no reading>")
            print(f"  {name:13} {cell!r}   (non-blank cells, first offset)",
                  flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
