#!/usr/bin/env python3
r"""D-PEEPHOLE — price the classic Z80 size idioms AGAINST THIS TREE.

Source of the pattern list: the WikiTI "Z80 Optimization" page (user, 2026-08-28).
A list of tricks is not a finding; the finding is HOW MANY BYTES EACH IS WORTH
HERE. Two of the page's entries are already closed and are reported as such
rather than re-counted:
  * `jp`->`jr`            — D-JRSLICE/2, FULLY BANKED 2026-08-24
  * `call X`/`ld a,(hl)`  — D-RETLN/D-EVSPDUP, gated by tools/redundant_load_sweep.py

🔴 EVERY HIT IS A CANDIDATE, NOT A CARVE. Most of these idioms CHANGE FLAGS, and
this tree is full of code that reads flags across the rewrite point
([[a-mechanical-fix-can-break-a-different-invariant]]: three separate breakages
on 2026-08-26, each caught by a DIFFERENT gate). So each pattern is classified:

  SAFE   the rewrite has identical flag effects, or the sequence itself ends in
         something that redefines every flag it could have set.
  FLAGS  byte-identical result, DIFFERENT flags -- each site needs its successor
         read before it can be taken.
  REGS   needs a scratch register to be free at that point -- needs reading.

The counts are exact; the SAVINGS COLUMN IS A CEILING, and for FLAGS/REGS rows a
ceiling that no one should quote as a carve.
"""
from __future__ import annotations
import collections, re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = sorted(ROOT.glob("basic/*.asm")) + sorted(ROOT.glob("sub/*.asm"))
LABEL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")
INSN_RE = re.compile(r"^\s+([a-z][a-z0-9]*)\b\s*(.*)$", re.I)


def strip_comment(s):
    out, q = [], None
    for ch in s:
        if q:
            out.append(ch)
            if ch == q: q = None
            continue
        if ch in "\"'": q = ch; out.append(ch); continue
        if ch == ";": break
        out.append(ch)
    return "".join(out).rstrip()


def load_syms():
    """label -> address, per image. A byte in sub/ is worth far less than a byte
    in main's low region, so a bare hit count is not a price."""
    out = {}
    for tag, path in (("main", "build/basic-reloc.sym"), ("sub", "build/sub.sym")):
        d = {}
        f = ROOT / path
        if f.exists():
            for line in f.read_text().splitlines():
                m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s+EQU\s+0?([0-9A-Fa-f]+)H",
                             line.strip(), re.I)
                if m:
                    d[m.group(1)] = int(m.group(2), 16)
        out[tag] = d
    return out


def region_of(rel, label, syms):
    """Which scarce pool does a byte here come out of?"""
    img = "sub" if rel.startswith("sub/") else "main"
    addr = syms[img].get(label)
    if addr is None:
        return f"{img}/?"
    if img == "sub":
        return "sub p0" if addr < 0x4000 else "sub p1"
    return "MAIN low" if addr < 0x4000 else "MAIN p1"


def parse():
    """-> {relpath: [(lineno, mn, [ops], is_label_here, nearest_label)]}"""
    files = {}
    for p in SRC:
        rel = str(p.relative_to(ROOT))
        seq, pending_label, last_label = [], False, None
        for n, raw in enumerate(p.read_text().splitlines(), 1):
            line = strip_comment(raw)
            if not line.strip(): continue
            m = LABEL_RE.match(line)
            if m:
                pending_label = True
                last_label = m.group(1)
                rest = line[m.end():].strip()
                if not rest: continue
                line = "                " + rest
            mi = INSN_RE.match(line)
            if not mi: continue
            ops = [o.strip().lower() for o in mi.group(2).split(",")] \
                  if mi.group(2).strip() else []
            seq.append((n, mi.group(1).lower(), ops, pending_label, last_label))
            pending_label = False
        files[rel] = seq
    return files


# 🔴 `a b c d e` ARE ALL VALID HEX DIGITS. The first cut of is_imm() accepted a
# bare register name as an immediate, so `ld d,a / ld e,b` -- a register MOVE --
# counted as a loadable constant pair and inflated that row. Registers are
# excluded by name before anything else is asked.
REGS8 = {"a", "b", "c", "d", "e", "h", "l", "i", "r",
         "ixh", "ixl", "iyh", "iyl"}
REGS16 = {"af", "af'", "bc", "de", "hl", "ix", "iy", "sp"}


def is_imm(s):
    s = s.strip()
    if not s or s in REGS8 or s in REGS16 or s.startswith("("):
        return False
    # a number in any of pasmo's forms, or a symbolic constant / expression
    return bool(re.fullmatch(r"\$[0-9a-fA-F]+|%[01]+|[0-9][0-9a-fA-F]*[hH]?"
                             r"|'.'|[A-Za-z_][A-Za-z0-9_]*"
                             r"|[A-Za-z_$%0-9][^,]*", s))


# --- each rule: (name, window, matcher, bytes_saved, klass, note) -----------
def r_lda0(w):
    n, mn, ops = w[0][0], w[0][1], w[0][2]
    return mn == "ld" and ops[:1] == ["a"] and len(ops) == 2 and ops[1] in ("0", "$00", "%00000000")

def r_cp0(w):
    n, mn, ops = w[0][0], w[0][1], w[0][2]
    return mn == "cp" and ops == ["0"]

def r_ldbc(w):
    n1, m1, o1 = w[0][:3]
    n2, m2, o2, lab2 = w[1][:4]
    if lab2: return False
    pairs = {("b", "c"), ("d", "e"), ("h", "l")}
    return (m1 == m2 == "ld" and len(o1) == 2 and len(o2) == 2
            and (o1[0], o2[0]) in pairs and is_imm(o1[1]) and is_imm(o2[1]))

def r_ldhl_imm(w):
    n1, m1, o1 = w[0][:3]
    n2, m2, o2, lab2 = w[1][:4]
    if lab2: return False
    return (m1 == "ld" and o1[:1] == ["a"] and len(o1) == 2 and is_imm(o1[1])
            and m2 == "ld" and o2 == ["(hl)", "a"])

def r_callret(w):
    n1, m1, o1 = w[0][:3]
    n2, m2, o2, lab2 = w[1][:4]
    if lab2: return False
    return m1 == "call" and len(o1) == 1 and m2 == "ret" and not o2

def r_djnz(w):
    n1, m1, o1 = w[0][:3]
    n2, m2, o2, lab2 = w[1][:4]
    if lab2: return False
    return m1 == "dec" and o1 == ["b"] and m2 == "jr" and o2[:1] == ["nz"]

def r_slarl(w):
    n1, m1, o1 = w[0][:3]
    n2, m2, o2, lab2 = w[1][:4]
    if lab2: return False
    return m1 == "sla" and o1 == ["l"] and m2 == "rl" and o2 == ["h"]

def r_cpl(w):
    n, mn, ops = w[0][0], w[0][1], w[0][2]
    return mn == "xor" and ops and ops[0] in ("$ff", "255", "%11111111")

def r_incvar(w):
    n1, m1, o1 = w[0][:3]
    n2, m2, o2, l2 = w[1][:4]
    n3, m3, o3, l3 = w[2][:4]
    if l2 or l3: return False
    return (m1 == "ld" and o1[:1] == ["a"] and len(o1) == 2
            and o1[1].startswith("(") and not o1[1] in ("(hl)", "(de)", "(bc)")
            and m2 in ("inc", "dec") and o2 == ["a"]
            and m3 == "ld" and len(o3) == 2 and o3[0] == o1[1] and o3[1] == "a")

def r_andcp(w):
    n1, m1, o1 = w[0][:3]
    n2, m2, o2, l2 = w[1][:4]
    n3, m3, o3, l3 = w[2][:4]
    if l2 or l3: return False
    return (m1 == "and" and len(o1) == 1 and m2 == "cp" and o2 == o1
            and m3 in ("jr", "jp") and o3[:1] in (["z"], ["nz"]))

def r_popmove(w):
    n1, m1, o1 = w[0][:3]
    n2, m2, o2, l2 = w[1][:4]
    n3, m3, o3, l3 = w[2][:4]
    if l2 or l3: return False
    pairs = {"bc": ("b", "c"), "de": ("d", "e"), "hl": ("h", "l")}
    if m1 != "pop" or not o1 or o1[0] not in pairs: return False
    hi, lo = pairs[o1[0]]
    return (m2 == "ld" and len(o2) == 2 and o2[1] == hi
            and m3 == "ld" and len(o3) == 2 and o3[1] == lo)

RULES = [
    ("ld a,0            -> xor a",        1, r_lda0,     1, "FLAGS",
     "xor a clears C and sets Z/S from 0; ld a,0 touches nothing"),
    ("cp 0              -> or a",         1, r_cp0,      1, "FLAGS",
     "same Z/S/C, but or a clears N and H"),
    ("xor $FF           -> cpl",          1, r_cpl,      1, "FLAGS",
     "cpl leaves S/Z/P/C alone; xor sets them"),
    ("ld r,n / ld r',n  -> ld rr,nn",     2, r_ldbc,     1, "SAFE",
     "neither form touches flags"),
    ("ld a,n / ld (hl),a-> ld (hl),n",    2, r_ldhl_imm, 1, "SAFE",
     "but A is clobbered in the before-form only -- check A is dead"),
    ("call X / ret      -> jp X",         2, r_callret,  1, "SAFE",
     "tail call; only if the return address is not needed"),
    ("dec b / jr nz     -> djnz",         2, r_djnz,     1, "FLAGS",
     "djnz sets NO flags; dec b sets Z/S/N/H"),
    ("sla l / rl h      -> add hl,hl",    2, r_slarl,    3, "FLAGS",
     "add hl,hl leaves Z/S alone"),
    ("ld a,(v)/inc/ld   -> inc (hl)",     3, r_incvar,   2, "REGS",
     "needs HL free AND A dead"),
    ("and n / cp n / jr -> and n / jr",   3, r_andcp,    2, "SAFE",
     "only when n is a single bit -- otherwise cp n is a real test"),
    ("pop rr / ld,ld    -> pop rr'",      3, r_popmove,  2, "SAFE",
     "pop straight into the destination pair"),
]


def main(argv):
    files = parse()
    print("D-PEEPHOLE — the WikiTI Z80 size idioms, counted against basic/ + sub/")
    print(f"denominator: {len(files)} files, "
          f"{sum(len(v) for v in files.values())} instructions\n")
    print("ALREADY CLOSED, not re-counted:")
    print("  jp -> jr                D-JRSLICE/2, FULLY BANKED 2026-08-24")
    print("  call X / ld a,(hl)      D-RETLN/D-EVSPDUP, gated by "
          "tools/redundant_load_sweep.py\n")

    syms = load_syms()
    total = collections.Counter()
    byreg = collections.Counter()
    detail = collections.defaultdict(list)
    for name, win, fn, saved, klass, note in RULES:
        for rel, seq in files.items():
            for i in range(len(seq) - win + 1):
                w = seq[i:i + win]
                try:
                    ok = fn(w)
                except Exception:
                    ok = False
                if ok:
                    reg = region_of(rel, w[0][4], syms)
                    total[name] += 1
                    byreg[(name, reg)] += 1
                    detail[name].append(f"{rel}:{w[0][0]}  [{reg}]")

    print(f"{'idiom':<34s} {'hits':>5s} {'B ceil':>7s}  class  note")
    print("-" * 100)
    grand = collections.Counter()
    for name, win, fn, saved, klass, note in RULES:
        n = total[name]
        grand[klass] += n * saved
        print(f"{name:<34s} {n:>5d} {n*saved:>7d}  {klass:<6s} {note}")
    print("-" * 100)
    for k in ("SAFE", "FLAGS", "REGS"):
        print(f"  {k:<6s} ceiling: {grand[k]:>4d} B")
    print(f"  TOTAL ceiling: {sum(grand.values())} B "
          f"(a CEILING; FLAGS/REGS rows need each site read)")
    print()
    print("BY REGION -- what the bytes are actually WORTH. Main's low region had"
          "\n38 B free and page 1 124 B on 2026-08-28; sub had 2444 + 1622 B, so a"
          "\nsub-ROM byte is not a carve, it is a rounding error.")
    perreg = collections.Counter()
    for (name, reg), n in byreg.items():
        saved = next(r[3] for r in RULES if r[0] == name)
        perreg[reg] += n * saved
    for reg, b in sorted(perreg.items(), key=lambda kv: -kv[1]):
        print(f"  {reg:<10s} {b:>4d} B ceiling")

    if "--sites" in argv:
        print()
        for name, *_ in RULES:
            if detail[name]:
                print(f"== {name}  ({len(detail[name])})")
                for s in detail[name][:40]:
                    print(f"     {s}")
                if len(detail[name]) > 40:
                    print(f"     ... and {len(detail[name])-40} more")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
