#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-KNIFEROM follow-up — which recorded "reddened nothing" verdicts can still be re-run?

`make knife-guard-check` polices the runners that EXIST. This asks the other
question: of the verdicts already written into `docs/`, how many rest on a knife
anyone could run again?

🔴 A "reddened nothing" VERDICT IS ONLY EVIDENCE IF THE CUT REACHED THE ROM, and
only CHECKABLE if the knife still exists. Three shapes, and they are not equally
bad:

  RUNNABLE + GUARDED    the script exists and hashes the built images -> re-runnable
  RUNNABLE + UNGUARDED  the script exists but cannot tell an inert cut from a
                        real null result
  NOT RUNNABLE          no script defines the tag at all -- the knife was applied
                        by hand and never committed, so the verdict is
                        unfalsifiable by anyone, now or later

🎯 AND ONE MORE AXIS THAT MATTERS MORE THAN ALL THREE. A null verdict that
ADDED A ROW is self-correcting: the row is committed and gated, so the finding
no longer rests on the knife. A null verdict used to CLOSE something -- "the
claim is witnessed", "the code is fine" -- rests on the knife forever. This
script reports the axis it can measure and NAMES the rest for reading, rather
than guessing at intent from prose.

⚠️ THIS INSTRUMENT REPORTS WHAT IT CANNOT RESOLVE. The spec -> script mapping is
a heuristic (tag lookup, then filename convention); every unresolved row is
printed as UNRESOLVED rather than silently dropped or guessed into a bucket. A
confident total over a heuristic mapping is exactly the fault this slice already
hit once (docs/spec-kniferom.md §5).
"""
from __future__ import annotations

import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp                       # noqa: E402,F401 -- sets tempfile.tempdir

VERDICT = re.compile(r"(reddened\s+NOTHING|reddened\s+nothing|UNWITNESSED|unwitnessed"
                     r"|moved\s+0\s+row)", re.I)
# a line that TALKS ABOUT the distinction rather than recording an outcome
# 🔴 A SENTENCE ABOUT THE PHRASE IS NOT A VERDICT. The first cut of this filter
# let through ADVICE ("report it as a predicted miss, never as 'reddened
# nothing'") and HYPOTHETICALS ("the knife WOULD HAVE reddened nothing") and
# scored them as unsupported findings -- inflating the alarming bucket with rows
# that record no outcome at all.
META = re.compile(r"separates|distinguish|is the finding, not|rather than|what a knife"
                  r"|indistinguishable|must say so|would report|would have"
                  r"|never as|report it as|is what the ROM-hash guard", re.I)
TAG = re.compile(r"\b(K-?[A-Z]{1,3}\d{1,2}|K\d{1,2})\b")
# 🔴 A KNIFE THAT IS NOT IN THE TREE IS NOT AUTOMATICALLY UNFALSIFIABLE. Several
# specs RECORD the hash transition in the prose -- "the ROM hash moved (d819a385
# vs the baseline af0a69ef)" -- so the evidence survives even though the script
# does not. The first cut of this audit would have reported 8 unfalsifiable
# verdicts; at least two of them carry their proof in the doc. Check the PROSE
# before calling a verdict unsupported.
INDOC = re.compile(r"(ROM|hash(es)?)[^.\n]{0,60}(moved|changed)"
                   r"|moved[^.\n]{0,30}\b[0-9a-f]{8}\b"
                   r"|\b[0-9a-f]{8}\b[^.\n]{0,30}(vs|->)[^.\n]{0,30}\b[0-9a-f]{8}\b", re.I)
HASHES = re.compile(r"hashlib|getsize|st_size|knife_guard")


def scripts():
    out = {}
    for p in glob.glob(os.path.join(ROOT, "scratchpad", "*.py")):
        out[p] = open(p, errors="replace").read()
    return out


def main():
    S = scripts()
    rows = []
    for doc in sorted(glob.glob(os.path.join(ROOT, "docs", "*.md"))):
        lines = open(doc, errors="replace").read().split("\n")
        for i, line in enumerate(lines):
            n = i + 1
            if not VERDICT.search(line) or META.search(line):
                continue
            # 🔴 THE TAG IS RARELY ON THE VERDICT LINE. The first cut only looked
            # at the line itself and left 20 of 25 rows UNRESOLVED -- a mapping
            # that fails four times in five is not a mapping. Knife tags live in
            # the table row, heading or sentence AROUND the claim, so search a
            # window: the line, then outwards.
            tags = TAG.findall(line)
            for d in range(1, 9):
                if tags:
                    break
                for j in (i - d, i + d):
                    if 0 <= j < len(lines):
                        tags = TAG.findall(lines[j])
                        if tags:
                            break
            # 🔴 A GENERIC TAG IS NOT AN IDENTIFIER, AND THE FIRST CUT OF THIS
            # PICKED THE FIRST FILE THAT CONTAINED THE STRING. `K2`, `K5` and
            # `K6` from three unrelated specs all "resolved" to ONE script --
            # confidently, and wrongly. Ambiguity is a VERDICT here, not a
            # tie to be broken. [[readout-blind-to-its-own-subject]]
            owner, how = None, ("NO-TAG" if not tags else None)
            if tags:
                t = tags[0]
                owners = [os.path.relpath(q, ROOT) for q, body in sorted(S.items())
                          if re.search(rf"[\"']{re.escape(t)}\b", body)]
                if len(owners) == 1:
                    owner = owners[0]
                    body = S[os.path.join(ROOT, owner)]
                    how = "GUARDED" if HASHES.search(body) else "UNGUARDED"
                elif len(owners) > 1:
                    how, owner = "AMBIGUOUS", f"{len(owners)} scripts"
                else:
                    ctx = "\n".join(lines[max(0, i - 6):i + 7])
                    how = ("NOT-IN-TREE (proof in doc)" if INDOC.search(ctx)
                           else "NOT-IN-TREE")
            rows.append((os.path.relpath(doc, ROOT), n, tags[0] if tags else "-",
                         owner, how))
    by = {}
    for r in rows:
        by.setdefault(r[4], []).append(r)
    print(f"knife_verdict_audit — {len(rows)} recorded null verdict(s) in docs/\n")
    for how in ("UNGUARDED", "NOT-IN-TREE", "NOT-IN-TREE (proof in doc)",
                "AMBIGUOUS", "NO-TAG", "GUARDED"):
        got = by.get(how, [])
        print(f"  {how:<11} {len(got)}")
    print()
    for how in ("UNGUARDED", "NOT-IN-TREE", "AMBIGUOUS", "NO-TAG"):
        for doc, n, tag, owner, _ in by.get(how, []):
            print(f"  {how:<11} {doc}:{n}  tag={tag:<6} owner={owner or '—'}")
    print(f"""
⚠️  READ THESE BUCKETS EXACTLY AS NAMED:
      UNGUARDED    the knife EXISTS and has no ROM evidence -- the verdict could
                   rest on an inert cut. These are the ones to re-run.
      NOT-IN-TREE  the tag names no script AND the doc records no hash: the
                   knife was hand-applied, and nothing preserves its evidence.
      NOT-IN-TREE (proof in doc)
                   the script is gone but the spec RECORDS the hash transition,
                   so the verdict still stands on written evidence.
      AMBIGUOUS    a generic tag (K2/K5) matches several scripts. NOT a finding
                   about the knife -- a finding about the tag namespace.
      NO-TAG       no knife tag near the claim; the mapping simply failed.
    Only UNGUARDED is a claim about a knife. The rest need reading, and must not
    be counted as either safe or unsafe.""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
