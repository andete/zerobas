# D-PUT3SLOW — the third `PUT` does not hang. It is slow, and the step made it look fatal.

*2026-09-02. Corrects [`docs/spec-basic-put3.md`](spec-basic-put3.md) and the
`TODO.md` item it backs. Probe:
[`scratchpad/dskfslow_probe.py`](../scratchpad/dskfslow_probe.py).*

## 1. What was filed

> 🔴 **THE THIRD `PUT` OF A SESSION HANGS ZEROBAS, UNTRAPPABLY — AND A
> RANDOM-ACCESS WRITE LOOP IS AN ORDINARY MSX BASIC PROGRAM.**

Characterised over two days and many rows: it is the PUT count and nothing else;
cumulative across the session; `CLOSE` + `CLEAR` + reopen does not reset it; not
a trappable error, because a live handler never runs.

**Every one of those readings was taken at a 2.5-second step.**

## 2. The one test nobody ran

`step` is how long the harness waits after typing a line before typing the next.
A statement that needs longer than `step` has not finished when the next line
arrives — and the reading is a blank screen. **"Hung" and "slow" are the same
observation at a fixed step.** Same program, same machine, only the wait changes:

| row | 2.5 s (default) | 5 s | 10 s | 90 s |
|---|---|---|---|---|
| 3 PUTs, then `LOF(1)` | *blank* | **128** | **128** | **128** |
| 4 PUTs, then `LOF(1)` | *blank* | **128** | **128** | **128** |
| the filing's own `LSET`+`STRING$`+`PUT` ×3 shape | *blank* | **OK** | **OK** | **OK** |
| `PUT` then `DSKF(0)` | *blank* | **706** | **706** | **706** |

**Nothing hangs.** The answers are also *correct* — `706` is what the CF-3300
returns, and `128` is the right `LOF`.

That also dissolves "untrappable", which was the most alarming part of the
filing: no handler runs because **there is no error**. The program is still
running.

## 3. But the divergence is real — it is PERFORMANCE

The obvious next worry is that the probe simply gave the two machines different
budgets, because it does: `SIDES` sets **cf3300 `step=4.5` and zb `step=2.5`**.
An operation costing between those two would read as "reference fine, zerobas
dead" with no defect at all.

**Controlled:** the CF-3300 was re-run at zerobas's own 2.5 s step and passes
every row. So the asymmetry did not manufacture this. zerobas needs more than
2.5 s where the reference needs less.

Bounded, not pinned: **> 2.5 s and < 5 s** for the three-PUT sequence.

## 4. Two mechanisms proposed and both refuted

* **A per-`PUT` cluster leak** (each write extending the chain, so each
  `frnd_locate` walk is longer than the last) would explain a *growing* cost.
  **Refuted:** `DSKF` after 1, 2 and 3 writes reads **706 / 706 / 706**, on both
  machines. The chain does not grow.
* **A stale cache key** — `fat_count_free` documents caching FAT sectors "keyed
  by `FWR_FIRST`", and `FWR_FIRST` is the *file's first cluster*, which
  `frnd_locate` writes during a `PUT`. One RAM cell, two meanings. **Refuted by
  reading the body:** it initialises `FWR_FIRST` to `$FFFF` on entry, so it
  inherits nothing.

⚠️ **AND ONE CLAIM I AM NOT MAKING.** It is tempting to say "the third `PUT` is
individually slower than the first two", since 1 and 2 pass at 2.5 s and 3 does
not. That does not follow: the harness types at fixed intervals, so three writes
of ~2.4 s each overrun *cumulatively* without any one of them growing. Whether
the per-`PUT` cost is flat or rising is **unmeasured**, and the leak refutation
above removes the only mechanism proposed for rising.

## 5. What this changes

The item drops from "ordinary programs hang untrappably" to "random-access
writes are slower than the reference, by at least ~2× on this sequence". Still
worth fixing — a write loop that is twice the reference's cost is a real defect
against a faithful-implementation charter — but it is **not** the correctness
emergency the filing described, and the `NEXT` step it named ("find what the
third `PUT` consumes") was chasing a resource that is not being consumed.

🔴 **THE GENERAL LESSON, AND IT COST TWO DAYS OF CHARACTERISATION.** A blank
screen is not a finding; it is the *absence* of one, and it has at least three
causes — the machine died, the machine is slow, or the probe cannot read what it
said. This tree has now been bitten by all three in one day: `<UNREADABLE>`
(D-LSETTM §5, D-PUT3CONSUME), a dead machine cached as a reading (D-SCRAPEMODE),
and now a slow one filed as a hang. **Vary the step before believing a blank.**
[[an-unnamed-outcome-reads-as-no-outcome]]
[[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]]
