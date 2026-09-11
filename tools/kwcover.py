#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-KWCOVER — which of the 159 keywords does the COLLECTED battery actually type?

`make tiers --keywords` reports most keywords as "no known gap (no item, no
kwsweep row -- unverified)", and says in its own words that this is not a tier.
Joost, 2026-09-11: *"given that we have so many keywords still at 'no known gap'
shouldn't we identify their status first before picking up new work?"* -- yes,
and this is the denominator that has to exist before that status can be claimed.

HOW THE INPUT IS OBTAINED, and why it is not a scan.
  The first three cuts scanned the probes' Python strings for BASIC and each one
  returned a plausible table from an input it had misread: `AND` "exercised by
  125 suites" (it was matching the English word), `COPY` by 32, an EMPTY
  unexercised set, then an over-corrected filter that dropped `KILL "A.BAS"`
  (its only token is inside the literal) and `FORI=0TO39:VPOKE...` (MSX needs no
  spaces, so an English word-boundary rule loses the verb).
  🎯 So the lines are CAPTURED, not guessed: `omsx_repl.run_cases` -- the one
  chokepoint every probe types through -- appends each typed line, tagged with
  its suite, when $ZEROBAS_KWCOVER is set. Run:

      ZEROBAS_KWCOVER=$PWD/build/kwcover.tsv make gates      # ~8 min, the battery
      python3 tools/kwcover.py                               # this report

WHAT THE OUTPUT CLAIMS
  UNEXERCISED  no collected suite types the keyword AT ALL. This is a claim:
               nothing in the battery would notice if it broke.
  EXERCISED    at least one collected suite types it. This is NOT "verified" --
               `PRINT` is in almost every readout, and a keyword typed as
               apparatus (a fence, a control, a setup line) is exercised, not
               scored. Separating subject from apparatus is step (c) of the
               per-keyword-table item and this tool does not invent it.
"""
from __future__ import annotations
import os, re, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import tier_table as T                                          # noqa: E402
CAP = os.environ.get("ZEROBAS_KWCOVER") or os.path.join(ROOT, "build", "kwcover.tsv")


def keywords_in(line, kws):
    """Match the way `match_kw` does: longest first, no right boundary (MSX needs
    no spaces -- `FORI=0TO39` really is FOR and TO), and a matched span consumed.
    BASIC string literals are removed first: `PRINT"FOR"` types no FOR."""
    s = re.sub(r'"[^"]*"?', " ", line.upper())
    hits, rest = set(), s
    for kw in kws:
        pat = re.compile(r"(?<![A-Z0-9$])" + re.escape(kw))
        if pat.search(rest):
            hits.add(kw); rest = pat.sub(" ", rest)
    return hits


def main() -> int:
    if not os.path.exists(CAP):
        print(f"kwcover: no capture at {CAP}.\n"
              f"  Run:  ZEROBAS_KWCOVER={CAP} make gates\n"
              f"  A report with no capture would be a guess, and three of those "
              f"were already wrong (see this file's header). Refusing.")
        return 2
    kws = sorted(set(T.kwtable_keywords()) | set(T.KNOWN_MISSING), key=len, reverse=True)
    by_kw: dict[str, set[str]] = collections.defaultdict(set)
    rows_by_kw: dict[str, str] = {}
    suites, lines = set(), 0
    for raw in open(CAP, encoding="utf-8", errors="replace"):
        parts = raw.rstrip("\n").split("\t")
        if len(parts) < 4: continue
        tag, _machine, label, text = parts[0], parts[1], parts[2], "\t".join(parts[3:])
        suites.add(tag); lines += 1
        for kw in keywords_in(text, kws):
            by_kw[kw].add(tag); rows_by_kw.setdefault(kw, f"{tag}:{label}  {text[:60]}")
    allk = sorted(set(kws))
    unex = [k for k in allk if not by_kw[k]]
    print(f"D-KWCOVER: {lines} typed line(s) captured from {len(suites)} suite(s); "
          f"{len(allk)} keywords\n")
    print(f"  EXERCISED   {len(allk) - len(unex):3}  at least one collected suite types it")
    print(f"  UNEXERCISED {len(unex):3}  nothing in the battery types it\n")
    for k in unex:
        print(f"  UNEXERCISED  {k}")
    if "--all" in sys.argv:
        print("\nEXERCISED (suite count, and the first row that types it):")
        for k in allk:
            if by_kw[k]:
                print(f"  {k:9} {len(by_kw[k]):3}  {rows_by_kw[k]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
