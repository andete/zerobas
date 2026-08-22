#!/usr/bin/env python3
"""D-XREG FOLLOW-UP — spans that differ in exactly ONE byte.

tools/dupspan_indep.py decides safety for BYTE-IDENTICAL spans, and D-DUPSPAN2
spent that supply down to a remainder of a few bytes. tools/clone_scout.py finds
NEAR-clones but by source shape, and its hits need real refactors.

This asks the middle question, which neither does: which spans are identical
EXCEPT AT ONE BYTE POSITION? That is the shape D-DUPSPAN's own carve had --
fourteen `ld a,N / jp raise_error` tails differing only in N -- and it is the
cheapest possible refactor when the differing byte is the OPERAND of the first
instruction: the caller loads its own constant and jumps to one shared tail.

🔴 EVERY SAFETY QUESTION dupspan_indep ASKS STILL APPLIES, AND ONE MORE. A
one-byte-different pair is only collapsible if the difference is an IMMEDIATE
(a value), never a DISPLACEMENT (`jr`'s operand) or half an ADDRESS -- collapsing
those changes where the code goes, not what it computes. So the sweep reports
WHERE the difference is and what the surrounding instruction is, and refuses to
score anything it cannot decode.
"""
from __future__ import annotations
import collections
import sys

sys.path.insert(0, "tools")
from dupspan_indep import build_spans, verdict, decode           # noqa: E402


def diff_positions(a, b):
    return [i for i in range(len(a)) if a[i] != b[i]]


def instr_at(buf, off):
    """Which instruction covers byte `off`, and is `off` its immediate?"""
    i = 0
    while i < len(buf):
        n, term, rel, ok = decode(buf, i)
        if not ok or n == 0:
            return None, None
        if i <= off < i + n:
            return buf[i:i + n], off - i
        i += n
    return None, None


def main() -> int:
    spans = [s for s in build_spans(open("build/basic-reloc.rom", "rb").read())
             if len(s["bytes"]) >= 4 and s["tiles"]]
    bylen = collections.defaultdict(list)
    for s in spans:
        bylen[len(s["bytes"])].append(s)

    hits = []
    for n, group in bylen.items():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                d = diff_positions(a["bytes"], b["bytes"])
                if len(d) != 1:
                    continue
                off = d[0]
                ins, k = instr_at(a["bytes"], off)
                if ins is None:
                    continue
                op = ins[0]
                # the difference must be an IMMEDIATE, and the safest case by far
                # is the operand of a 2-byte `ld r,n` / `cp n` style opcode
                kind = ("relative-DISPLACEMENT" if op in (0x10, 0x18, 0x20, 0x28,
                                                          0x30, 0x38)
                        else "part of an ADDRESS" if len(ins) == 3 and k > 0
                        else "an IMMEDIATE" if len(ins) == 2 and k == 1
                        else "inside a multi-byte operand")
                hits.append((n, a, b, off, ins, kind))
    hits.sort(key=lambda t: -t[0])
    mid = []
    print(f"  denominator: {len(spans)} decodable spans >= 4 B; "
          f"{len(hits)} pairs differ in exactly ONE byte\n")
    gain = 0
    for n, a, b, off, ins, kind in hits:
        va, vb = verdict(a), verdict(b)
        safe2 = va[0].startswith("SAFE") and vb[0].startswith("SAFE")
        # CHEAP: the difference is the immediate of the FIRST instruction, so
        # each site keeps its own `ld a,N` (2 B) + a `jp` (3 B) and the rest of
        # the span is shared once.
        usable = kind == "an IMMEDIATE" and off == 1 and safe2
        rec = n - 5 if usable else 0
        gain += max(rec, 0)
        # DEARER: a MID-span immediate cannot be pre-set by a caller that has to
        # run the instructions before it, so the collapse needs the value in a
        # register and a 2 B prologue per site: n + 4 becomes 2*2 + n, i.e. it
        # saves n - 4 across the pair... minus the `ld a,C` that replaces the
        # `ld a,N` inside (same size) and the `jr` that reaches the shared body.
        if kind == "an IMMEDIATE" and off != 1 and safe2:
            mid.append((n, a["name"], b["name"], max(n - 8, 0)))
        print(f"  {n:3d} B  ${a['addr']:04X} {a['name']:<20s} vs "
              f"${b['addr']:04X} {b['name']:<20s}")
        print(f"         differs at byte {off} ({kind}), instruction "
              f"{ins.hex()}; verdicts {va[0]}/{vb[0]}  -> "
              f"{('RECOVERS %d B' % rec) if rec > 0 else 'no'}")
    print(f"\n  MEASURED-USABLE at the cheap end (difference is the FIRST "
          f"instruction's immediate, both spans SAFE): {gain} B")
    if mid:
        print(f"  and {len(mid)} pair(s) whose immediate is MID-SPAN, which needs "
              f"the value in a register and a prologue per site:")
        for n, an, bn, r in mid:
            print(f"      {n:3d} B  {an} / {bn}  -> ~{r} B, and a free register")
        print(f"      ~{sum(r for *_, r in mid)} B in total, against real "
              f"register pressure in already-tight code")
    print("  ⚠️ an upper bound on THIS shape only: a pair whose difference is an "
          "immediate still has to be a pair whose CALLERS can both set it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
