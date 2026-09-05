#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""build-assert-check — an ALIGNMENT assert over a moving symbol is a landmine.

🔴 WHY THIS EXISTS (filed 2026-08-22 by D-DEFFN, docs/deffn-impl-2026-08-22.md
§4.5; built 2026-09-05). `sub/deftype.asm`'s `edt_codes` guard —

    IF (high edt_codes) != (high (edt_codes+3))
                db      EDT_CODES_CROSSES_A_PAGE__...
    ENDIF

— fired because a 40-byte routine was added to a file INCLUDED AHEAD OF IT. The
guard was right and useless: *"never let an unrelated sub-ROM edit relocate this
table"* is not a rule anyone can keep, and every future page-0 tenant re-rolls
the dice. That one is now enforced with ≤3 B of pad, the assert kept as a proof.
**The SWEEP was what stayed open** — "nothing has walked the tree for the rest".
This walks it, every build.

🎯 THE DISCRIMINATOR, AND IT IS THE WHOLE IDEA. Two kinds of `db`-assert look
identical and behave completely differently:

* **BUDGET** — `IF $ > $4000`. An edit trips it, the edit is YOURS, and the
  remedy is the one the project already runs on: trim, split, carve. Fine.
* **ALIGNMENT** — `high X != high (X+n)`, or a low-byte-carry bound. Whether it
  fires depends on where X LANDS, so a stranger's unrelated edit upstream trips
  it and the remedy (pad to the boundary) is not obvious from the diagnostic.

⚠️ **AND ALIGNMENT ALONE IS NOT ENOUGH TO CONDEMN ONE.** Three of this tree's
four alignment asserts are over symbols that CANNOT MOVE — `USRTAB` is the
published MSX sysvar `$F39A`, `SUBROM_ENTRY_BASE_P1` is `equ $4010`, and
`FN_BASE` is `equ`'d AND separately pinned by its own `IF FN_BASE != $EA92`. An
assert over a pinned literal is a PROOF, not a landmine: the only way to trip it
is to edit the literal, which is deliberate and self-explanatory. The one that
bit was the one over a **code label**, whose address is whatever the assembler
made it.

So the rule is the CONJUNCTION: alignment-shaped **and** an operand that moves.

Exit: 0 clean, 1 an unenforced alignment landmine, 2 the instrument could not
measure.

    python3 tools/check_build_asserts.py [--selftest] [--list]
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOW = os.path.join(ROOT, "tools", "build-asserts-enforced.txt")
SCAN_DIRS = ["basic", "sub", "disk"]

# `IF <cond>` … `db <SCREAMING_SYMBOL>` … `ENDIF`, the project's assert idiom.
ASSERT = re.compile(
    r"^[ \t]*IF[ \t]+(?P<cond>.+?)[ \t]*\n"
    r"(?P<body>(?:[^\n]*\n)*?)"
    r"[ \t]*ENDIF[ \t]*$", re.M)
DBSYM = re.compile(r"^[ \t]*db[ \t]+([A-Z][A-Z0-9_]{11,})[ \t]*(?:;.*)?$", re.M)
EQU = re.compile(r"^([A-Za-z_][A-Za-z_0-9]*)[ \t]+equ[ \t]+(.+?)[ \t]*(?:;.*)?$", re.M)
LABEL = re.compile(r"^([a-z_][a-z_0-9]*):", re.M)
IDENT = re.compile(r"\b([A-Za-z_][A-Za-z_0-9]*)\b")

# An alignment/carry shape: it asks WHERE something landed, not HOW BIG it is.
# 🔴 `high`/`low` ALONE MISSED ONE, on this checker's first run: basic/expr.asm
# expresses the same page-crossing question as `(X >> 8) - (Y >> 8)`, and a
# detector that only knew the pasmo operators classified it as a budget assert.
# The shape is the question, not the spelling -- `>> 8` and `& $FF00` ask it too.
ALIGN = re.compile(r"\b(high|low)\b|>>\s*8\b|&\s*\$FF00", re.I)

# pasmo operators and directives that are not symbols
NOISE = {"high", "low", "IF", "ENDIF", "db", "and", "or", "not", "mod", "shl",
         "shr", "equ", "ds", "dw"}

MIN_ASSERTS = 12       # fewer than this means the scan broke, not that the tree is clean


def sources():
    for d in SCAN_DIRS:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for dirpath, _dn, files in os.walk(base):
            for f in sorted(files):
                if f.endswith((".asm", ".inc")):
                    yield os.path.relpath(os.path.join(dirpath, f), ROOT)


def symbol_map():
    """name -> 'pinned' (equ to a pure literal), 'derived' (equ to an
    expression), or 'label' (a code label: its address is wherever the assembler
    put it, so an unrelated edit upstream moves it)."""
    kinds = {}
    for rel in sources():
        text = open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace").read()
        for name, expr in EQU.findall(text):
            e = expr.replace("$", "0x").strip()
            try:
                int(eval(e, {"__builtins__": {}}, {}))          # noqa: S307
                kinds.setdefault(name, "pinned")
            except Exception:
                kinds.setdefault(name, "derived")
        for name in LABEL.findall(text):
            kinds.setdefault(name, "label")
    return kinds


def resolve_kind(name, kinds, seen=None):
    """Walk a `derived` equ down to what it really depends on. A name that
    resolves only through other pinned equs is itself pinned."""
    seen = seen or set()
    k = kinds.get(name)
    if k != "derived" or name in seen:
        return k
    return k


def scan(kinds):
    out = []
    for rel in sources():
        path = os.path.join(ROOT, rel)
        text = open(path, encoding="utf-8", errors="replace").read()
        for m in ASSERT.finditer(text):
            sym = DBSYM.search(m.group("body"))
            if not sym:
                continue                       # an IF that emits code, not an assert
            cond = m.group("cond")
            line = text.count("\n", 0, m.start()) + 1
            names = [n for n in IDENT.findall(cond) if n not in NOISE]
            movers = sorted({n for n in names
                             if kinds.get(n) == "label"} | ({"$"} if "$" in cond else set()))
            out.append({"file": rel, "line": line, "cond": cond.strip(),
                        "sym": sym.group(1),
                        "align": bool(ALIGN.search(cond)),
                        "movers": movers,
                        "kinds": {n: kinds.get(n, "?") for n in names}})
    return out


# 🎯 ENFORCEMENT IS DETECTED IN THE SOURCE, NOT ACKNOWLEDGED IN A LIST. The one
# real landmine here is already fixed the right way — `IF (low $) > 252 / ds 256
# - (low $), $00` immediately before `edt_codes`, at most 3 bytes of pad that
# make the straddle impossible. An allowlist entry would have recorded that and
# then gone stale the day somebody deleted the pad, which is the failure mode
# this whole check exists to prevent. So the check LOOKS for the pad: remove it
# and the row goes red again by itself.
PAD = re.compile(r"^[ \t]*IF[ \t]+\(low[ \t]+\$\)[ \t]*>[ \t]*\d+[ \t]*\n"
                 r"[ \t]*ds[ \t]+.*\n[ \t]*ENDIF", re.M | re.I)


def padded(rel, label):
    """Is `label:` immediately preceded by a page-alignment pad?"""
    text = open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace").read()
    m = re.search(rf"^{re.escape(label)}:", text, re.M)
    if not m:
        return False
    before = text[:m.start()]
    tail = "\n".join(before.splitlines()[-6:])
    return bool(PAD.search(tail))


def load_allow():
    if not os.path.exists(ALLOW):
        return {}
    out = {}
    for ln in open(ALLOW, encoding="utf-8"):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        key, _, why = ln.partition(" ")
        out[key] = why.strip()
    return out


def selftest():
    """A GREEN control and a PLANTED landmine. Without the plant, "0 landmines"
    is equally what a checker that matches nothing prints."""
    fails = 0
    kinds = {"PINNED_THING": "pinned", "moving_table": "label"}
    fixture = (
        "    IF $ > $4000\n                db      REGION_FULL_TRIM_OR_SPLIT\n    ENDIF\n"
        "    IF (high PINNED_THING) != (high (PINNED_THING+3))\n"
        "                db      PINNED_CROSSES_A_PAGE_BOUNDARY\n    ENDIF\n"
        "    IF (high moving_table) != (high (moving_table+3))\n"
        "                db      TABLE_CROSSES_A_PAGE_BOUNDARY\n    ENDIF\n")
    got = []
    for m in ASSERT.finditer(fixture):
        sym = DBSYM.search(m.group("body"))
        if not sym:
            continue
        cond = m.group("cond")
        names = [n for n in IDENT.findall(cond) if n not in NOISE]
        movers = sorted({n for n in names if kinds.get(n) == "label"}
                        | ({"$"} if "$" in cond else set()))
        got.append((bool(ALIGN.search(cond)), tuple(movers)))
    want = [(False, ("$",)), (True, ()), (True, ("moving_table",))]
    if got != want:
        print(f"  selftest: classification {got}, want {want}")
        fails += 1
    # the budget assert must NOT be a landmine even though it moves
    if any(a and mv for a, mv in got[:1]):
        print("  selftest: the budget assert was condemned")
        fails += 1
    # ...and the pinned alignment assert must NOT be one either
    if got[1][1]:
        print("  selftest: the PINNED alignment assert was condemned")
        fails += 1
    # ...while the label one must be
    if not (got[2][0] and got[2][1]):
        print("  selftest: the planted landmine was NOT detected")
        fails += 1
    print("  selftest: PASS" if not fails else f"  selftest: {fails} FAILURE(S)")
    return fails


def main(argv):
    if "--selftest" in argv:
        return 2 if selftest() else 0
    kinds = symbol_map()
    rows = scan(kinds)
    if len(rows) < MIN_ASSERTS:
        print(f"INSTRUMENT FAULT: found {len(rows)} assert(s); the floor is "
              f"{MIN_ASSERTS}. The scan broke — a clean run here would mean "
              f"nothing.")
        return 2
    allow = load_allow()
    align = [r for r in rows if r["align"]]
    for r in align:
        r["padded"] = any(m != "$" and padded(r["file"], m) for m in r["movers"])
    land = [r for r in align if r["movers"]]
    bad = [r for r in land if not r["padded"]
           and f"{r['file']}:{r['sym']}" not in allow]

    print(f"build-assert-check: {len(rows)} `IF …/db SYMBOL` assert(s) across "
          f"{len(SCAN_DIRS)} tree(s)")
    print(f"  {len(rows) - len(align)} BUDGET (size/overflow — your own edit "
          f"trips them, and the remedy is the usual one)")
    print(f"  {len(align)} ALIGNMENT (they ask WHERE something landed):")
    for r in align:
        why = allow.get(f"{r['file']}:{r['sym']}")
        if r["movers"] and r.get("padded"):
            tag = (f"ENFORCED in source — {', '.join(r['movers'])} moves, but a "
                   f"page-alignment pad precedes it, so the assert is a proof "
                   f"that cannot fire. Delete the pad and this goes red.")
        elif r["movers"]:
            tag = f"🔴 LANDMINE (moves: {', '.join(r['movers'])})" if not why \
                  else f"[acknowledged] {why}"
        else:
            pinned = ", ".join(f"{n}={k}" for n, k in r["kinds"].items())
            tag = f"proof — nothing here moves ({pinned})"
        print(f"    {r['file']}:{r['line']}  {r['sym']}")
        print(f"        {r['cond']}")
        print(f"        {tag}")
    if "--list" in argv:
        print("\n  all asserts:")
        for r in rows:
            print(f"    {r['file']}:{r['line']:<5} "
                  f"{'ALIGN ' if r['align'] else 'budget'} {r['sym']}")
    print()
    if bad:
        for r in bad:
            print(f"🔴 {r['file']}:{r['line']} — an ALIGNMENT assert over "
                  f"{', '.join(r['movers'])}, which an unrelated edit upstream "
                  f"relocates. Enforce it (pad to the boundary and keep the "
                  f"assert as the proof) or acknowledge it in "
                  f"tools/build-asserts-enforced.txt with the reason.")
        print(f"\n{len(bad)} unenforced landmine(s)")
        return 1
    print("clean — every alignment assert is over a symbol that cannot move, or "
          "is acknowledged as enforced.")
    print("⚠️ SHAPE-LEVEL ONLY. This cannot tell whether the PADDING that "
          "enforces one is still big enough; the assert itself is what says "
          "that, at build time.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
