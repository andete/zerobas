#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-KEYON -- pin what `KEY ON` does to the text window, before writing the fix.

D-AKCM measured the defect: with `KEY ON`, `LOCATE 0,23` then `CSRLIN` reads
**22 on the VG-8020 and 23 here**, while `KEY OFF` reads 23 on both. So the
reference keeps the bottom row for the function-key display and we do not.
What that measurement does NOT say is the SHAPE of the reference's rule, and
three different implementations fit it:

  * `LOCATE` CLAMPS a too-large row to the window bottom;
  * `LOCATE` RAISES on a row outside the window (and the 22 came from somewhere
    else entirely);
  * the window bottom is 22 for LOCATE but 23 for SCROLLING, or vice versa.

⚠️ CRTCNT ($F3B1) IS ALREADY RULED OUT as the mechanism: it reads 24 on both
machines in BOTH states. Whatever the reference moves, it is not that cell.
🔴 EVERY ROW HAS A `KEY OFF` TWIN, because the question is always "what does KEY
ON change", never "what does this machine do".
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = ("C-BIOS_MSX1_EU_REPACK_DISK", "Philips_VG_8020")


def prog(*body: str) -> list[str]:
    """The trap line is derived from the FINAL list -- see akcm_probe.py for the
    off-by-one that made eleven cells read `<no reading>`."""
    lines = ["ON ERROR GOTO @T"] + list(body) + ["END", 'PRINT"<E";ERR;">":END']
    lines[0] = "ON ERROR GOTO %d" % (10 * len(lines))
    for l in lines:
        assert len(l) <= 34, (len(l), l)
        assert "@" not in l, l
    return lines


def pair(setup: str, *body: str):
    """The same body under KEY ON and KEY OFF."""
    return (prog("KEY ON", setup, *body), prog("KEY OFF", setup, *body))


CASES = []
for tag, setup, body in [
    # where does LOCATE actually land?
    ("r22", "LOCATE 0,22", 'A=CSRLIN:CLS:PRINT"<K";A;">"'),
    ("r23", "LOCATE 0,23", 'A=CSRLIN:CLS:PRINT"<K";A;">"'),
    ("r24", "LOCATE 0,24", 'A=CSRLIN:CLS:PRINT"<K";A;">"'),
    # ...and does the CURSOR COLUMN survive a clamped row?
    ("c23", "LOCATE 5,23", 'A=POS(0):CLS:PRINT"<K";A;">"'),
]:
    on, off = pair(setup, body)
    CASES.append((tag + "_on", on))
    CASES.append((tag + "_off", off))
# does SCROLLING see the same bottom? print 30 lines, then ask where we are
CASES.append(("scr_on", prog("KEY ON", "FOR I=1 TO 30", 'PRINT"x"', "NEXT",
                             'A=CSRLIN:CLS:PRINT"<K";A;">"')))
CASES.append(("scr_off", prog("KEY OFF", "FOR I=1 TO 30", 'PRINT"x"', "NEXT",
                              'A=CSRLIN:CLS:PRINT"<K";A;">"')))


def main() -> int:
    for mach in MACHINES:
        print("===", mach, flush=True)
        specs = [("stored", lines) for _, lines in CASES]
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
                txt[txt.rfind("<E"):txt.rfind("<E") + 8]
                if "<E" in txt else "<no reading>")
            print(f"  {name:9} {cell!r}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
