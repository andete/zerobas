#!/usr/bin/env python3
r"""D-DEFERSWEEP — comments that DEFER on a condition, and whether the condition
has since been met.

🔴 THE CLASS, MEASURED RATHER THAN WAITED FOR. Twice on 2026-09-02 a defect was
hiding behind a comment whose CONDITION HAD ALREADY BEEN SATISFIED:

  * basic/printusing.asm — "the float-only format specs ... ARRIVE WITH PHASE-3
    FLOATS". Floats arrived; six specifiers are simply missing (D-PUSING).
  * basic/play.asm — "NO live drain (the interrupt servicer is Slice 3)".
    playsvc.asm ships; read as current it priced PLAY(n) out of existence
    (D-PLAYFN).

A deferral is a PROMISE WITH A TRIGGER, and nothing in this tree watches the
trigger. Both were found by accident while reading for something else. This
sweep is the instrument that would have found them on purpose.

⚠️ IT CANNOT DECIDE, AND DOES NOT PRETEND TO. Whether a condition is MET is a
judgement about the tree's state; the sweep's job is to put every deferral in one
list with its file, line and trigger phrase so a human (or a later pass) can
answer that per row. Reporting a count as if it were a defect count would be the
same over-claim this project keeps catching.
[[a-fix-falsifies-the-justification-beside-it]] [[filed-justification-is-a-claim]]
"""
import glob, os, re, sys

# trigger phrases: a deferral names a FUTURE EVENT. Kept narrow on purpose --
# "TODO" and "for now" match half the tree and would bury the real ones.
# 🔴 ROUND 1 WAS TOO WIDE AND ITS OWN OUTPUT SAID SO: a bare `\bdeferred\b`
# returned 186 hits, dominated by this tree's DEFERRED-ERROR vocabulary
# ("raise a deferred FPERR=4", "the deferred-error discipline") -- a RUNTIME
# MECHANISM, not a feature promise. A sweep whose signal is buried under its own
# false positives is the instrument failing the way the thing it replaced failed.
# Narrowed to deferrals that name a FUTURE EVENT, and "deferred" only when it is
# NOT about an error.
PATTERNS = [
    (r"arrives? with\b",                       "arrives with <event>"),
    (r"\bnot yet implemented\b",               "not yet implemented"),
    (r"\bPhase-?\d\b",                         "Phase-N gated"),
    (r"\bwhen .{0,40}\blands?\b",              "when X lands"),
    (r"\buntil .{0,40}\bships?\b",             "until X ships"),
    (r"\bare deferred\b|\bis deferred\b",      "is/are deferred"),
]
# the deferred-ERROR idiom, which is a runtime concept and never a promise
NOISE = re.compile(r"deferred (error|fault|FPERR|syntax|TM|type|numeric)"
                   r"|deferred-error|deferred to (the statement|AFTER)", re.I)

def main() -> int:
    files = sorted(glob.glob("basic/*.asm") + glob.glob("basic/*.inc")
                   + glob.glob("sub/*.asm") + glob.glob("disk/*.asm"))
    hits = []
    for f in files:
        for n, line in enumerate(open(f, errors="replace"), 1):
            if ";" not in line:
                continue
            comment = line.split(";", 1)[1]
            for pat, name in PATTERNS:
                if NOISE.search(comment):
                    break
                if re.search(pat, comment, re.I):
                    hits.append((f, n, name, comment.strip()[:96]))
                    break
    by_file = {}
    for f, n, name, txt in hits:
        by_file.setdefault(f, []).append((n, name, txt))
    print(f"deferral-style comments: {len(hits)} in {len(by_file)} file(s), "
          f"over {len(files)} source file(s)\n")
    for f in sorted(by_file, key=lambda k: -len(by_file[k])):
        print(f"  {f}  ({len(by_file[f])})")
        for n, name, txt in by_file[f][:4]:
            print(f"     {n:5d}  [{name}]  {txt}")
        if len(by_file[f]) > 4:
            print(f"     ... {len(by_file[f]) - 4} more")
    print("\n🔴 A COUNT HERE IS NOT A DEFECT COUNT. Each row is a PROMISE WITH A\n"
          "   TRIGGER; whether the trigger has fired is a judgement per row.\n"
          "\n"
          "📏 MEASURED PRECISION, all 30 rows dispositioned 2026-09-03:\n"
          "     1  REAL DEFECT   sound.asm's GICINI deferral -> D-GICINI, 6 rows\n"
          "     4  STALE PROSE   strvar.asm 'NO string functions', traps.asm\n"
          "                      'KEY/SPRITE arrive with T3/T4', save.asm's future\n"
          "                      tense, sub/sub.asm 'no real tenants yet'\n"
          "     4  ALREADY FIXED the sysvars.inc rows this sweep itself found\n"
          "    21  DESCRIPTIVE   'the Phase-1.5 HOST side', 'arrives with FPERR\n"
          "                      clean' -- a phase NAME or a runtime event, not a\n"
          "                      promise. These are the cost of a narrow pattern\n"
          "                      set, and they are cheap to reject by eye.\n"
          "   So ~1 defect and 4 doc-debt corrections per 30 hits. That is the\n"
          "   instrument's yield ON ITS FIRST FULL PASS, over a tree nobody had\n"
          "   swept before; a second pass over the same rows will yield far less,\n"
          "   and the number to watch is what NEW deferrals arrive with.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
