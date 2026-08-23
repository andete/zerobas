#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""check_switch_builds — flip every conditional-compilation switch and ASSEMBLE.

🔴 NO GATE IN THIS TREE EVER RUNS WITH A SWITCH FLIPPED, SO THE SWITCHES DECAY.
2026-08-23 ([[a-build-switch-is-only-as-flippable-as-the-last-attempt]]):
D-DUPSPAN2 had shipped

    loc_missing     equ     g8_missing

an ALWAYS-ASSEMBLED site pointing at a symbol that exists only under
`IF G8_RESIDENT`. `G8_RESIDENT equ 0` had therefore been unbuildable since that
carve landed, and the diagnostic named a file three removes from the cause:

    ERROR: Symbol 'g8_missing' is undefined  on line 299 of file basic/missing.asm

Nothing could see it. `tools/dupspan_indep.py` decides POSITION-independence and
ROM REGION and has no notion of conditional assembly; `check_dead_code`,
`check_tenant_closure` and the eleven emulator batteries all measure the ENABLED
build. It was found by the one thing in this tree that ever flips a switch — a
scaffold (`scratchpad/deffn_scaffold.py`) — mid-slice, where a broken switch is
indistinguishable from a broken edit. That cost is paid by whoever needs the
switch NEXT, which is why this is a standing control and not a one-off sweep.

WHAT THIS ASKS, AND WHAT IT DELIBERATELY DOES NOT
  * It asks only that the image ASSEMBLES. Not that it is correct, not that it
    fits, not that it boots — a disabled feature's stub may well change the
    walls, and gating a wall here would make this control fail for reasons that
    have nothing to do with the switch.
  * It assembles the MAIN image only, and that is measured, not assumed: all
    six switches are referenced from `basic/` alone (`grep -rn` over
    `basic/`+`sub/`: 14 sites in sysvars.inc, the rest in basic/*.asm and
    kwtable.inc, ZERO under sub/). If a switch is ever read from a `sub/` file,
    this tool must grow a sub arm — SWITCH_HOMES below is the assertion that
    keeps that honest, and it FAILS if a switch turns up outside `basic/`.
  * One switch at a time. Combinations are 2^6 and the failure this exists to
    catch is per-switch.

⚠️ IT MUTATES `basic/sysvars.inc` AND RESTORES IT. The swap is an ASSERTED
string replacement (a restore that silently no-ops leaves the tree scaffolded
and every later reading is a lie), the restore runs in a `finally`, and the
final byte-identity check is an assert, not a hope. It writes only into
`build/switchcheck/`, so the shipping artefacts in `build/` are never touched
and no `rm -rf build` is needed.
"""
from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SYSVARS = ROOT / "basic/sysvars.inc"
MAIN_SRC = ROOT / "basic/main.asm"
OUT = ROOT / "build/switchcheck"
PASMO = "pasmo"

# Every conditional-compilation switch in the tree. A switch not listed here is
# a switch nothing flips — add it when you add it.
SWITCHES = ("G6_RESIDENT", "G7_RESIDENT", "G8_RESIDENT",
            "I1_RESIDENT", "TRAPS_T3", "TRAPS_T4")

# The measured claim this tool's scope rests on: no switch is read from `sub/`.
SWITCH_HOMES = ("basic",)


def scope_holds() -> bool:
    """Refuse to report a PASS whose scope has silently stopped being true."""
    bad = []
    for d in ("basic", "sub"):
        for p in sorted((ROOT / d).rglob("*")):
            if p.suffix not in (".asm", ".inc") or not p.is_file():
                continue
            txt = p.read_text()
            for name in SWITCHES:
                if re.search(rf"\b{name}\b", txt) and d not in SWITCH_HOMES:
                    bad.append(f"{p.relative_to(ROOT)} reads {name}")
    if bad:
        print("SCOPE BROKEN — a switch is read outside "
              f"{'/'.join(SWITCH_HOMES)}, so a main-only assemble no longer "
              "covers it:")
        for b in bad:
            print(f"  {b}")
        return False
    return True


def swap(name: str, frm: str, to: str) -> None:
    s = SYSVARS.read_text()
    old = f"{name:<15} equ     {frm}"
    new = f"{name:<15} equ     {to}"
    if s.count(old) != 1:
        raise SystemExit(
            f"REFUSING: basic/sysvars.inc has {s.count(old)} copies of "
            f"{old!r} — the switch is not written the way this tool expects, "
            f"and a swap that matches nothing is a check that measures nothing")
    SYSVARS.write_text(s.replace(old, new, 1))


def assemble(tag: str) -> tuple[int, str]:
    OUT.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [PASMO, "--bin", str(MAIN_SRC), str(OUT / f"{tag}.rom"),
         str(OUT / f"{tag}.sym")],
        cwd=ROOT, capture_output=True, text=True)
    if r.returncode == 0:
        return 0, ""
    txt = (r.stdout + r.stderr).strip().splitlines()
    err = next((l for l in txt if "ERROR" in l.upper()),
               txt[-1] if txt else "<no diagnostic>")
    return r.returncode, err.strip()


def main() -> int:
    if not scope_holds():
        return 2
    orig = SYSVARS.read_text()
    stat = SYSVARS.stat()          # see the mtime note in the `finally` below
    results = []
    try:
        rc, err = assemble("baseline")
        if rc:
            print(f"REFUSING: the UNMODIFIED tree does not assemble — "
                  f"{err}\nNothing below would mean anything.")
            return 2
        print("baseline (all switches on): assembles\n")
        for name in SWITCHES:
            SYSVARS.write_text(orig)
            swap(name, "1", "0")
            rc, err = assemble(name)
            results.append((name, rc, err))
            print(f"{'PASS' if rc == 0 else 'FAIL'}  {name} equ 0"
                  + (f"\n        {err}" if rc else ""), flush=True)
    finally:
        SYSVARS.write_text(orig)
        assert SYSVARS.read_text() == orig, "basic/sysvars.inc was not restored!"
        # 🔴 AND PUT THE MTIME BACK, WHICH IS THE OPPOSITE OF THE KNIFE RULE AND
        # DELIBERATELY SO. A knife must NEVER preserve mtime (make then rebuilds
        # nothing and the next gate scores the previous knife's ROM). This is not
        # a knife: the content is restored BYTE-IDENTICAL -- asserted one line up
        # -- so there is nothing for make to rebuild, and leaving the mtime bumped
        # makes `make -q build/zerobas-main-eu.rom` report the shipping ROM STALE.
        # That is not cosmetic: probes/lib/latch_check.py's preflight REFUSES on a
        # stale ROM ("APPARATUS FAILURE -- NOTHING WAS MEASURED"), so running this
        # gate poisoned every emulator gate after it until someone rebuilt. Caught
        # 2026-08-23 by `latch-check` going rc=2 in the battery immediately after
        # this target's first green run [[apparatus-is-part-of-the-measurement]].
        os.utime(SYSVARS, (stat.st_atime, stat.st_mtime))

    bad = [n for n, rc, _ in results if rc]
    print(f"\nSWITCHES: {len(results) - len(bad)} of {len(results)} assemble "
          f"with the switch off")
    if bad:
        print("FAIL: " + ", ".join(bad))
        print("A switch that cannot be flipped is a switch that is not there. "
              "The usual cause is an ALWAYS-ASSEMBLED reference to a symbol "
              "that only exists under the switch (`X equ y`, a `jp`, a table "
              "entry); the fix is an ELSE arm, which costs the shipping build "
              "nothing because it is not assembled there.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
