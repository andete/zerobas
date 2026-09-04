#!/usr/bin/env python3
r"""D-FILEDROT — re-run the row set every OPEN `TODO.md` item cites, and say
which filed divergences no longer reproduce.

🔴 THE CLASS THIS EXISTS FOR. Three times now a filed candidate had ALREADY
SHIPPED and nobody noticed, because the entry reads like a measurement and a
measurement reads like a fact:

  * gapsweep's rank 1                    -- already shipped
  * TODO's "measured page-1 candidate"   -- already shipped
  * `CVI(5)` Syntax-vs-Type mismatch     -- fixed by D-CVITM the SAME DAY the
                                            D-NGRAM15 entry filing it was written

A wall rots, a ranking rots, and so does a ROW. The only thing that does not rot
is running it, so this runs them.

⚠️ EVERY PROBE HERE IS AN EMULATOR PROBE. Serial, one at a time, refcache OFF --
a contended battery produces false verdicts and a replayed row is not a
measurement. Expect minutes each; use --skip/--limit to work in chunks.

usage: filed_row_sweep.py [--skip N] [--limit N] [--timeout S] [--list]
"""
import argparse, os, re, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODO = os.path.join(ROOT, "TODO.md")
CITE = re.compile(r"scratchpad/([a-z0-9_]+_probe)\.py")
# 🔴 THERE IS NO UNIFORM VERDICT CONTRACT ACROSS THESE PROBES, and the first
# cut of this sweep assumed there was. Measured 2026-08-31 on the first six:
#
#   catterm  rc=1  "DIFF vs references: 1/9"      summary line + rc agree
#   catusr   rc=1  "DIFF: 1/5"                    a DIFFERENT summary form
#   dupspan  rc=0  "ROW x  refs-agree  zb=same"   a third row form, no summary
#   deffn_a  rc=0  "o.alias: DIVERGENCE"          🔴 DIVERGES AND EXITS 0
#   keystr   rc=0  "k.slot1 ... 🔴 DIFF" x5       🔴 DIVERGES AND EXITS 0
#   budget   rc=0  a timing table                 no verdict concept at all
#
# So neither the exit code NOR one summary regex can score this corpus: two
# probes print divergences and exit 0, and three print rows in three shapes.
# Scan for EVERY known divergence marker AND report the rc beside it, then
# refuse to call anything clean when the two channels disagree -- naming the
# SECOND cause of green instead of trusting the first.
SUMMARY = re.compile(r"^\s*DIFF(?: vs references)?:\s*(\d+)\s*/\s*(\d+)(.*)$", re.M)
#   ngram13  rc=1  "DIFF d.body-l  cf3300=..."   a FIFTH form: LEADING `DIFF`
#   playfn   rc=0  "...  <-- DIFFER"                a SIXTH
#   ramfree  rc=1  "FAIL s.draw ... want=0"         a SEVENTH
#   reclen   rc=0  a two-column table, NO verdict word anywhere -- an EIGHTH
#                  shape that simply has no channel to read, and is reported as
#                  unparsed rather than guessed at.
MARKER = re.compile(r"(?:\U0001f534\s*DIFF\b|\bDIFF\s*$|\bDIVERGENCE\b|"
                    r"^\s*DIFF\s|\bDIFFER\b|^\s*FAIL\s)", re.M)
# every row shape seen in this corpus, not just the one the first probe used
ROWLINE = re.compile(r"(?:\b(?:SAME|DIFF|NO-ORACLE)\s*$|vg8020=|cf3300=|"
                     r"\bzb=|^\s*ROW\s|->\s*'|^\s*(?:OK|FAIL)\s)", re.M)


def open_items():
    """Yield (todo_line_no, [probe modules]) for each OPEN `- [ ]` item."""
    items, cur, start = [], [], None
    for n, line in enumerate(open(TODO, errors="replace"), 1):
        if line.startswith("- ["):
            if start is not None:
                items.append((start, cur))
            start, cur = (n, []) if line.startswith("- [ ]") else (None, [])
        if start is not None:
            cur += CITE.findall(line)
    if start is not None:
        items.append((start, cur))
    return [(n, c) for n, c in items if c]


# tools/, not scratchpad/: `scratchpad/*.txt` is gitignored, and a pinned
# adjudication set must be COMMITTED -- it lives beside the other pinned sets
# (probe-reach-allow.txt, citations-advisory-allow.txt).
KNOWN_FILE = os.path.join(ROOT, "tools", "filed-row-known.txt")


def known_rows():
    """probe -> [row labels] from the adjudication file. Rows are ';'-separated
    because two playfn labels contain commas."""
    out = {}
    for line in open(KNOWN_FILE, errors="replace"):
        line = line.strip()
        if not line or line.startswith("#") or ": " not in line:
            continue
        head, rest = line.split(": ", 1)
        rows = rest.split(" --", 1)[0]
        # 🔴 ACCUMULATE, NEVER REPLACE. This was `out[head] = ...`, so a SECOND
        # line for the same probe silently discarded the first -- and the failure
        # is invisible in the report: a pin set of the same SIZE with different
        # MEMBERS still prints "[2 known, 4 UNFILED]". Found 2026-09-04 by
        # splitting playfn's rows across their two owning entries and reading the
        # unchanged counts as "the edit did not apply".
        out.setdefault(head, []).extend(
            r.strip() for r in rows.split(";") if r.strip())
    # 🔴 Refuse-on-degenerate, same as the probe list: an empty adjudication
    # file would score every divergence NEW, which is loud but wrong the other
    # way -- and a parse failure would score every divergence KNOWN=0 silently.
    if len(out) < 5:
        raise SystemExit(f"🔴 REFUSING: only {len(out)} adjudicated probe(s) "
                         f"parsed from {KNOWN_FILE}; expected ~13.")
    return out


def score(out, state, known=()):
    """Two INDEPENDENT channels -- printed markers and exit code -- reported
    together, because on this corpus they disagree."""
    body = open(out, errors="replace").read()
    rows = len(ROWLINE.findall(body))
    marks = len(MARKER.findall(body))
    v = SUMMARY.search(body)
    n = int(v.group(1)) if v else marks
    # 🔴 ORDER MATTERS, AND THE FIRST CUT HAD IT BACKWARDS. `playfn_fixture_probe`
    # prints `<-- DIFFER` on rows this sweep's ROWLINE cannot match, so the
    # rows==0 refusal fired FIRST and buried two real divergences under
    # "measured nothing". A MARKER IS ITSELF PROOF THE PROBE MEASURED -- test it
    # before concluding the output is empty.
    if n:
        # --- adjudicate each MARKER LINE against the filed set --------------
        # A marker line naming a known row is *measured-and-known*; one naming
        # none is *measured-and-UNNOTICED* -- the sweep's whole reason to exist.
        # A known row matching NO marker line has stopped diverging: the CVI
        # shape (fixed-when-filed, entry stale), reported rather than dropped.
        mlines = [l for l in body.splitlines() if MARKER.search(l)]
        hit = set()
        fresh = 0
        for l in mlines:
            owners = [r for r in known if r in l]
            hit.update(owners)
            if not owners:
                fresh += 1
        stale = [r for r in known if r not in hit]
        adj = f"  [{len(hit)} known"
        if fresh:
            adj += f", \U0001f534 {fresh} marker line(s) UNFILED -- read them"
        if stale:
            adj += f", \u26a0\ufe0f {len(stale)} known row(s) NO LONGER " \
                   f"DIVERGING ({' '.join(stale)}) -- the CVI shape, re-run " \
                   f"and re-file"
        adj += "]"
        where = (f"{v.group(1)}/{v.group(2)}{v.group(3).rstrip()}" if v
                 else f"{marks} marker(s) in {rows} parsed line(s)") + adj
        # 🔴 The second cause of green: a probe can print divergences and STILL
        # exit 0, so a collector reading only the rc would call this clean.
        hidden = "  \U0001f534 AND EXITS 0 -- invisible to any rc-only collector" \
            if state == "rc=0" else ""
        return f"DIVERGES {where}{hidden}"
    if rows == 0:
        # 🎯 TWO DIFFERENT THINGS WORE ONE RED LABEL. "The probe measured
        # nothing" is a fault; "this probe has no verdict channel at all" is a
        # MEASUREMENT INSTRUMENT doing its job -- budget_probe prints emulated-
        # time margins, interpspeed_probe prints ratios, put3consume_probe prints
        # values under a reading note. None of them has a SAME/DIFF column to
        # adjudicate, and three permanent red lines are how a real one stops
        # being noticed.
        #
        # So a probe may DECLARE it in the pin file (`<probe>: NO-VERDICT -- why`)
        # and the declaration is what separates them. An undeclared silence stays
        # red. ⚠️ Declaring one does NOT make its rows safe: interpspeed sat here
        # for two days with `c.arith` reading `<NO OUTPUT>`, which set the filed
        # speed band 0.7x too low -- see docs/spec-basic-interpspeed.md.
        if "NO-VERDICT" in known:
            return ("--  no verdict channel BY DESIGN (declared): a measurement "
                    "instrument, not an oracle. Its ROWS still need a human.")
        return "🔴 NOTHING PARSED -- probe measured nothing, or format unknown"
    if state not in ("rc=0",):
        return f"\u26a0\ufe0f  {state} but no divergence marker in {rows} parsed line(s) -- READ IT"
    return f"clean: {rows} parsed line(s), no divergence marker"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--timeout", type=float, default=900.0)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--check-orphans", action="store_true",
                    help="report pins in filed-row-known.txt whose probe is no "
                         "longer cited by any OPEN item -- those pins can never "
                         "be validated by this sweep and go stale invisibly")
    a = ap.parse_args()

    items = open_items()
    # one entry per PROBE, carrying every open item that cites it
    by_probe = {}
    for n, mods in items:
        for m in mods:
            by_probe.setdefault(m, []).append(n)
    names = sorted(by_probe)

    # 🔴 REFUSE ON A DEGENERATE INPUT rather than print an empty clean table.
    # A regex that stops matching TODO.md's item form, or a rename of the
    # scratchpad probes, would otherwise report "nothing to re-run" -- which
    # reads exactly like "nothing rotted".
    if len(names) < 10:
        print(f"🔴 REFUSING: only {len(names)} cited probe(s) found in {TODO}.\n"
              "   The sweep has been finding ~20; this is a parse failure, not\n"
              "   a clean tree. Check the `- [ ]` item form and the citation form.",
              file=sys.stderr)
        return 2

    if a.check_orphans:
        return check_orphans()
    if a.list:
        for m in names:
            print(f"{m:28s} cited by TODO.md:" +
                  ",".join(str(x) for x in by_probe[m]))
        print(f"\n{len(names)} probe(s) cited by {len(items)} open item(s)")
        return 0

    todo = names[a.skip:]
    if a.limit:
        todo = todo[:a.limit]
    KNOWN = known_rows()
    env = dict(os.environ)
    env["ZEROBAS_REFCACHE"] = "0"          # a sweep measures, it never replays
    print(f"# {len(todo)} of {len(names)} cited probe(s), serial, refcache OFF, "
          f"{a.timeout:.0f}s each")
    for i, m in enumerate(todo, 1):
        rel = f"scratchpad/{m}.py"
        out = f"/tmp/zerobas/rot_{m}.out"
        t0 = time.time()
        with open(out, "w") as fh:
            try:
                rc = subprocess.call([sys.executable, os.path.join(ROOT, rel)],
                                     stdout=fh, stderr=subprocess.STDOUT,
                                     cwd=ROOT, timeout=a.timeout, env=env)
                state = f"rc={rc}"
            except subprocess.TimeoutExpired:
                state = "TIMEOUT"
        print(f"{i:3d}/{len(todo)}  {m:28s} {state:9s} {time.time()-t0:6.1f}s  "
              f"{score(out, state, KNOWN.get(m, ()))}", flush=True)
        print(f"          cites TODO.md:" +
              ",".join(str(x) for x in by_probe[m]), flush=True)
    return 0


def check_orphans() -> int:
    """🔴 THE PINS THIS SWEEP CANNOT REACH. Its corpus is the probes cited by
    OPEN items; when an item closes, its probe leaves the corpus and its pin
    stays in filed-row-known.txt, unvalidatable. reqcomma_probe sat stale for a
    day that way -- `g.field` agreed on both machines while the pin still
    claimed it as a known divergence, and the scoreboard built from these pins
    counted it as outstanding correctness debt.
    [[a-ranked-candidate-rots-like-a-wall]]"""
    corpus = {m for _, mods in open_items() for m in mods}
    pinned, orphans = [], []
    for ln in open(KNOWN_FILE):
        m = re.match(r"([a-z0-9_]+_probe):", ln.strip())
        if not m:
            continue
        pinned.append(m.group(1))
        if m.group(1) not in corpus:
            orphans.append(m.group(1))
    print(f"pins: {len(pinned)}   sweep corpus: {len(corpus)} probe(s)")
    if not orphans:
        print("  no orphans — every pin names a probe this sweep still runs")
        return 0
    print(f"🔴 {len(orphans)} ORPHANED PIN(S) — cited by no OPEN item, so this "
          f"sweep never runs them and cannot see them go stale:")
    for o in orphans:
        print(f"     {o}")
    print("  Re-run each by hand; if its rows now agree, the pin leaves the set.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
