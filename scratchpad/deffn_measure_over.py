#!/usr/bin/env python3
"""READ THE WALL ON AN IMAGE THAT DOES NOT FIT (D-DEFFNEV, 2026-08-22).

The `$8000` ceiling assert in basic/main.asm is an UNDEFINED SYMBOL, which is
what makes it stop the build -- and pasmo then writes no `.sym` at all, so the
overrun cannot be read. That is the right behaviour for a gate and the wrong
behaviour for an instrument: "how far past the ceiling is it?" is the single
number the DEF FN funding arithmetic turns on.

So: neutralise ONLY that assert, assemble, read __MEAS_PAGE1_END, and put the
source back byte-for-byte.

⚠️ THREE THINGS THIS DOES DELIBERATELY, because each is how the same trick goes
wrong:
  * the WRAP assert (`IF $ < BASIC_ORG`, the >32 KB catastrophic case) stays
    ARMED -- neutralising both would let a wrapped image read as a small one;
  * the restore is a string replacement asserted to match, not a copy of a
    saved file, so a failed restore RAISES rather than silently leaving the
    tree defused (`shutil.copy2` is the tree's own named trap here);
  * it prints `git diff --stat basic/main.asm` afterwards, so "the source came
    back" is a READING and not an intention.

🔴 A NUMBER FROM THIS IS A STATEMENT ABOUT THE IMAGE'S SIZE AND NOTHING ELSE.
The image it measures cannot be built, therefore cannot be run.
"""
from __future__ import annotations
import re
import subprocess
import sys

MAIN = "basic/main.asm"
ARMED = """    IF $ > $8000
                db      BASIC_IMAGE_OVERRAN_8000_CEILING__TRIM_IT_OR_EVICT_TO_SUBROM
    ENDIF"""
DEFUSED = """    IF $ > $8000
                ; __MEASURE_OVERRUN__ temporarily neutralised to READ the wall
    ENDIF"""


def swap(frm: str, to: str) -> None:
    s = open(MAIN).read()
    if frm not in s:
        raise SystemExit(f"FAIL: {MAIN} does not contain the expected block:\n{frm}")
    open(MAIN, "w").write(s.replace(frm, to, 1))


def main() -> int:
    swap(ARMED, DEFUSED)
    try:
        subprocess.run(["rm", "-rf", "build"], check=True)
        subprocess.run(["make", "build/basic-reloc.sym"],
                       capture_output=True, text=True)
    finally:
        swap(DEFUSED, ARMED)                 # raises if it cannot be undone

    diff = subprocess.run(["git", "diff", "--stat", "--", MAIN],
                          capture_output=True, text=True).stdout.strip()
    print(f"  source restored: {'CLEAN' if not diff else 'DIRTY -- ' + diff}")

    try:
        sym = open("build/basic-reloc.sym").read()
    except FileNotFoundError:
        print("  NO SYM -- the build failed for a reason other than the ceiling")
        return 1
    out = {}
    for name in ("__MEAS_LOW_END", "__MEAS_PAGE1_END"):
        m = re.search(rf"^{name}\s+EQU\s+([0-9A-Fa-f]+)H", sym, re.M)
        if m:
            out[name] = int(m.group(1), 16)
    if "__MEAS_PAGE1_END" not in out:
        print("  the measurement labels are not in the sym")
        return 1
    p1, low = out["__MEAS_PAGE1_END"], out.get("__MEAS_LOW_END", 0)
    over = p1 - 0x8000
    lowfree = 0x4000 - low
    print(f"  __MEAS_PAGE1_END = ${p1:04X}   "
          f"{'%d B PAST the $8000 ceiling' % over if over > 0 else '%d B free' % -over}")
    print(f"  __MEAS_LOW_END   = ${low:04X}   {lowfree} B free in the low region")
    if over > 0:
        print(f"  GAP = {over} - {lowfree} = {over - lowfree} B "
              f"(the two regions are co-mapped, so low bytes spend on page-1 pressure)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
