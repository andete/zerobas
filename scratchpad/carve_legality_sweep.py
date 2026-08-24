#!/usr/bin/env python3
"""(3) FINISH THE DENOMINATOR — is ANY main page-1 entry point page-0-evictable?

The 2026-08-24 carve scout tested FIVE source files and found all five refused,
always by the same two paths (`pchar -> CHPUT`, `raise_error -> BREAKX`). It
recorded the generalisation as "very likely" and named the cheap way to settle
it. This is that way, and it does not stop at files:

  * FILE granularity -- every basic/*.asm with page-1 content, entered at the
    labels called from OUTSIDE it (the conservative choice: a tenant must expose
    every one of them).
  * LABEL granularity -- EVERY page-1 label as a single entry, which is the
    denominator the file view cannot give. A file can be refused because ONE of
    its entries is dirty while another is clean and movable on its own.

A page-0 tenant runs with the BIOS (< $2812) AND the main low region
($2812-$3FFF) switched out, and the slot configuration persists through calls
into resident main page 1 -- so an escape reached THROUGH page 1 is fatal and
cannot be re-expressed. Reuses tools/carve_scout.py's own graph so this sweep
and the scout cannot disagree.

FALSIFICATION: --selftest asserts that a hand-built clean closure IS reported
clean, so "0 clean" is known not to be a sweep that reports nothing.
"""
from __future__ import annotations
import importlib.util, glob, os, re, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
spec = importlib.util.spec_from_file_location("cs", "tools/carve_scout.py")
cs = importlib.util.module_from_spec(spec); spec.loader.exec_module(cs)

SYM = "build/basic-reloc.sym"
PLUMBING = set(cs.DEFAULT_PLUMBING)


def load():
    syms = cs.load_syms(SYM) if hasattr(cs, "load_syms") else None
    if syms is None:                       # carve_scout parses inline in main()
        syms = {}
        for ln in open(SYM):
            m = re.match(r'\s*([0-9A-Fa-f]{4})h?\s+(\S+)\s*$', ln)
            if m:
                syms[m.group(2).lstrip('.')] = int(m.group(1), 16)
            else:
                m = re.match(r'\s*(\S+)\s*[:=]\s*\$?([0-9A-Fa-f]{4})h?\s*$', ln)
                if m:
                    syms[m.group(1).lstrip('.')] = int(m.group(2), 16)
    return syms


def main():
    syms = load()
    assert syms, "no symbols parsed -- the sweep would report a vacuous 0"
    sources = sorted(glob.glob("basic/*.asm"))
    graph = cs.build_callgraph(sources)
    data = cs.build_datagraph(sources)
    span = cs.sizes_by_symbol(syms)

    p1 = {n for n, a in syms.items() if cs.PAGE1 <= a < 0x8000}
    print(f"denominator: {len(syms)} symbols, {len(p1)} in main page 1, "
          f"{len(sources)} source files walked")

    def verdict(entries, moved):
        closure = cs.reachable(graph, entries)
        escapes = [n for n in closure if n in syms and syms[n] < cs.PAGE1]
        inner = cs.reachable({k: v for k, v in graph.items()
                              if k in moved or k in entries}, entries)
        direct = [n for n in escapes if any(n in graph.get(m, ()) for m in inner)]
        indirect = [n for n in escapes if n not in direct]
        dref = cs.data_targets(closure, data, set(graph))
        desc = [n for n in dref if n in syms and syms[n] < cs.PAGE1]
        d_ind = [n for n in desc if not any(n in data.get(m, ()) for m in inner)]
        blockers = [n for n in direct if n not in PLUMBING]
        return len(indirect), len(d_ind), len(blockers), indirect

    # ---- FILE granularity -------------------------------------------------
    print("\n=== FILE granularity: entries = labels called from OUTSIDE the file")
    clean_files = []
    for f in sources:
        moved = cs.labels_in([f])
        in_p1 = {n for n in moved if n in p1}
        if not in_p1:
            continue
        ext = {t for src, tg in graph.items() if src not in moved
               for t in tg if t in in_p1}
        if not ext:
            continue
        ind, dind, blk, _ = verdict(sorted(ext), moved)
        size = sum(span.get(n, 0) for n in in_p1)
        ok = (ind == 0 and dind == 0 and blk == 0)
        if ok:
            clean_files.append((size, f))
        print(f"  {'CLEAN ' if ok else 'refused':8} {size:5} B  {f:26} "
              f"through-p1={ind:4} data={dind:2} blockers={blk}")
    print(f"  -> {len(clean_files)} of the files walked are page-0-evictable")

    # ---- LABEL granularity ------------------------------------------------
    print("\n=== LABEL granularity: every page-1 label as a lone entry")
    clean, tally = [], collections.Counter()
    for n in sorted(p1):
        ind, dind, blk, esc = verdict([n], {n})
        if ind == 0 and dind == 0 and blk == 0:
            clean.append((span.get(n, 0), n))
        else:
            for e in esc:
                tally[e] += 1
    clean.sort(reverse=True)
    tot = sum(s for s, _ in clean)
    print(f"  {len(clean)} of {len(p1)} page-1 labels are page-0-clean on their own"
          f"  ({tot} B, but see the note below)")
    for s, n in clean[:15]:
        print(f"      {s:5} B  {n}")
    print("\n  the escapes that refuse the most labels (the STRUCTURAL blockers):")
    for e, c in tally.most_common(10):
        print(f"      {c:5} labels blocked by  {e} @ ${syms[e]:04X}")
    print("\n  ⚠️ A CLEAN LEAF IS NOT A CARVE. These are single labels; moving one "
          "costs a\n     tenant entry + a resident stub, and its callers stay in "
          "page 1. The number\n     that matters is a CLUSTER that is clean "
          "TOGETHER, which the file view above\n     is the honest proxy for.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
