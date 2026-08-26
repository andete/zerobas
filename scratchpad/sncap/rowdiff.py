#!/usr/bin/env python3
"""D-SNCAP verification: are two runs of a probe BYTE-IDENTICAL row for row?

The tally proves a mark was never REACHED (a fallback). NOTHING in the tally
catches a mark placed too EARLY -- that captures a half-finished machine on BOTH
sides and can agree wrongly, which is the exact failure the scheduled budget
existed to prevent. This is the check with teeth: parse both runs through the
supported reader (probe_report.parse, so a layout change cannot turn it into a
line differ) and compare tag+label+values.

  python3 scratchpad/sncap/rowdiff.py BEFORE.log AFTER.log [...]

Exit 0 only if every pair is identical AND both sides parsed a non-zero,
EQUAL number of rows -- a report that shrank is not "no differences".
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "probes", "lib"))
import probe_report


def rows(path):
    txt = open(path, errors="replace").read()
    # require_footer=False: these logs carry the `make` recipe echo and (after
    # the conversion) the capture-on-signal tally around the report, and a
    # sharded lineerr log has its own footer per shard. The COUNT check below is
    # what replaces the footer's truncation guard.
    return {(r.label): (r.tag, tuple(sorted(r.vals.items())))
            for r in probe_report.parse(txt, require_footer=False)}, txt


def main():
    args = sys.argv[1:]
    if len(args) % 2:
        sys.exit("usage: rowdiff.py BEFORE AFTER [BEFORE AFTER ...]")
    bad = 0
    for i in range(0, len(args), 2):
        b, a = args[i], args[i + 1]
        rb, tb = rows(b)
        ra, ta = rows(a)
        name = os.path.basename(a)
        if not rb or not ra:
            print(f"FAIL {name}: parsed {len(rb)} before / {len(ra)} after -- "
                  f"a report with no rows cannot say anything")
            bad += 1
            continue
        only_b = sorted(set(rb) - set(ra))
        only_a = sorted(set(ra) - set(rb))
        moved = sorted(l for l in set(rb) & set(ra) if rb[l] != ra[l])
        if only_b or only_a or moved:
            bad += 1
            print(f"FAIL {name}: {len(moved)} row(s) MOVED, "
                  f"{len(only_b)} lost, {len(only_a)} new "
                  f"({len(rb)} before, {len(ra)} after)")
            for l in moved[:40]:
                print(f"     {l}\n       before {rb[l]}\n       after  {ra[l]}")
            for l in only_b[:20]:
                print(f"     LOST {l} {rb[l]}")
            for l in only_a[:20]:
                print(f"     NEW  {l} {ra[l]}")
        else:
            print(f"ok   {name}: {len(ra)} row(s), byte-identical")
    print(f"\nROWDIFF: {len(args)//2} pair(s), {bad} with differences")
    return 1 if bad else 0


sys.exit(main())
