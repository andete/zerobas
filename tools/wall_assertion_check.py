#!/usr/bin/env python3
"""Free-space assertions in OPEN TODO items must be DATED.

D-REPRICE (docs/repricing-page1-2026-08-19.md §4) went looking for declines a
64 B carve might fund and found a different class instead: FOUR open `TODO.md`
items asserting a CURRENT free-space figure in prose, as fact, and all four
wrong --

    "THE PAGE-1 WALL IS NOW 14 B"      "main page 1 is now 16 B"
    "Main page 1 is down to 49 B"      "9 B free low / 6 B free page 1"

-- against 5 B low and 64 B page 1 measured that day. Three of the four
UNDERSTATED the wall, so each read as LESS affordable than it was: a slice
opening one and trusting the inline figure would decline work it can already
fund. That is the 160-dead-bytes shape in prose.

🔴 THE HARD HALF IS THE GRAMMAR, NOT THE COMPARE, and this tool does not pretend
otherwise. Deciding "is this sentence stale?" means parsing English tense and
intent. So it asks a DIFFERENT question, which is mechanical and which a human
can always satisfy:

    A free-space figure must carry a DATE or a COMMIT, or say it is historical.

That converts an unanswerable question into a crisp one, and dating a figure
makes its staleness self-evident to the next reader without any tool at all. A
dated reading STANDS AS TAKEN -- this never second-guesses one.

SCOPE, stated rather than implied: only `- [ ]` items in TODO.md. That is the
pickup list, and it is where a stale figure actively misleads the next slice;
every one of the four found was there. Historical figures in dated slice docs
under docs/ are the house style and are none of this tool's business.

🔴 WHAT THIS DOES NOT CATCH, MEASURED RATHER THAN GUESSED (knife K-WA3).
The UNDATED rule is the WEAK half: a figure is exempt if a date appears within
QUAL_RADIUS lines, and that date does not have to be ABOUT the figure. K-WA3
planted "A second rasteriser against 5 B free low region would not fit" one line
below an unrelated "Filed 2026-08-11" and it was NOT flagged. So an undated wall
figure that happens to sit beside any date survives this check.

The radius was chosen by measurement, not preference:

    radius 0 : 4/4 founding defects, but 6 false positives on the clean tree
    radius 1 : 4/4 founding defects, 0 false positives   <-- chosen
    radius 2 : 4/4 founding defects, 0 false positives

Radius 0 flags every dated record whose date wrapped onto the previous line,
which is ordinary prose here. PRESENT-TENSE is the STRONG half and is not
defeated by an adjacent date at all (K-WA2 proves it: a figure dated on its own
line still flags if it says "is now"). Treat a clean run as evidence about
present-tense claims, and only weak evidence about undated ones.
"""
import re, subprocess, sys

TODO = 'TODO.md'

# "N B" within a few words of a region name -- the four real phrasings plus the
# obvious neighbours. Deliberately WIDE: a false positive costs one date, a
# false negative costs a slice.
REGION = r'(?:main )?page[ -]?1|page[ -]?1|low region|free low|\blow\b'
ASSERT = re.compile(
    r'(\d+)\s*B\b[^.\n]{0,60}?(' + REGION + r')'          #  "64 B ... page 1"
    r'|(' + REGION + r')[^.\n]{0,60}?(\d+)\s*B\b',        #  "page 1 ... 64 B"
    re.I)

# A qualifier must sit WITHIN ONE LINE of the figure, not merely somewhere in the
# item.
# 🔴 THE FIRST VERSION SCANNED THE WHOLE BLOCK AND WAS VACUOUS: run against the
# pre-D-REPRICE TODO.md, where all four defects were live, it flagged 0 OF 4.
# Every item names a slice (`D-LSTRNG`) or carries a date somewhere in its
# history, so a block-wide search exempts everything. A gate that cannot redden
# on its own founding defect is measuring nothing -- so the SET was calibrated
# against the known positives BEFORE the tool was believed, and the scope
# tightened until it caught them. `\bwas\b` and a bare slice name are gone with
# it: both are ambient in this file.
DATED = re.compile(
    r'\b20\d\d-\d\d-\d\d\b'          # a date
    r'|`[0-9a-f]{7,40}`'             # a commit, backticked
    r'|\bat\s+`?[0-9a-f]{7}`?'       # "at b51bbbb"
    r'|\bstale\b|\bhistoric'
    r'|\bstands as (taken|written)\b',
    re.I)
# 🔴 PAST-TENSE PROSE IS NOT A QUALIFIER, AND ACCEPTING IT COST THREE OF THE FOUR.
# The second draft allowed `was`/`then`/`before`/`prior`. Re-calibrated against
# the pre-D-REPRICE file it still missed the 14 B, 16 B and 49 B defects: the
# 14 B item's NEXT line reads "82 B **was** itself the post-carve figure", which
# exempted the live assertion above it. `was` is exactly how a stale figure
# reads. Only a DATE or a COMMIT counts -- the one thing a reader can check.
QUAL_RADIUS = 1                      # lines either side of the figure

# 🔴 A DATE IS NOT ENOUGH ON ITS OWN, AND THE FOURTH FOUNDING DEFECT PROVES IT.
# "RE-PRICED 2026-08-09 by D-EVALCHK ... main page 1 **is now 16 B**" carries its
# date on the line above and STILL read as current, because "is now" is a claim
# about the present tense that a date beside it does not retract. Rule 1 (dating)
# catches 3 of the 4; this catches the 4th, and it is deliberately a SEPARATE
# finding with a different remedy: not "add a date" but "say WAS, not IS NOW".
# A COST or a DELTA is history, not a claim about the wall now. "It cost 11 B of
# page 1", "page 1 24 -> 13 B free", "= 14 B page 1" are records of what a slice
# SPENT; re-reading one later misleads nobody. Excluding them took the
# calibration set from 17 figures to 9 without losing any of the four founding
# defects -- the signal is state claims, and a delta arrow is the cheapest
# mechanical tell that a line is not one.
LEDGER = re.compile(r'→|->|\bcosts?\b|\btook\b|\bspent\b|\bfreed\b|\bsaves?d?\b'
                    r'|\bestimated\b|\bpriced\b|\bbreakdown\b'
                    r'|=\s*\d+\s*B\b',   # "ERR 59 = 8 B page 1" -- a price, not a wall
                    re.I)

PRESENT = re.compile(
    r'\bis now\b|\bis down to\b|\bis at\b|\bare now\b'
    r'|\bwall is\b|\bnow (?:only )?(?:down to|at)\b'
    r'|\bhas\b(?=[^.\n]{0,20}\d+\s*B\b)|\bcurrently\b',
    re.I)


def walls():
    """The live four, from the build. None if it could not be measured."""
    try:
        r = subprocess.run(['make', 'basic-reloc'], capture_output=True, text=True)
    except Exception:
        return None
    out = {}
    for m in re.finditer(r'measure:\s+(.+?free)\s*=\s*(\d+) B', r.stdout + r.stderr):
        out[m.group(1).strip()] = int(m.group(2))
    return out or None


def blocks():
    lines = open(TODO, encoding='utf-8').read().split('\n')
    starts = [i for i, l in enumerate(lines) if l.startswith('- [ ]')]
    bounds = sorted({i for i, l in enumerate(lines)
                     if re.match(r'^- \[[ x]\]', l) or l.startswith('#')})
    for s in starts:
        nxt = [b for b in bounds if b > s]
        e = nxt[0] if nxt else len(lines)
        yield s + 1, '\n'.join(lines[s:e])


def main():
    w = walls()
    print("== live walls ==")
    if w:
        for k, v in w.items():
            print(f"   {k} = {v} B")
    else:
        print("   UNMEASURED (make basic-reloc did not report) — "
              "reporting undated assertions only")

    items = list(blocks())
    flagged = []
    for ln, txt in items:
        rows = txt.split('\n')
        bad = []
        for i, row in enumerate(rows):
            if LEDGER.search(row):
                continue                     # a cost/delta record, not a state claim
            for m in ASSERT.finditer(row):
                # 🔴 A QUOTED FIGURE IS EVIDENCE, NOT AN ASSERTION -- and the first
                # run proved it by flagging THIS TOOL'S OWN RESIDUAL, which quotes
                # all four founding defects verbatim in order to document them.
                # A checker that reddens on the write-up of the defect it was
                # built for is measuring the wrong thing.
                if row.count('"') >= 2 and row.find('"') < m.start() < row.rfind('"'):
                    continue
                fig = f"{m.group(1) or m.group(4)} B"
                lo, hi = max(0, i - QUAL_RADIUS), min(len(rows), i + QUAL_RADIUS + 1)
                near = '\n'.join(rows[lo:hi])
                if PRESENT.search(row):
                    bad.append((ln + i, fig, 'PRESENT-TENSE', row.strip()[:82]))
                elif not DATED.search(near):
                    bad.append((ln + i, fig, 'UNDATED', row.strip()[:82]))
        if bad:
            flagged.append((ln, rows[0][6:96], bad))

    print(f"\n== denominator ==\n   {len(items)} open item(s) in {TODO}; "
          f"{sum(1 for _, t in items if ASSERT.search(t))} mention a free-space figure")

    print("\n== UNDATED FREE-SPACE ASSERTIONS (gating) ==")
    if not flagged:
        print("   none — every open item that quotes a wall says WHEN it was read")
        return 0
    for ln, first, bad in flagged:
        print(f"   TODO.md:{ln}  {first}")
        for bl, fig, why, row in bad:
            print(f"       :{bl}  [{why:13s}] {fig}  |  {row}")
    n = sum(len(b) for _, _, b in flagged)
    print(f"\n   {len(flagged)} item(s), {n} figure(s).")
    print("   UNDATED       -> add the date it was taken (or `at <commit>`);")
    print("                    a dated reading then STANDS AS TAKEN.")
    print("   PRESENT-TENSE -> say \"was N B on <date>\", not \"is now N B\". A date")
    print("                    beside a present-tense claim does not retract it.")
    return 1


sys.exit(main())
