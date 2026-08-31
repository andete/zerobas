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
