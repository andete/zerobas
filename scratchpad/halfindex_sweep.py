#!/usr/bin/env python3
r"""D-HALFIDX — price IXH/IXL/IYH/IYL against this tree, on BOTH axes.

Asked by Joost 2026-08-28 ("are we considering using them yet?"), who also
confirmed the instructions are supported by every official MSX machine — so
hardware availability is NOT the question and is not re-litigated here.

🎯 THE PREFIX BYTE IS THE WHOLE STORY ON THE SIZE AXIS. Every half-index access
costs 2 B (`ld ixl,a` = DD 6F), against 1 B for a normal register and 1 B each
for `push rr`/`pop rr`. So a half-index register NEVER beats a register or the
stack for size; it beats only a MEMORY temporary at 3 B per access. That reduces
the entire size opportunity to one shape:

        ld   (cell),a        3 B  ->  ld   ixl,a       2 B
        ...                          ...
        ld   a,(cell)        3 B  ->  ld   a,ixl       2 B
                             ---                       ---
                             6 B                       4 B     = 2 B per pair

This sweep counts that shape, then applies the test that actually decides it:
**a spill is convertible only if NOTHING ELSE READS THE CELL.** A cell with other
readers is not a spill, it is state, and the value has to stay in memory.

Excluded conservatively: pointer derefs ((hl)/(de)/(bc)/(ix)/(iy)/(sp)) are not
memory temporaries; and any window containing a `call`/`rst`, because a call can
clobber IX/IY — CALSLT certainly does, and IYh is already the slot-id parameter
of that very ABI (basic/subromcall.asm, basic/initext.asm, sub/format.asm are
this tree's ONLY three half-index references today, all of them ABI, none an
optimisation).

Region matters more than the total: sub-ROM had 2444 + 1622 B free on
2026-08-28 against main's 38 + 124 B, so a sub byte is not a carve.

  --selftest  plants a known pure spill and a known multi-reader cell and exits
              non-zero unless the first is reported and the second rejected.
"""
from __future__ import annotations
import collections, re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
INSN = re.compile(r"^\s+([a-z][a-z0-9]*)\b\s*(.*)$", re.I)
LAB = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")
PTR = {"(hl)", "(de)", "(bc)", "(sp)", "(ix)", "(iy)"}
WINDOW = 12


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


def load_sym():
    d = {}
    f = ROOT / "build/basic-reloc.sym"
    if f.exists():
        for line in f.read_text().splitlines():
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s+EQU\s+0?([0-9A-Fa-f]+)H",
                         line.strip(), re.I)
            if m: d[m.group(1)] = int(m.group(2), 16)
    return d


def scan(files):
    """-> [(region, rel, n_store, n_load, cell)]"""
    sym = load_sym()
    hits = []
    for p in files:
        rel = (str(p.relative_to(ROOT)) if p.is_relative_to(ROOT)
               else str(p))          # the selftest plants its fixture outside ROOT
        seq, lab = [], None
        for n, raw in enumerate(p.read_text().splitlines(), 1):
            line = strip_comment(raw)
            if not line.strip(): continue
            m = LAB.match(line)
            if m:
                lab = m.group(1)
                rest = line[m.end():].strip()
                if not rest: continue
                line = "    " + rest
            mi = INSN.match(line)
            if mi:
                ops = [o.strip().lower() for o in mi.group(2).split(",")] \
                      if mi.group(2).strip() else []
                seq.append((n, mi.group(1).lower(), ops, lab))
        for i, (n, mn, ops, lb) in enumerate(seq):
            if not (mn == "ld" and len(ops) == 2 and ops[1] == "a"
                    and re.fullmatch(r"\([a-z_][a-z0-9_]*\)", ops[0])
                    and ops[0] not in PTR):
                continue
            cell = ops[0]
            for j in range(i + 1, min(i + 1 + WINDOW, len(seq))):
                n2, m2, o2, _ = seq[j]
                if m2 in ("call", "rst"): break        # IX/IY may not survive
                if m2 == "ld" and o2[:1] == ["a"] and len(o2) == 2 and o2[1] == cell:
                    if rel.startswith("sub/"):
                        reg = "sub"
                    else:
                        a = sym.get(lb)
                        reg = ("MAIN low" if a is not None and a < 0x4000
                               else "MAIN p1" if a is not None else "MAIN ?")
                    hits.append((reg, rel, n, n2, cell))
                    break
                if m2 == "ld" and len(o2) == 2 and o2[0] == cell: break
    return hits


def readers(cell, files):
    """every reference to the cell's NAME across the tree (comments stripped)."""
    name = cell.strip("()")
    pat = re.compile(rf"\b{re.escape(name)}\b", re.I)
    n = 0
    for p in files:
        for line in p.read_text().splitlines():
            if pat.search(strip_comment(line)): n += 1
    return n


def main(argv):
    files = sorted(ROOT.glob("basic/*.asm")) + sorted(ROOT.glob("sub/*.asm"))

    if "--selftest" in argv:
        import tempfile, os
        d = pathlib.Path(tempfile.mkdtemp(dir="/tmp/zerobas"))
        (d / "t.asm").write_text(
            "lbl:\n"
            "                ld      (pure_spill),a\n"
            "                inc     b\n"
            "                ld      a,(pure_spill)\n"
            "                ld      (shared_cell),a\n"
            "                inc     b\n"
            "                ld      a,(shared_cell)\n"
            "                ld      hl,shared_cell\n"
            "                ld      b,(shared_cell)\n")
        hits = scan([d / "t.asm"])
        cells = {h[4] for h in hits}
        ok = "(pure_spill)" in cells and "(shared_cell)" in cells
        r1 = readers("(pure_spill)", [d / "t.asm"])
        r2 = readers("(shared_cell)", [d / "t.asm"])
        ok = ok and r1 == 2 and r2 > 2
        print(f"selftest: hits={len(hits)} cells={sorted(cells)} "
              f"pure_spill refs={r1} shared_cell refs={r2}")
        print("selftest OK" if ok else "selftest FAILED")
        return 0 if ok else 1

    hits = scan(files)
    byreg = collections.Counter(h[0] for h in hits)
    print("D-HALFIDX — the ONLY size shape a half-index register wins: a memory")
    print("spill pair (6 B) -> two prefixed register moves (4 B) = 2 B each.\n")
    print(f"{'region':<10s} {'pairs':>5s} {'B ceiling':>10s}")
    for reg, n in sorted(byreg.items(), key=lambda kv: -kv[1]):
        print(f"{reg:<10s} {n:>5d} {n*2:>10d}")
    print()
    print("🔴 NOW THE TEST THAT DECIDES IT — other readers of the cell:")
    conv, rej = [], []
    seen = set()
    for reg, rel, n1, n2, cell in hits:
        if reg == "sub" or cell in seen: continue
        seen.add(cell)
        r = readers(cell, files)
        (conv if r <= 2 else rej).append((reg, rel, n1, n2, cell, r))
    for reg, rel, n1, n2, cell, r in sorted(rej, key=lambda x: -x[5]):
        print(f"   REJECT {cell:<14s} {r:>3d} refs  — state, not a spill "
              f"({rel}:{n1})")
    for reg, rel, n1, n2, cell, r in conv:
        print(f"   ✅ CONVERTIBLE {cell:<14s} {r:>3d} refs  {rel}:{n1}->{n2} [{reg}]")
    print()
    print(f"MAIN size verdict: {len(conv)} convertible pair(s) = {len(conv)*2} B "
          f"(of {byreg['MAIN low']+byreg['MAIN p1']} raw hits).")
    print("PERF axis is the live one: the sub-ROM pairs sit in the inner loops")
    print("(graphics + fp_*), sub bytes are ~free, and the pair is 26 T-states")
    print("against 16 for the half-index form (21 for push/pop).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
