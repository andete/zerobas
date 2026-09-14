#!/usr/bin/env python3
"""Which suites type each statement, and could a kwsweep row replace them?

🎚️ Joost, 2026-09-14: *"maybe some of the kwsweep tests can replace tests in the
suites?"* -- an inversion of my own question (should suites feed the tier table),
and the better one: it keeps ONE instrument and CUTS battery time instead of
adding to it.

🔴 THIS ONLY MEASURES WHO TYPES WHAT. It cannot say a suite row is redundant --
two rows can type the same keyword and read entirely different things, which is
the whole lesson of `LEN(MKI$(1))` standing in for MKI$'s content. What it CAN do
is bound the question: a suite that types a statement only a handful of times is a
candidate to look at; one that types it hundreds of times is not.

📊 THE ANSWER, MEASURED 2026-09-14 over 47559 typed lines from 83 suites:
**THE DISTRIBUTION IS BIMODAL AND THERE IS NO MIDDLE BAND.** A suite types a
statement either HUNDREDS of times, because it IS that suite's subject
(`width-acceptance` types WIDTH 981x and SCREEN 1087x, against kwsweep's 2 rows
each), or ONCE OR TWICE, because it is APPARATUS inside a test of something else.
There is nothing in between for a sweep row to substitute for.

🎯 AND THE LOW-COUNT PAIRS ARE NOT THIN TESTS, THEY ARE NOT TESTS AT ALL. Checked
by reading the lines rather than the counts:
    deffn-acceptance types ABS once, in `30 DEF FNA(X)=ABS(0)+X` -- ABS is the
        BODY of the DEF FN under test
    ramfree-acceptance types LINE once, to CONSUME VRAM before measuring free RAM
    gicini-acceptance types SCREEN once, as `30 SCREEN 1:SCREEN 0` setup
    array-acceptance types POKE, to PLANT the bytes it then reads as an array
    banner-acceptance types PRINT, as its READOUT
Deleting any of those does not remove a test of that keyword; it breaks the test
of a different one.

🎚️ SO THE TWO INSTRUMENTS ARE ORTHOGONAL, NOT REDUNDANT. kwsweep is 1488 of the
47559 lines -- about 3% -- and it is a BREADTH instrument: every statement, once
or twice, each row designed to fail if that statement breaks. The suites are DEPTH
instruments: one statement, hundreds of times, mostly error and geometry cases.
Neither can stand in for the other, and the battery is not carrying duplicate work
that could be cut.
"""
import collections, os, re, sys
sys.path.insert(0, "tools")
sys.path.insert(0, "probes/basic")
import tier_table as tt, basic_probe_kwsweep as sweep    # noqa: E402

TSV = "build/kwcover.tsv"
WORD = re.compile(r"[A-Z][A-Z0-9]*\$?")
kws = tt.kwtable_keywords()
kwset = set(kws)

# statement -> suite -> count of typed lines naming it
by_stmt = collections.defaultdict(collections.Counter)
suite_lines = collections.Counter()
with open(TSV, encoding="utf-8", errors="replace") as fh:
    for line in fh:
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 4:
            continue
        suite, text = parts[0], parts[-1]
        suite_lines[suite] += 1
        for w in set(WORD.findall(text.upper())):
            if w in kwset:
                by_stmt[w][suite] += 1

# kwsweep's own rows per statement
sweep_rows = collections.defaultdict(list)
for r in sweep.SWEEP:
    subj = tt.stmt_subject(r[1], kwset, sweep.row_subject(r[4]))
    if subj:
        sweep_rows[subj].append(r[0])

print("=== the battery types %d keyword(s) across %d suite(s), %d lines ===\n"
      % (len(by_stmt), len(suite_lines), sum(suite_lines.values())))

# The question: for each statement, is there a suite whose ENTIRE coverage of it
# is small enough that kwsweep's rows might stand in?
cands = []
for kw in sorted(kwset):
    rows = sweep_rows.get(kw, [])
    for suite, n in by_stmt.get(kw, {}).items():
        if suite in ("kwsweep", "selftest-check"):
            continue
        cands.append((n, kw, suite, len(rows)))
cands.sort()

print("--- statements a suite types FIVE TIMES OR FEWER (the only place a sweep")
print("    row could plausibly stand in), with kwsweep's own row count ---")
shown = 0
for n, kw, suite, nrows in cands:
    if n > 5:
        break
    print("  %-9s typed %2dx by %-28s  kwsweep rows: %d" % (kw, n, suite, nrows))
    shown += 1
print("  (%d such pairs)" % shown)

print("\n--- and the other end: the ten heaviest suite/statement pairs ---")
for n, kw, suite, nrows in cands[-10:][::-1]:
    print("  %-9s typed %5dx by %-28s  kwsweep rows: %d" % (kw, n, suite, nrows))

print("\n--- per SUITE: how many lines it types, and how many statements it is the")
print("    ONLY non-kwsweep suite for ---")
only = collections.Counter()
for kw, suites in by_stmt.items():
    ext = [s for s in suites if s not in ("kwsweep", "selftest-check")]
    if len(ext) == 1:
        only[ext[0]] += 1
for suite, n in suite_lines.most_common(15):
    print("  %-28s %6d line(s)   sole source for %d statement(s)"
          % (suite, n, only.get(suite, 0)))
