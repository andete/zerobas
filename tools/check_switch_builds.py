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

# Every conditional-compilation switch in the tree, with the trees it is READ
# from. A switch not listed here is a switch nothing flips — add it when you add
# it. The value is what gets ASSEMBLED for that switch, so the scope claim is
# per-switch rather than global.
#
# 🔴 IT USED TO BE A GLOBAL CLAIM -- "no switch is read from `sub/`" -- and that
# kept CLEARPOOL OUT of this gate entirely: it is read from `sub/arrays.asm` and
# `sub/strheap.asm`, so adding it tripped `scope_holds()` and the ELSE arm went
# unassembled instead. A scope that excludes the switch that needs covering most
# is a scope that has chosen its own denominator.
SWITCHES = {
    "G6_RESIDENT": ("basic",),
    "G7_RESIDENT": ("basic",),
    "G8_RESIDENT": ("basic",),
    "I1_RESIDENT": ("basic",),
    "TRAPS_T3": ("basic",),
    "TRAPS_T4": ("basic",),
    "CLEARPOOL": ("basic", "sub"),
}

SRC = {"basic": (ROOT / "basic/main.asm", []),
       "sub": (ROOT / "sub/sub.asm", ["-I", "sub"])}

# 🔴 ASSEMBLING IS THE EASY HALF. The failure CLEARPOOL was filed for is an
# off-by-one that BUILDS: `fperr_to_err` is a DENSE table whose next free index
# moves with the switch, so a wrong `FPERR_MISSOP` reads a NEIGHBOURING byte and
# raises some other error, silently. A gate that only asks "does it build" would
# report PASS on exactly that. So a switch may also declare a POST-CHECK read
# out of the assembled image.
POSTCHECK = {
    # switch -> (symbol naming the index, table symbol, expected byte)
    "CLEARPOOL": ("FPERR_MISSOP", "fperr_to_err", 24),
}


def scope_holds() -> bool:
    """Refuse to report a PASS whose scope has silently stopped being true.

    Per switch now: a switch read from a tree it does not DECLARE is a switch
    whose flip this tool does not actually cover."""
    bad = []
    for d in ("basic", "sub"):
        for p in sorted((ROOT / d).rglob("*")):
            if p.suffix not in (".asm", ".inc") or not p.is_file():
                continue
            txt = p.read_text()
            for name, trees in SWITCHES.items():
                if re.search(rf"\b{name}\b", txt) and d not in trees:
                    bad.append(f"{p.relative_to(ROOT)} reads {name}, which "
                               f"declares only {'/'.join(trees)}")
    if bad:
        print("SCOPE BROKEN — a switch is read from a tree it does not declare, "
              "so flipping it is not actually covered:")
        for b in bad:
            print(f"  {b}")
        return False
    return True


def _sym(tag: str, tree: str, name: str):
    try:
        txt = (OUT / f"{tag}-{tree}.sym").read_text()
    except OSError:
        return None
    m = re.search(rf"^{re.escape(name)}\s+EQU\s+([0-9A-Fa-f]+)H", txt, re.M)
    return int(m.group(1), 16) if m else None


def postcheck(name: str, tag: str) -> tuple[bool, str]:
    """Read the switch's declared table byte back out of the assembled ROM."""
    spec = POSTCHECK.get(name)
    if not spec:
        return True, ""
    idx_sym, tbl_sym, want = spec
    idx = _sym(tag, "basic", idx_sym)
    tbl = _sym(tag, "basic", tbl_sym)
    org = _sym(tag, "basic", "BASIC_ORG")
    if None in (idx, tbl, org):
        return False, (f"postcheck could not resolve {idx_sym}/{tbl_sym}/"
                       f"BASIC_ORG in the sym file -- an offset from a DEFAULT "
                       f"is not a reading")
    rom = (OUT / f"{tag}-basic.rom").read_bytes()
    off = tbl - org + (idx - 1)                 # FPERR codes are 1-based
    if not (0 <= off < len(rom)):
        return False, f"{tbl_sym}[{idx_sym}={idx}] is outside the image"
    got = rom[off]
    if got != want:
        return False, (f"{tbl_sym}[{idx_sym}={idx}] is {got}, want {want} -- the "
                       f"equate and the dense table have DRIFTED APART, and a "
                       f"raise there would report ERR {got}")
    return True, f"{tbl_sym}[{idx_sym}={idx}] = {got}"


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


def assemble(tag: str, trees=("basic",)) -> tuple[int, str]:
    """Assemble every tree the switch declares. A `sub/`-read switch that only
    ever built `basic/` was a PASS about the half that could not break."""
    OUT.mkdir(parents=True, exist_ok=True)
    for tree in trees:
        src, extra = SRC[tree]
        r = subprocess.run(
            [PASMO, *extra, "--bin", str(src), str(OUT / f"{tag}-{tree}.rom"),
             str(OUT / f"{tag}-{tree}.sym")],
            cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            txt = (r.stdout + r.stderr).strip().splitlines()
            err = next((l for l in txt if "ERROR" in l.upper()),
                       txt[-1] if txt else "<no diagnostic>")
            return r.returncode, f"[{tree}] {err.strip()}"
    return 0, ""


def main() -> int:
    if not scope_holds():
        return 2
    orig = SYSVARS.read_text()
    stat = SYSVARS.stat()          # see the mtime note in the `finally` below
    results = []
    try:
        rc, err = assemble("baseline", ("basic", "sub"))
        if rc:
            print(f"REFUSING: the UNMODIFIED tree does not assemble — "
                  f"{err}\nNothing below would mean anything.")
            return 2
        for nm in POSTCHECK:
            ok, note = postcheck(nm, "baseline")
            if not ok:
                print(f"REFUSING: the UNMODIFIED tree fails {nm}'s postcheck — "
                      f"{note}\nNothing below would mean anything.")
                return 2
        print("baseline (all switches on): assembles"
              + (f", postchecks OK ({len(POSTCHECK)})" if POSTCHECK else "") + "\n")
        for name, trees in SWITCHES.items():
            SYSVARS.write_text(orig)
            swap(name, "1", "0")
            rc, err = assemble(name, trees)
            if rc == 0:
                ok, note = postcheck(name, name)
                if not ok:
                    rc, err = 1, note
                elif note:
                    err = note          # carried into the PASS line, see below
            results.append((name, rc, err))
            print(f"{'PASS' if rc == 0 else 'FAIL'}  {name} equ 0 "
                  f"({'+'.join(trees)})"
                  + (f"  [{err}]" if rc == 0 and err else "")
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
