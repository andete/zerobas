#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RAMSHIFT: move blocks of zerobas's private workspace, and PROVE that
exactly those blocks moved.

    python3 tools/ws_shift.py --move LO HI DELTA [--move ...] [--txtmax X]
                              [--nodisk Y] [--disk-only NAME,...] [--apply]
    python3 tools/ws_shift.py LO HI DELTA NEWTXTMAX [--apply]   (the D-RAMSHIFT
                              form: one move and a new TXTMAX)

Every `NAME equ $XXXX` whose LITERAL value lies in a move's [LO, HI), in the
basic component's sources (basic/, sub/) and the disk component's (disk/),
gets that move's DELTA (DELTA may be negative: `-C96`); --txtmax sets TXTMAX
(the disk build's text ceiling, NOT-A-CELL), --nodisk sets TXTMAX_NODISK (the
diskless one, D-RAMCEIL). Generated files (*basic-resident-abi.inc) are
skipped: the build regenerates them, and their names are verified through their
basic originals. Several moves are applied AT ONCE, so blocks can SWAP places.

🔴 THE REWRITE IS NOT THE CLAIM; THE RESOLVED MAP IS. tools/ram_map.py resolves
every name of both components BEFORE and AFTER (source only, no .sym -- a stale
build must not vouch for it), and the run REFUSES -- restoring every file --
unless:
  * every name that resolved into a move's range moved by exactly its DELTA;
  * every name whose expression reaches TXTMAX (transitively) moved by exactly
    TXTMAX's change (DSK_ENGTAB sits just under the ceiling);
  * every other name is unchanged;
  * NO NEW OVERLAP: every pair of cells (both components, declared widths) that
    overlaps afterwards overlapped before -- an overlay moves as a unit, and no
    block lands on a tenant (this replaced the one-move "destination is a hole"
    check, which cannot see a swap);
  * nothing but NOT-A-CELL constants lies under TXTMAX, and between TXTMAX and
    TXTMAX_NODISK lie only the --disk-only names (and disk-map cells) -- that
    span is PROGRAM RAM on the diskless build;
  * a DELTA that is not a multiple of $100 moves no name that code uses in a
    page-relative idiom (`high X`, `low X`, `X & $FF`): such a delta changes low
    bytes, so it is refused for exactly those names.

Without --apply it rewrites, verifies, prints the verdict and RESTORES.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
os.chdir(REPO)
import ram_map                                      # noqa: E402

EQU_LIT = re.compile(r"^(\s*([A-Za-z_][A-Za-z0-9_]*)\s+equ\s+)\$([0-9A-Fa-f]{4})\b(.*)$",
                     re.IGNORECASE)
CODE_GLOBS = ("basic/*.asm", "basic/*.inc", "sub/*.asm", "sub2/*.asm", "disk/*.asm", "disk/*.inc")


def resolve_all():
    return {c: ram_map.Map(c, 0, 0x10000, use_sym=False) for c in ("basic", "disk")}


def reaches(m, name, target, seen=None):
    seen = seen or set()
    if name in seen:
        return False
    seen.add(name)
    expr = m.raw.get(name, ("",))[0]
    for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr):
        if tok == target or (tok in m.raw and reaches(m, tok, target, seen)):
            return True
    return False


def is_mirror(m, n):
    return m.comp == "disk" and m.raw.get(n, ("", ""))[1].endswith("basic-resident-abi.inc")


def page_idiom_names():
    import glob
    used = set()
    pat = re.compile(r"\b(?:high|low)\s+\(?\s*([A-Za-z_][A-Za-z0-9_]*)|"
                     r"([A-Za-z_][A-Za-z0-9_]*)[^;,\n]*&\s*\$FF\b", re.IGNORECASE)
    for g in CODE_GLOBS:
        for f in glob.glob(g):
            for ln in open(f):
                code = ln.split(";", 1)[0]
                for m in pat.finditer(code):
                    used.add(m.group(1) or m.group(2))
    return used


def overlaps(cells):
    cells = sorted(cells, key=lambda c: c[2])
    pairs = set()
    for i, (c1, n1, a1, e1) in enumerate(cells):
        for c2, n2, a2, e2 in cells[i + 1:]:
            if a2 >= e1:
                break
            if (c1, n1) != (c2, n2):
                pairs.add(tuple(sorted([(c1, n1), (c2, n2)])))
    return pairs


def parse_args():
    argv = sys.argv[1:]
    moves, txtmax, nodisk, donly = [], None, None, set()
    pos = [a for a in argv if not a.startswith("--")]
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--move":
            moves.append(tuple(int(x.replace("$", ""), 16) for x in argv[i + 1:i + 4]))
            i += 4
            continue
        if a == "--txtmax":
            txtmax = int(argv[i + 1].replace("$", ""), 16); i += 2; continue
        if a == "--nodisk":
            nodisk = int(argv[i + 1].replace("$", ""), 16); i += 2; continue
        if a == "--disk-only":
            donly |= set(argv[i + 1].split(",")); i += 2; continue
        i += 1
    if not moves and len(pos) == 4:                 # the D-RAMSHIFT form
        lo, hi, delta, top = (int(x.replace("$", ""), 16) for x in pos)
        moves, txtmax = [(lo, hi, delta)], top
    if not moves:
        sys.exit(__doc__)
    return moves, txtmax, nodisk, donly


def main():
    moves, newtop, newnod, donly = parse_args()
    before = resolve_all()
    oldtop = before["basic"].vals["TXTMAX"]
    oldnod = before["basic"].vals.get("TXTMAX_NODISK", oldtop)
    newtop = oldtop if newtop is None else newtop
    newnod = oldnod if newnod is None else newnod
    if newnod < newtop:
        sys.exit("REFUSED: the diskless ceiling cannot be below the disk one")

    def move_of(v):
        for lo, hi, d in moves:
            if lo <= v < hi:
                return d
        return None

    # page-idiom names may only move by whole pages
    idioms = page_idiom_names()
    bad_pg = sorted(n for c, m in before.items() for n, v in m.vals.items()
                    if n in idioms and move_of(v) is not None and move_of(v) % 0x100
                    and not m.not_a_cell(n))         # constants never move
    if bad_pg:
        sys.exit(f"REFUSED: a non-page delta would move page-idiom name(s): {bad_pg}")

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
                new = None
                if name == "TXTMAX":
                    new = newtop
                elif "NOT-A-CELL" not in ln and move_of(val) is not None:
                    new = val + move_of(val)
                if new is not None and new != val:
                    ln = f"{mt.group(1)}${new:04X}{mt.group(4)}"
                    edits.append((f, i, name, val, new))
                    changed = True
            elif re.match(r"^\s*TXTMAX_NODISK\s+equ\s", ln, re.IGNORECASE) and newnod != oldnod:
                ln = re.sub(r"(equ\s+)\S+", lambda m: f"{m.group(1)}${newnod:04X}", ln, count=1)
                edits.append((f, i, "TXTMAX_NODISK", oldnod, newnod))
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
                if is_mirror(b, n):
                    orig = n if n in before["basic"].vals else n[5:] if n.startswith("main_") else None
                    if move_of(v) is not None and (orig is None or orig not in before["basic"].vals):
                        bad.append(f"disk {n}: a mirror of moved RAM with no basic original")
                    mirrors += 1
                    continue
                if n not in a.vals:
                    bad.append(f"{c} {n}: no longer resolves")
                    continue
                if n == "TXTMAX":
                    want = newtop
                elif n == "TXTMAX_NODISK":
                    want = newnod
                elif reaches(b, n, "TXTMAX"):
                    want = v + (newtop - oldtop)
                elif move_of(v) is not None and not b.not_a_cell(n):
                    want = v + move_of(v)
                else:
                    want = v
                if a.vals[n] != want:
                    bad.append(f"{c} {n}: ${v:04X} -> ${a.vals[n]:04X}, want ${want:04X}")
        # no new overlap (window: the workspace and a margin)
        win = (min(newtop, oldtop) - 0x400, 0xF380)
        bm = {c: ram_map.Map(c, *win, use_sym=False) for c in ("basic", "disk")}
        # 🔴 WIDTHS FROM THE *BEFORE* MAP, APPLIED AT THE *AFTER* ADDRESSES. The
        # first cut read each map's own inferred widths, and ram_map DROPS the
        # width of cells that overlap (disputed / overrun) -- so two cells moved
        # onto each other vanished from the check at the moment they collided:
        # the negative control (STRSCR moved onto FLD_DESC alone) VERIFIED.
        width = {}
        for c, m in bm.items():
            for ad in m.addrs:
                w = m.width.get(ad)
                if w:
                    for n in m.byaddr[ad]:
                        width[(c, n)] = w
        def cells(maps_vals, base):
            out = []
            for c in ("basic", "disk"):
                m = base[c]
                for ad in m.addrs:
                    for n in m.byaddr[ad]:
                        if is_mirror(m, n) or (c, n) not in width:
                            continue
                        v = maps_vals[c].vals.get(n, ad)
                        out.append((c, n, v, v + width[(c, n)]))
            return out
        new_pairs = overlaps(cells(after, bm)) - overlaps(cells(before, bm))
        am = {c: ram_map.Map(c, *win, use_sym=False) for c in ("basic", "disk")}
        for p in sorted(new_pairs)[:20]:
            bad.append(f"NEW OVERLAP: {p[0][0]}:{p[0][1]} with {p[1][0]}:{p[1][1]}")
        # what lies under the ceilings
        for c, m in am.items():
            for ad in m.addrs:
                if ad >= newnod:
                    continue
                ns = m.byaddr[ad]
                if all(m.not_a_cell(n) or is_mirror(m, n) for n in ns):
                    continue
                if ad < newtop:
                    # only an ARRIVAL is a finding: MSX-DOS boot-path cells
                    # (DOS_RESV_TOP $DF93) have always lived below the ceiling
                    was = [before[c].vals.get(n) for n in ns]
                    if any(w is not None and w >= oldtop for w in was):
                        bad.append(f"{c} {'/'.join(ns)} ${ad:04X}: moved under the DISK "
                                   f"ceiling ${newtop:04X}")
                    continue
                if c == "basic" and not any(n in donly for n in ns):
                    bad.append(f"basic {'/'.join(ns)} ${ad:04X}: in the diskless program RAM "
                               f"[${newtop:04X}, ${newnod:04X}) and not --disk-only")
        print(f"{len(edits)} literal equ(s) rewritten in {len(saved)} file(s); "
              f"TXTMAX ${oldtop:04X} -> ${newtop:04X}; TXTMAX_NODISK ${oldnod:04X} -> ${newnod:04X}")
        for f, i, n, o, v in edits:
            print(f"   {f}:{i}  {n}  ${o:04X} -> ${v:04X}")
        if bad:
            ok = False
            print(f"🔴 REFUSED -- {len(bad)} finding(s):")
            for x in bad[:40]:
                print("   " + x)
        else:
            moved = sum(1 for c in before for n, v in before[c].vals.items()
                        if after[c].vals.get(n) not in (None, v))
            print(f"🟢 VERIFIED: {moved} resolved name(s) moved, each exactly as claimed; "
                  f"every other name unchanged; no new overlap; nothing but disk-only "
                  f"cells between the ceilings ({mirrors} disk mirror(s) of basic names "
                  f"verified through their originals; the build regenerates them).")
    finally:
        if not ok or "--apply" not in sys.argv:
            for f, text in saved.items():
                open(f, "w").write(text)
            print("(files restored)" if saved else "")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
