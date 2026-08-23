#!/usr/bin/env python3
"""SCAFFOLD THE BUILD SO AN UNSHIPPABLE FEATURE CAN BE **RUN**.

DEF FN is 26 B past the `$8000` ceiling, so the shipping feature set cannot be
assembled -- and an image that cannot be assembled cannot be booted, which means
the tenant's parse, the servicer's protocol and every one of the 69 subject rows
would otherwise be unmeasured Z80.

Turning off G6/G7/G8_RESIDENT (DRAW's / SPRITE's / BASE's resident halves --
switches THIS TREE ALREADY HAS, all normally 1) frees ~652 B of main page 1.
See [[a-scaffolded-build-is-a-different-machine]]:

  🔴 EVERY NUMBER TAKEN FROM A SCAFFOLDED BUILD IS A READING OF THE SCAFFOLD.
  The shipping image has never been run. Any defect that depends on the FINAL
  layout -- a `jr` reach, a page-crossing table, a hardcoded probe address --
  is UNMEASURED here, and no knife suite can be cut against it.

  ⚠️ `make unit-test` FAILS EXACTLY ONE FILE while this is on
  (test_stmt_dispatch.py, naming DRAW/SPRITE/VDP/BASE). That is the scaffold
  ANNOUNCING ITSELF in a gate that has no idea it is being used as a control.
  DO NOT "FIX" IT.

  ⚠️ AND DO NOT RUN `graphics-acceptance` / `graphics-floor-acceptance` /
  `lineerr-acceptance` HERE -- their subjects are the switched-off features.

Usage:  deffn_scaffold.py on | off | check
The swap is an ASSERTED string replacement (never a file copy: a restore that
silently no-ops leaves the tree scaffolded and the next reading is a lie), and
`check` prints `git diff --stat` so "the switches came back" is a READING.
"""
from __future__ import annotations
import subprocess
import sys

SRC = "basic/sysvars.inc"
SWITCHES = ("G6_RESIDENT", "G7_RESIDENT", "G8_RESIDENT")


def swap(frm_val: str, to_val: str) -> None:
    s = open(SRC).read()
    for name in SWITCHES:
        frm = f"{name}     equ     {frm_val}"
        to = f"{name}     equ     {to_val}"
        if s.count(frm) != 1:
            raise SystemExit(f"FAIL: {SRC} has {s.count(frm)} copies of {frm!r}")
        s = s.replace(frm, to, 1)
    open(SRC, "w").write(s)


def diffstat() -> str:
    return subprocess.run(["git", "diff", "--stat", "--", SRC],
                          capture_output=True, text=True).stdout.strip()


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode == "on":
        swap("1", "0")
        print("  SCAFFOLD ON -- G6/G7/G8_RESIDENT = 0. This is a DIFFERENT MACHINE.")
    elif mode == "off":
        swap("0", "1")
        print("  SCAFFOLD OFF -- G6/G7/G8_RESIDENT = 1 (the shipping feature set).")
    elif mode != "check":
        raise SystemExit(__doc__)
    d = diffstat()
    print(f"  {SRC}: {'CLEAN' if not d else 'MODIFIED -- ' + d}")
    for line in open(SRC):
        if any(line.startswith(n) for n in SWITCHES):
            print("   ", line.rstrip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
