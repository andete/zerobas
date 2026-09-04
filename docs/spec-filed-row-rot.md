# D-FILEDROT — re-run every filed row, and seven probes turn out to diverge at rc 0

*2026-08-31. Instrument `scratchpad/filed_row_sweep.py`. Opened by picking up one
stale `TODO.md` item and finding it had been fixed the day it was filed.*

**No ROM change.** The output is a denominator, one closed item, one corrected
probe, and one filed defect class.

## 1. The item that opened it

`TODO.md` filed, on 2026-08-31: *`CVI(5)` reads `Syntax error` here and
`Type mismatch` on the CF-3300*, marked 🤖 AUTONOMOUS with the row named.

Run first, per the standing rule that a filed claim is re-measured before it is
built on — **refcache off, both sides `ERR 13`**. `fef3d69` (D-CVITM) had fixed
it **the same day the entry was written**, and had found a third wrong
disposition (`CVI("A")`) while it was in there.

That is the **third** time a filed candidate had already shipped, after
gapsweep's rank 1 and TODO's "measured page-1 candidate". A one-line close would
have set up the fourth.

## 2. A stale entry and a mis-scored row kept each other alive

The interesting part is not that the entry was stale. It is that
`scratchpad/ngram15_probe.py` **went on printing `b.cvi … DIFF` after the fix
landed**, for a completely different reason:

| | VG-8020 | CF-3300 | zerobas |
|---|---|---|---|
| `b.cvi` = `CVI(5)` | `ERR 5` | `ERR 13` | `ERR 13` |

`CVI` is a Disk BASIC verb; the cassette-only VG-8020 answers *Illegal function
call* to every form of it. The probe **already excluded `g.cvi` for precisely
this reason** and its own comment block spelled the reason out — then scored
`b.cvi` against both references anyway.

> 🔴 **THE ROW SAID THIS TREE WAS WRONG WHILE IT AGREED WITH THE ONLY REFERENCE
> THAT CAN ARBITRATE.** A stale entry explained a live `DIFF`, and a live `DIFF`
> corroborated a stale entry. Neither would have survived alone.

`b.cvi` joins `g.cvi` in `NO_ORACLE`; the probe is now **0/12 DIFF, rc 0**.

## 3. So run them all

`scratchpad/filed_row_sweep.py` re-runs the row set behind **every open TODO
item that cites one** — 18 probes across 16 items, serially, refcache off,
because a contended battery produces false verdicts and a replayed row is not a
measurement.

It **refuses** if it finds fewer than 10 cited probes: a regex that stops
matching the item form would otherwise print an empty table, and an empty table
reads exactly like *nothing rotted*.

## 4. The denominator

| | |
|---|---|
| probes cited by open items | **18** |
| **diverge** | **14** |
| …of those, **invisible to an rc-only collector** | **7** |
| clean | 2 |
| no verdict channel at all | 2 |

The seven that print divergences and exit 0: `deffn_alias_probe`,
`keystr_probe`, `ntwall_probe`, `onerrarm_probe`, `open2_probe`,
`playfn_fixture_probe`, `trapsvc_probe`.

## 5. What is NOT owed: "make them exit 1"

Several of the seven are divergences this project has **decided not to fix** —
`keystr_probe` is the NOT-THIS-ONE `KEY n,"str"` item, blocked on ~160 B. Their
rc 0 is not obviously a bug; it may be the author saying *measured, known,
declined*.

The defect is that **a probe cannot tell that apart from "measured and nobody
noticed"**, and neither can any collector. What is owed is a convention that
separates the two. Filed in `TODO.md`, 🤖, because the sweep settles the
denominator but the convention is a design call.

## 6. The instrument was wrong first, three times

Worth recording, because the sweep exists to catch instruments that hand you a
plausible table:

1. **It assumed a verdict contract.** There is none. The 18 probes use **eight**
   output shapes — trailing `SAME`/`DIFF`, leading `DIFF `, `🔴 DIFF`,
   `DIVERGENCE`, `refs-agree zb=same`, `<-- DIFFER`, `FAIL row … want=`, and a
   bare two-column table with no verdict word anywhere — and **two rc
   conventions**. The first cut scored three of the first six wrong.
2. **It stated a row count it could not derive.** The regex matches *lines*; a
   row may span several or share one. Relabelled "parsed line(s)", because a
   wrong denominator is the failure this whole document is about.
3. **It refused before it checked.** `playfn_fixture_probe` prints `<-- DIFFER`
   on lines the row regex cannot match, so the `rows == 0` refusal fired first
   and buried two real divergences under *measured nothing*. **A marker is
   itself proof the probe measured** — test it before concluding the output is
   empty.

The fix in each case was the same: report **markers and exit code as
independent channels**, and refuse to call anything clean when they disagree —
naming the second cause of green rather than trusting the first.

## 7. The lesson

**A row rots like a wall.** An entry that names a probe, a row and an expected
answer reads like a measurement, and stays readable long after it stops being
true — and the probe that would contradict it can be mis-scored in a way that
agrees with it instead.

## 8. The convention (landed same day): an adjudication file, not an exit code

§5 said what is *not* owed. What landed instead:
[`tools/filed-row-known.txt`](../tools/filed-row-known.txt) pins, per
probe, the divergent rows a filed TODO item **owns** — each named by the owning
entry's *heading*, because this same session watched TODO line numbers shift
twice. The sweep adjudicates every marker line against the set:

- a marker line naming a known row → **measured-and-known** (`[N known]`);
- a marker line naming none → **`🔴 UNFILED — read them`**, the sweep's whole
  reason to exist;
- a known row matching no marker line → **`⚠️ NO LONGER DIVERGING`** — the CVI
  shape of §2, fixed-when-filed, reported instead of silently dropped.

Measured on all 18 saved outputs: **0 unfiled, 0 stale** — today, every
divergence in the corpus is owned by an entry. That green was then falsified by
planting both directions on the same output: dropping `gos.leak` from
`trapsvc_probe`'s known set reads UNFILED; adding a ghost row reads
NO-LONGER-DIVERGING; the unmodified control reads neither. And the loader
refuses below 5 parsed probes, because an unparseable adjudication file would
otherwise score every divergence silently un-adjudicated.

The set is pinned; the judgement is not — the same shape as
`probe-reach-allow.txt` and the citation advisories.

## D-FILEDPIN (2026-09-04) — sixteen unfiled divergences, and a loader that hid pins

Run after two open items in a row turned out to be stale or to have their only
coverage attached to the stale entry. **15 probes, 12 open items, 0 orphan pins.**

**0 rows have stopped diverging** — nothing in the corpus is fixed-when-filed
today. But three probes carried divergences no entry claimed:

| probe | unfiled | what they were |
|---|---|---|
| `keylist_probe` | 6 | **debt this session created** — D-KEYSCOUT2's rows, measured and written into the entry's prose an hour earlier, never pinned |
| `dupopen_probe` | 6 | **filed in prose, never pinned** — D-DUPOPEN names all six by row in the entry, and the sweep reads *this file*, not prose. Unfiled for two days. |
| `playfn_fixture_probe` | 4 | two more of the same PLAY transient, plus two rows a *different* entry owns |

### 🎯 One probe's DIFF set can span two filed items

`playfn_fixture_probe`'s six differing rows are not one finding. Four are the
`PLAY(n)` start-up transient — and `empty string, no delay` is the sharpest of
them, because there is nothing to play and the reference *still* marks voice 1
active. The other two are `width: TIME for FOR 20/50`, which are **`TIME`
readings** (2 vs 6, 4 vs 14) owned by the interpreter-speed entry, not PLAY
behaviour at all.

🔴 **And 4 vs 14 is ~3.5×, above that entry's filed 2.5–3.1× band** even allowing
`TIME`'s ±1 quantisation on small integers — worth re-reading when it is priced.

### 🔴 The loader replaced pins instead of accumulating them

Splitting those rows across their two owners meant writing a second
`playfn_fixture_probe:` line. `known_rows()` built `out[head] = rows`, so the
second line **silently discarded the first**.

What makes it worth writing down is how it reads: the pin set changed *members*
but not *size*, so the report still said **`[2 known, 4 UNFILED]`** — the same
numbers for a different reason. I first read that as "the edit did not apply".
The loader now `setdefault(...).extend(...)`, and the file carries a one-line-per-
probe warning; but the durable fix is that a duplicate can no longer lose data.

### ⚠️ Three of fifteen probes are unreadable to this sweep

`budget_probe`, `interpspeed_probe` and `put3consume_probe` report **`NOTHING
PARSED — probe measured nothing, or format unknown`**. That is 20 % of the corpus
the sweep cannot adjudicate at all, and it is *not* the same as "clean": the
refusal is honest, but a probe it cannot read is a probe whose rows can rot
invisibly. `playfn_fixture_probe` is a near miss of the same kind — its markers
are found but its row *names* are not (`6 marker(s) in 0 parsed line(s)`), which
works only because adjudication does substring containment on the marker line.

### ⚠️ And the sweep is structurally blind outside `scratchpad/`

`CITE` matches `scratchpad/([a-z0-9_]+_probe)\.py`. A probe promoted into
`probes/basic/` — as `catterm`, `catusr` and `pusing` were this session — cannot
enter this corpus even if an open item cites it. That is *correct* for those
three, because each is now collected by the battery as a gate, which is stronger.
It is a hazard for any future promotion that does **not** get a gate.

## D-SPEEDHOLE (2026-09-04) — the three unparseable probes, and what one of them was hiding

D-FILEDPIN recorded that `budget_probe`, `interpspeed_probe` and
`put3consume_probe` report `🔴 NOTHING PARSED`. Reading them settles what that
means — and finds a published number that was wrong because of it.

### They have no verdict channel, and that is not the same as measuring nothing

All three are **measurement instruments**: emulated-time margins, `TIME` ratios,
cluster/LOF values under an explicit `read:` note. None has a `SAME`/`DIFF`
column to adjudicate. The old label conflated that with a probe that genuinely
produced nothing, and **three permanent red lines are how a real one stops being
noticed.**

A probe may now declare it — `<probe>: NO-VERDICT -- why` in the pin file — and
an *undeclared* silence stays red. The declaration says only "there is no verdict
to read here"; it explicitly does not say the probe's rows are fine.

### 🔴 Which matters, because one of them was hiding a wrong published number

`interpspeed_probe`'s seventh row read `<NO OUTPUT>`:

    FOR I=1 TO 2000:X=I*2+1:NEXT     cf3300 1004   zb 3826   3.81x

zerobas needs ~64 emulated seconds for it and the probe's budget was 60. So the
row never entered any table — and it is the **worst ratio in the set**, so its
absence pulled the published ceiling from 3.8× down to **2.5–3.1×**. The
apparatus was choosing the headline of `docs/spec-basic-interpspeed.md`.

Three separate things kept it invisible, and each is a named failure shape here:

1. **A missing measurement prints like a row with nothing to say** — `<NO OUTPUT>`
   in a column, next to six rows that reported.
2. **The probe was unadjudicated**, because the sweep cannot parse it — so
   nothing ever asked why one row was blank.
3. **A corroborating reading existed and was not connected**:
   `playfn_fixture_probe`'s `width: TIME` rows independently read ~3.5×, above the
   published band, and sat unpinned until D-FILEDPIN attached them to that entry
   an hour before this was found.

The default budget is 150 s now and all seven rows report. Emulated time runs far
above real time, so the wide budget is nearly free — **the narrow one bought
nothing and cost the conclusion.**
