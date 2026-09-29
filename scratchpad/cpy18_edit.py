#!/usr/bin/env python3
"""D-CPY18: fold the sub-ROM math's `ld hl,<src> / ld de,<dst> / call <copy18>`
sites into shared entry points in front of ONE copy body.

fat_copy18 (fp_atan.asm) and fsq_copy18 (fp_sqrt.asm) are byte-identical
(`ld bc,18 / ldir / ret`; fp_atan's own header says "identical body"), and the
buffers alias by address: MATH_A = SQRT_Y, MATH_T = SQRT_X,
MATH_R = SQRT_R = HORNER_ACC (basic/sysvars.inc). So a site is named by the
ADDRESS it copies, not the spelling.

A site is three consecutive INSTRUCTIONS (comment-only lines may sit between;
a label between them disqualifies it). It becomes ONE `call`, placed where the
first instruction was, carrying the old `call` line's trailing comment; comment
lines between are kept. Sites whose destination is ARGA/ARGB but whose source
is none of the named buffers keep their `ld hl` and lose only the `ld de`.

    python3 scratchpad/cpy18_edit.py          # dry run: counts per family
    python3 scratchpad/cpy18_edit.py --write  # apply; refuses on a count change
"""
import glob, re, sys

ALIAS = {"math_a": "y", "sqrt_y": "y", "math_t": "x", "sqrt_x": "x",
         "math_r": "r", "sqrt_r": "r", "horner_acc": "r", "arga": "arga", "argb": "argb",
         "horner_g": "x"}
COPY = ("fat_copy18", "fsq_copy18")
# (src, dst) -> entry point; counts cross-checked by an independent awk pass
# (2026-09-29 -- the FIRST scan missed four sites and was the wrong one)
FAM = {("y", "arga"): ("cpy_y_arga", 32), ("y", "argb"): ("cpy_y_argb", 11),
       ("x", "arga"): ("cpy_x_arga", 12), ("x", "argb"): ("cpy_x_argb", 4),
       ("r", "arga"): ("cpy_r_arga", 12), ("r", "argb"): ("cpy_r_argb", 4),
       ("arga", "y"): ("cpy_arga_y", 7)}
# destination-only: `ld de,<dst> / call <copy18>` with HL set some other way ->
# one call; counts from an independent awk classification of all 162 calls
GENERIC = {"arga": ("cpy_arga", 4), "argb": ("cpy_argb", 35), "y": ("cpy_to_y", 13),
           "x": ("cpy_to_x", 8), "r": ("cpy_to_r", 15)}
# 🔴 HORNER_G = SQRT_X too: the first write mapped it to its own "g" entry, which
# was correct code and a wasted 5 B entry; folded into "x" by hand the same hour.


def parse(line):
    """(kind, body, comment): kind is 'blank', 'label' or 'ins'."""
    code, _, com = line.rstrip("\n").partition(";")
    s = code.strip()
    if not s:
        return ("blank", "", com)
    m = re.match(r"^([A-Za-z_.][\w.]*:)\s*(.*)$", s)
    if m or not code[:1].isspace():
        return ("label", s, com)
    return ("ins", re.sub(r"\s+", " ", s.lower()), com)


def operand(ins, op):
    m = re.match(rf"^ld {op},([\w.()]+)$", ins)
    return m.group(1) if m else None


def plan(path):
    lines = open(path, encoding="utf-8").readlines()
    ins = [(i, parse(l)) for i, l in enumerate(lines)]
    code = [(i, p) for i, p in ins if p[0] != "blank"]
    edits = []                          # (first line, [lines to delete], new call, fam key)
    k = 0
    while k + 2 < len(code):
        (i1, a), (i2, b), (i3, c) = code[k], code[k + 1], code[k + 2]
        src, dst = operand(a[1], "hl") if a[0] == "ins" else None, operand(b[1], "de") if b[0] == "ins" else None
        call = c[1] if c[0] == "ins" else ""
        if src and dst and call in tuple("call " + x for x in COPY):
            s, d = ALIAS.get(src), ALIAS.get(dst)
            if (s, d) in FAM:
                edits.append((i1, [i2, i3], FAM[(s, d)][0], (s, d), c[2]))
                k += 3
                continue
        # the destination-only pair, starting at k
        dst1 = operand(a[1], "de") if a[0] == "ins" else None
        call1 = b[1] if b[0] == "ins" else ""
        if dst1 and ALIAS.get(dst1) in GENERIC and call1 in tuple("call " + x for x in COPY):
            d = ALIAS[dst1]
            edits.append((i1, [i2], GENERIC[d][0], ("*", d), b[2]))
            k += 2
            continue
        k += 1
    return lines, edits


def main():
    write = "--write" in sys.argv
    files = sorted(glob.glob("sub/fp_*.asm"))
    got, allplans = {}, []
    for f in files:
        lines, edits = plan(f)
        allplans.append((f, lines, edits))
        for e in edits:
            got[e[3]] = got.get(e[3], 0) + 1
    bad = False
    for key, (name, want) in FAM.items():
        n = got.get(key, 0)
        flag = "" if n == want else "   <-- REFUSE: expected %d" % want
        bad |= n != want
        print(f"  {name:12} {n:3}{flag}")
    for d, (name, want) in GENERIC.items():
        n = got.get(("*", d), 0)
        bad |= n != want
        print(f"  {name:12} {n:3}   (dest only){'' if n == want else '   <-- REFUSE: expected %d' % want}")
    if bad:
        raise SystemExit("REFUSE: a family count moved since the scan -- re-read the sites")
    if not write:
        print("dry run: nothing written")
        return 0
    for f, lines, edits in allplans:
        if not edits:
            continue
        drop, repl = set(), {}
        for first, dels, name, _key, com in edits:
            indent = re.match(r"^(\s*)", lines[first]).group(1)
            new = f"{indent}call    {name}"
            if com.strip():
                new = f"{new:<36}; {com.strip()}"
            repl[first] = new + "\n"
            drop.update(dels)
        out = [repl.get(i, l) for i, l in enumerate(lines) if i not in drop]
        open(f, "w", encoding="utf-8").writelines(out)
        print(f"wrote {f}: {len(edits)} site(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
