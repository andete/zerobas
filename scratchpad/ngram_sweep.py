#!/usr/bin/env python3
r"""D-NGRAM — repeated instruction SEQUENCES, exact operands, priced as routines.

Why this and not tools/clone_scout.py: clone_scout masks up to two operands BY
DESIGN, so it finds PARAMETERISABLE clones and prices them as a `call`. Twice on
2026-08-28 that ranking was beaten 3:1 by grepping a shape by hand (D-BAREEND
+45 B, D-POPRAISE +13 B), because the wins were EXACT repeats collapsible into a
SHARED TAIL, which is a different object. This sweep looks for the exact kind.

PRICING, and it is unforgiving:
  * as a SUBROUTINE: k sites of m bytes -> one body (m + 1 for `ret`) plus k
    `call`s (3 B each).   saving = m*(k-1) - 3k - 1
  * as a SHARED TAIL (the sequence already ends in ret/jp/jr, so no `ret` is
    added and each site jumps instead of calling): saving = m*(k-1) - 3(k-1)
    ... i.e. (m-3)*(k-1), and a site whose predecessor falls through needs the
    jump anyway.
A 6 B sequence at 3 sites is worth 2 B as a subroutine. The arithmetic kills most
of what looks impressive in a raw frequency table, which is the point of printing
it rather than a hit count.

⚠️ SIZES ARE ESTIMATED from the mnemonic form (no listing file is produced by
this build). Anything the estimator cannot price is reported UNKNOWN and never
counted -- a mis-estimate must not be able to manufacture a candidate. The top
candidates are then confirmed by ASSEMBLING them with pasmo.
"""
from __future__ import annotations
import collections, re, subprocess, sys, pathlib, os

ROOT = pathlib.Path(__file__).resolve().parent.parent
INSN = re.compile(r"^\s+([a-z][a-z0-9']*)\b\s*(.*)$", re.I)
LAB = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")
R8 = {"a","b","c","d","e","h","l","(hl)"}
R16 = {"bc","de","hl","sp","af","ix","iy"}
TERM = {"ret", "jp", "jr", "reti", "retn"}


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


def size_of(mn, ops):
    """Estimated encoded length, or None if unsure (never counted)."""
    o = [x.strip().lower() for x in ops.split(",")] if ops.strip() else []
    pre = 1 if any(x.startswith(("ix", "iy", "(ix", "(iy")) for x in o) else 0
    if mn in ("nop","ret","reti","retn","halt","ei","di","exx","daa","cpl","scf",
              "ccf","rlca","rrca","rla","rra","neg","ldi","ldd","ldir","lddr",
              "cpi","cpir"):
        return 1 + (1 if mn in ("neg","ldi","ldd","ldir","lddr","cpi","cpir") else 0)
    if mn == "ld" and len(o) == 2:
        a, b = o
        if a in R8 and b in R8: return 1 + pre + (1 if "(ix" in a+b or "(iy" in a+b else 0)
        if a in R8 and re.fullmatch(r"[-$%\w']+", b): return 2 + pre
        if a in R16 and b == "hl": return 1
        if a in R16: return 3 + pre
        if a.startswith("(") and b == "a": return 3
        if a == "a" and b.startswith("("): return 3
        if a.startswith("(") or b.startswith("("): return 3 + pre
        return None
    if mn in ("inc","dec"):
        if not o: return None
        return (1 if o[0] in R8 | R16 else None) if not o[0].startswith("(i") else 3
    if mn in ("add","adc","sub","sbc","and","or","xor","cp"):
        if len(o) == 2 and o[0] == "hl" and o[1] in R16: return 1 + (1 if mn in ("adc","sbc") else 0)
        t = o[-1]
        return 1 + pre if t in R8 else (2 if re.fullmatch(r"[-$%\w']+", t) else None)
    if mn in ("push","pop"): return 1 + pre
    if mn == "jr": return 2
    if mn == "djnz": return 2
    if mn in ("jp","call"): return 3
    if mn == "rst": return 1
    if mn in ("bit","set","res","rl","rr","sla","sra","srl","rlc","rrc"): return 2 + pre*2
    if mn in ("ex",): return 1
    return None


def parse():
    out = []
    for p in sorted(ROOT.glob("basic/*.asm")) + sorted(ROOT.glob("sub/*.asm")):
        rel = str(p.relative_to(ROOT)); lab = None
        for n, raw in enumerate(p.read_text().splitlines(), 1):
            line = strip_comment(raw)
            if not line.strip(): continue
            m = LAB.match(line)
            if m:
                lab = m.group(1); rest = line[m.end():].strip()
                out.append(("LABEL", rel, n, lab, None, None))
                if not rest: continue
                line = "    " + rest
            mi = INSN.match(line)
            if mi:
                mn = mi.group(1).lower(); ops = mi.group(2).strip()
                key = f"{mn} {re.sub(r'\\s+', '', ops.lower())}"
                out.append(("I", rel, n, key, size_of(mn, ops), mn))
    return out


def main(argv):
    seq = parse()
    print(f"D-NGRAM — exact repeated instruction sequences across "
          f"basic/ + sub/ ({sum(1 for x in seq if x[0]=='I')} instructions)\n")
    # a sequence may not span a LABEL: another entry path would enter mid-body
    runs, cur = [], []
    for kind, rel, n, key, sz, mn in seq:
        if kind == "LABEL":
            if cur: runs.append(cur)
            cur = []
        else:
            cur.append((rel, n, key, sz, mn))
    if cur: runs.append(cur)

    best = []
    for N in range(3, 13):
        grams = collections.defaultdict(list)
        for run in runs:
            for i in range(len(run) - N + 1):
                w = run[i:i + N]
                if any(x[3] is None for x in w):     # unpriceable -> never counted
                    continue
                # 🔴 A CONDITIONAL JUMP IS NOT A TERMINATOR. The first cut
                # keyed "is this a tail?" on the MNEMONIC, so `jp nc,stmt_error`
                # counted as one and the top candidate was priced as a shared
                # tail it can never be -- execution falls through a conditional.
                # Only an unconditional ret/jp/jr (no condition operand) ends a
                # sequence.
                last_key = w[-1][2]
                lm = last_key.split(" ", 1)
                lops = lm[1] if len(lm) > 1 else ""
                uncond = (lm[0] in TERM and
                          (lm[0] in ("ret", "reti", "retn") or
                           lops.split(",")[0] not in
                           ("z","nz","c","nc","p","m","pe","po")) and
                          not (lm[0] == "ret" and lops))
                grams[tuple(x[2] for x in w)].append((w[0][0], w[0][1],
                                                      sum(x[3] for x in w),
                                                      uncond))
        for g, hits in grams.items():
            k = len(hits)
            if k < 2: continue
            m = hits[0][2]
            tail = hits[0][3]
            sub = m * (k - 1) - 3 * k - 1
            shared = (m - 3) * (k - 1) if tail else None
            gain = max(sub, shared if shared is not None else -99)
            if gain > 0:
                best.append((gain, N, k, m, tail, g, hits))
    # 🎯 REGION AGAIN. The raw table is dominated by sub/fp_* -- hundreds of bytes
    # of repeated mathpack calls -- and sub p0/p1 had 2444 + 1622 B free on
    # 2026-08-28. Those bytes buy nothing. Only sites in basic/ come out of a
    # scarce pool, so `--main` scores a candidate on its MAIN-region sites only.
    if "--main" in argv:
        rescored = []
        for gain, N, k, m, tail, g, hits in best:
            mh = [h for h in hits if h[0].startswith("basic/")]
            km = len(mh)
            if km < 2: continue
            sub = m * (km - 1) - 3 * km - 1
            shared = (m - 3) * (km - 1) if tail else -99
            gm = max(sub, shared)
            if gm > 0:
                rescored.append((gm, N, km, m, tail, g, mh))
        best = rescored
    best.sort(reverse=True, key=lambda x: x[0])
    seen = set()
    print(f"{'B':>4s} {'n':>3s} {'x':>3s} {'each':>5s}  shape")
    print("-" * 92)
    shown = 0
    for gain, N, k, m, tail, g, hits in best:
        sig = g[:3]
        if sig in seen: continue
        seen.add(sig); shown += 1
        if shown > 14: break
        kind = "TAIL" if tail else "sub"
        print(f"{gain:>4d} {N:>3d} {k:>3d} {m:>5d}  [{kind}] " + " | ".join(g[:5])
              + (" ..." if N > 5 else ""))
        for rel, ln, _, _ in hits[:4]:
            print(f"                     {rel}:{ln}")
    if not shown:
        print("  (nothing prices positive)")
    print()
    print(f"{len(best)} positively-priced candidate(s) before dedup.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
