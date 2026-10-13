#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RAMSHIFT: move one block of zerobas's private workspace by a fixed delta,
and PROVE that exactly that block moved.

    python3 tools/ws_shift.py LO HI DELTA NEWTXTMAX [--apply]

Every `NAME equ $XXXX` whose LITERAL value lies in [LO, HI), in the basic
component's sources (basic/, sub/) and the disk component's (disk/), gets
+DELTA; TXTMAX (a NOT-A-CELL constant: the text ceiling, the workspace floor)
is set to NEWTXTMAX. Generated files (*basic-resident-abi.inc) are skipped:
the build regenerates them.

🔴 THE REWRITE IS NOT THE CLAIM; THE RESOLVED MAP IS. tools/ram_map.py resolves
every name of both components BEFORE and AFTER (source only, no .sym -- a stale
build must not vouch for it), and the run REFUSES -- restoring every file --
unless:
  * every name that resolved into [LO, HI) before resolves to old + DELTA;
  * every name whose expression reaches TXTMAX (transitively) moved by exactly
    NEWTXTMAX - old TXTMAX (DSK_ENGTAB sits just under the ceiling);
  * every other name is unchanged;
  * no name lands in [LO, NEWTXTMAX) after (that span becomes program RAM),
    except NOT-A-CELL constants;
  * the destination [LO + DELTA, HI + DELTA) held no cell of either component
    before (the block moves into a HOLE, not onto a tenant).
A delta that is a multiple of $100 keeps every low byte, so page-relative idioms
(`ld h,high X`, `cp low X`) cannot break; anything else is refused.

Without --apply it rewrites, verifies, prints the verdict and RESTORES.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
os.chdir(REPO)
import ram_map                                      # noqa: E402

EQU_LIT = re.compile(r"^(\s*([A-Za-z_][A-Za-z0-9_]*)\s+equ\s+)\$([0-9A-Fa-f]{4})\b(.*)$",
                     re.IGNORECASE)


def resolve_all():
    return {c: ram_map.Map(c, 0, 0x10000, use_sym=False) for c in ("basic", "disk")}


def reaches(m, name, target, seen=None):
    """Does NAME's expression reach TARGET through other names?"""
    seen = seen or set()
    if name in seen:
        return False
    seen.add(name)
    expr = m.raw.get(name, ("",))[0]
    for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr):
        if tok == target or (tok in m.raw and reaches(m, tok, target, seen)):
            return True
    return False


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 4:
        sys.exit(__doc__)
    lo, hi, delta, newtop = (int(a.replace("$", ""), 16) for a in args)
    if delta % 0x100:
        sys.exit("REFUSED: a delta that is not a multiple of $100 changes low bytes")
    before = resolve_all()
    oldtop = before["basic"].vals["TXTMAX"]

    # the destination must be a hole in BOTH maps
    for c, m in before.items():
        clash = [n for n, v in m.vals.items()
                 if lo + delta <= v < hi + delta and not m.not_a_cell(n)]
        if clash:
            sys.exit(f"REFUSED: the destination holds {c} cells: {sorted(clash)[:8]}")

    files = sorted(set(before["basic"].files) | set(before["disk"].files))
    files = [f for f in files if not f.endswith("basic-resident-abi.inc")]
    saved, edits = {}, []
    for f in files:
        text = open(f).read()
        out, changed = [], False
        for i, ln in enumerate(text.split("\n"), 1):
            mt = EQU_LIT.match(ln)
            if mt:
                name, val = mt.group(2), int(mt.group(3), 16)
                if name == "TXTMAX":
                    ln = f"{mt.group(1)}${newtop:04X}{mt.group(4)}"
                    edits.append((f, i, name, val, newtop))
                    changed = True
                elif lo <= val < hi and "NOT-A-CELL" not in ln:
                    ln = f"{mt.group(1)}${val + delta:04X}{mt.group(4)}"
                    edits.append((f, i, name, val, val + delta))
                    changed = True
            out.append(ln)
        if changed:
            saved[f] = text
            open(f, "w").write("\n".join(out))
    ok = True
    try:
        after = resolve_all()
        bad, mirrors = [], 0
        for c in ("basic", "disk"):
            b, a = before[c], after[c]
            for n, v in b.vals.items():
                # a GENERATED mirror (disk/basic-resident-abi.inc) is not rewritten
                # here -- the build regenerates it from the basic map -- so it is
                # verified THROUGH its basic original, which the basic pass checks
                if c == "disk" and b.raw.get(n, ("", ""))[1].endswith("basic-resident-abi.inc"):
                    # code labels and `main_` renames are mirrored too; only a RAM
                    # value inside the block needs an original that moves with it
                    orig = n if n in before["basic"].vals else n[5:] if n.startswith("main_") else None
                    if lo <= v < hi and (orig is None or orig not in before["basic"].vals):
                        bad.append(f"disk {n}: a mirror of block RAM with no basic original")
                    mirrors += 1
                    continue
                if n not in a.vals:
                    bad.append(f"{c} {n}: no longer resolves")
                    continue
                if n == "TXTMAX":
                    want = newtop
                elif b.not_a_cell(n) and reaches(b, n, "TXTMAX"):
                    want = v + (newtop - oldtop)
                elif lo <= v < hi and not b.not_a_cell(n):
                    want = v + delta
                elif reaches(b, n, "TXTMAX"):
                    want = v + (newtop - oldtop)
                else:
                    want = v
                if a.vals[n] != want:
                    bad.append(f"{c} {n}: ${v:04X} -> ${a.vals[n]:04X}, want ${want:04X}")
            for n, v in a.vals.items():
                if c == "disk" and a.raw.get(n, ("", ""))[1].endswith("basic-resident-abi.inc"):
                    continue
                if lo <= v < newtop and not a.not_a_cell(n) and v >= 0x8000:
                    bad.append(f"{c} {n}: ${v:04X} is left below the new ceiling")
        print(f"{len(edits)} literal equ(s) rewritten in {len(saved)} file(s); "
              f"TXTMAX ${oldtop:04X} -> ${newtop:04X}")
        for f, i, n, o, v in edits:
            print(f"   {f}:{i}  {n}  ${o:04X} -> ${v:04X}")
        if bad:
            ok = False
            print(f"🔴 REFUSED -- {len(bad)} name(s) did not move as claimed:")
            for b in bad[:40]:
                print("   " + b)
        else:
            moved = sum(1 for c in before for n, v in before[c].vals.items()
                        if after[c].vals.get(n) != v)
            print(f"🟢 VERIFIED: {moved} resolved name(s) moved, each exactly as claimed; "
                  f"every other name unchanged ({mirrors} disk mirror(s) of basic names "
                  f"verified through their originals; the build regenerates them).")
    finally:
        if not ok or "--apply" not in sys.argv:
            for f, text in saved.items():
                open(f, "w").write(text)
            print("(files restored)" if saved else "")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
