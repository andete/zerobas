# What is every keyword's status, actually? (D-KWCOVER)

Joost, 2026-09-11: *"given that we have so many keywords still at 'no known gap'
shouldn't we identify their status first before picking up new work?"* — yes.
`make tiers --keywords` reported **105 of 159** keywords as *"no known gap (no
item, no kwsweep row — unverified)"*, and the page says in its own words that
this is not a tier. This spec is the instrument chain that replaces it, in two
stages, because the two questions have very different costs.

## 1. Stage one — EXERCISED vs UNEXERCISED (mechanical, one battery run)

🔴 **THREE SCANS OF THE PROBE SOURCES WERE WRONG BEFORE THIS EXISTED.** Matching
the probes' Python strings for BASIC scored English prose (`AND` "exercised by
125 suites", `COPY` by 32, and an EMPTY unexercised set — the tell that the
filter was the finding, not the coverage). Tightening it then LOST real rows:
`KILL "A.BAS"` keeps no token once its literal is stripped, and an English
word-boundary rule loses `FORI=0TO39:VPOKE160+I,39:NEXT`, because MSX BASIC needs
no spaces and crunches `FORI` as `FOR`+`I`. Each round produced a plausible
table [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].

So the lines are **captured, not guessed**: `omsx_repl.run_cases` is the one
chokepoint every probe types through, and with `$ZEROBAS_KWCOVER` set it appends
every typed line tagged with its suite (`tools/run_gates.py` sets the tag per
unit). `make kwcover` runs the battery with the capture armed and reports;
`tools/kwcover.py` REFUSES without a capture, because a report without one is a
guess and three of those were already wrong.

    make kwcover                 # battery + report (~8 min)
    make kwcover-report ARGS=--all

Keyword matching then mirrors `match_kw` exactly: longest first, no right
boundary, matched span consumed, BASIC string literals removed first (so
`PRINT"FOR"` types no `FOR`).

**What stage one claims.** `UNEXERCISED` is a claim: no collected suite types the
keyword at all, so nothing in the battery would notice if it broke. `EXERCISED`
is NOT "verified" — `PRINT` is in almost every readout, and `NEW`/`CLS`/`WIDTH`
are apparatus in dozens of suites.

## 2. Stage two — EXERCISED → VERIFIED or BLIND (a mutation sweep the capture makes affordable)

The honest test of "verified" is the one the tree already uses for gates: break
it and see if anything goes red [[gateblind-slice]]. Per keyword that means
disabling its handler and re-running the suites that type it — and until now
"which suites type it" was unknown, so the sweep was unaffordable. The capture
answers exactly that, and two things make it cheap:

* **Patch the ROM, don't rebuild.** The handler's address comes from
  `build/basic-reloc.sym`; writing `C3 <stmt_error>` over its entry and
  re-installing the machine is seconds, where a source knife is a ~40 s build.
* **Knife DISJOINT keywords together.** From the capture, keywords whose suite
  sets do not overlap can be disabled in the same ROM: a red suite then names
  exactly one keyword. Colouring the overlap graph batches ~159 keywords into
  far fewer runs.

A keyword whose handler can be disabled with the battery still green is **BLIND**
— that is the work list stage two produces, and each entry is one row to write.

⚠️ Not claimed: that a green sweep means the keyword is CORRECT. It means a total
failure of its handler is noticed. Behavioural depth is what the per-keyword
rows are for; this only removes the case where there is nothing at all.
