# D-ONLIST — predictions, PINNED BEFORE THE PROBE RAN

2026-08-26, on `9644bf2`. Walls: main p0 low 45 B, **main p1 99 B**, sub p0
2464 B, sub p1 1622 B.

## 0. The site set, read as INSTRUCTIONS before any machine booted

`esn_nocf` (`basic/program.asm`:2146) has **FIVE** incoming `jr nz`, and they do
not mean the same thing:

| site | reached by | my reading |
|---|---|---|
| `:2091` | `esn_p1`, `cp LINENO_TOKEN` fails | no list at all, **or** a comma then a non-lineno — MALFORMED |
| `:2104` | `esn_p1`, no comma after an entry | list SHORTER than N — **LEGAL** |
| `:2129` | `esn_scan` (N=0), no entries at all | no list at all — MALFORMED |
| `:2138` | `esn_scan_lp`, no more commas | end of a real list — **LEGAL** |
| `:2143` | `esn_scan_lp`, comma then non-lineno | MALFORMED |

⚠️ **THAT COLUMN IS A READING OF THE SOURCE, NOT A MEASUREMENT.** D-EVFERR's
lesson was that reading jump sites tells you where code GOES, not which rows
REACH it — and D-MISSOP3's was that a row can agree for a reason unrelated to the
site. Every claim above is under test.

## 1. Readout

`[ERR F]` — **F is what an error code cannot say**: `ON 5 GOTO 40` and
`ON 1 GOTO 40` both end at ERR 0, and only the flag separates *fell through*
from *branched*.

* `F=0` — aborted before line 25
* `F=1` — FELL THROUGH (line 25 ran)
* `F=2` — BRANCHED to line 40

## 2. Row-by-row

| row | statement | refs | zb | site |
|---|---|---|---|---|
| `o.nolist` | `ON 1 GOTO` | `2 0` | **`0 1`** 🔴 | `:2091` — D-MISSOP3 measured the ERR half |
| `o.nolistsub` | `ON 1 GOSUB` | `2 0` | **`0 1`** 🔴 | `:2091` |
| `o.zeronolist` | `ON 0 GOTO` | `2 0` | **`0 1`** 🔴 | `:2129` — is syntax checked when N=0? |
| `o.overnolist` | `ON 5 GOTO` | `2 0` | **`0 1`** 🔴 | `:2091` — is it checked when N is past the end? |
| `o.short` | `ON 5 GOTO 40` | `0 1` | `0 1` ✅ | `:2104` — **must not move** |
| `o.zero` | `ON 0 GOTO 40` | `0 1` | `0 1` ✅ | `:2138` — **must not move** |
| `o.trail1` | `ON 1 GOTO 40,` | `2 0` | **`0 2`** 🔴 | `esn_p2` tolerates it and BRANCHES |
| `o.trail0` | `ON 0 GOTO 40,` | `2 0` | **`0 1`** 🔴 | `:2143` |
| `o.badafter` | `ON 1 GOTO 40,X` | `2 0` | **`0 2`** 🔴 | branches anyway |
| `o.ok` | `ON 1 GOTO 40` | `0 2` | `0 2` ✅ | control |
| `o.gosubok` | `ON 1 GOSUB 40` | `0 2` | `0 2` ✅ | control |

**Predicted: 11 scored, 7 DIFF.**

## 3. The rule being predicted, so one row can refute it

> **An `ON n GOTO/GOSUB` whose target list is EMPTY or MALFORMED is a
> `Syntax error` REGARDLESS of N; a list that is well formed but SHORTER than N
> falls through silently.**

That is one rule, and `o.zeronolist` / `o.overnolist` are the rows that can break
it: if the reference checks the list's syntax only on the path that actually
seeks an entry, then N=0 and N-past-the-end would answer `0 1` and the rule is
narrower than stated.

⚠️ **AND `o.trail1` IS THE ROW I LEAST EXPECT TO GET RIGHT.** A dangling comma
after a FOUND entry is the one case where zerobas does something worse than
silence — it BRANCHES — and I have no reference reading for it at all.

---

# ROUND 2 — the rule was TOO WIDE, and the refutation named the real one

**Baseline: 11 scored, 2 DIFF. My §3 rule is REFUTED on the reference side.**

| row | I predicted refs | refs ACTUALLY | |
|---|---|---|---|
| `o.zeronolist` `ON 0 GOTO` | `2 0` | **`0 1`** | ❌ |
| `o.overnolist` `ON 5 GOTO` | `2 0` | **`0 1`** | ❌ |
| `o.trail1` `ON 1 GOTO 40,` | `2 0` | **`0 2`** | ❌ zb already right |
| `o.trail0` `ON 0 GOTO 40,` | `2 0` | **`0 1`** | ❌ zb already right |
| `o.badafter` `ON 1 GOTO 40,X` | `2 0` | **`0 2`** | ❌ zb already right |

🔴 **ALL FIVE MISSES ARE THE SAME ERROR: I ASSUMED THE REFERENCE VALIDATES A
LIST IT NEVER LOOKS AT.** It does not. And **three of the five are rows where
zerobas is ALREADY CORRECT** — a fix built on the wide rule would have shipped
three regressions into currently-green behaviour. The rows that caught it are
the ones added as *"legal, must not move"* and the malformed tails I was most
confident about.

## The rule the refutation leaves

`ON 1 GOTO` is **ERR 2** and `ON 5 GOTO` is **SILENT** — and in zerobas those are
the *same instruction*, `:2091` on its first iteration. So the discriminator is
not the list at all:

> **The reference demands a line number only at the position it is about to USE.
> `Syntax error` iff the Nth position is REACHED and what is there is not a line
> number. N=0 never looks; a list that ends before position N never looks.**

In `eon_seek_nth` terms that is exactly **`DE == 1` at `:2091`** — the entry
about to be read is the one being sought — and nothing else.

| row | statement | refs | zb | what it settles |
|---|---|---|---|---|
| `o.n2trail` | `ON 2 GOTO 40,` | **`2 0`** | `0 1` 🔴 | a consumed comma COMMITS the reference to position 2 |
| `o.n5trail` | `ON 5 GOTO 40,` | `0 1` | `0 1` ✅ | position 5 is never reached, so the same comma commits nothing |
| `o.n2short` | `ON 2 GOTO 40` | `0 1` | `0 1` ✅ | no comma -> list shorter -> legal |
| `o.n2ok` | `ON 2 GOTO 50,40` | `0 2` | `0 2` ✅ | control |

**Predicted: 4 scored, 1 DIFF.** `o.n2trail` is the whole round: if it reads
`0 1` on the references then the rule is narrower still — only the FIRST
position is ever demanded — and the fix is a one-site test rather than a
`DE == 1` test.

---

# KNIFE ROUND 1 — 1 of 4, and three of the misses share ONE cause

| knife | predicted | moved | |
|---|---|---|---|
| K-OL1 | 3 rows revert to `0 1` | exactly those 3 | ✅ EXACT |
| K-OL2 | 4 rows raise | 5 moved, 4 to the wrong VALUE | 🔴 |
| K-OL3 | `o.trail1` + `o.badafter` → `2 0` | `o.badafter` ✅, `o.trail1` → **`0 1`** | 🔴 |
| K-OL4 | `o.zeronolist` → `2 0` | **NOTHING MOVED** | 🔴 |

🔴 **K-OL4 REDDENED NOTHING, WHICH IS THE TRAP, NOT THE RESULT.** All three
misses have one cause: **`esn_notlineno` is coupled to `esn_p1`'s state.** It
opens with `dec de`, and at every other site DE is already 0, so it wraps to
`$FFFF`, tests NZ, and lands back on the LEGAL exit. Pointing another jump at it
does not re-create the wide rule — it re-creates *silence*.

And **K-OL2 did not do what its own description said**: `jr nz` → `jr z` INVERTS
the test, it does not remove it, so the three already-raising rows fell through
instead of staying red. A knife whose description and whose cut disagree cannot
score its claim, however many rows it moves.

## Round 2 — the same three claims, cut so they can actually be tested

The shipped source now labels the raise point `esn_bad`, **0 B**, so a site can
ask for the verdict *past* the discriminator. Re-pinned before re-running:

| knife | cut | predicted to move |
|---|---|---|
| K-OL1 | unchanged | `o.nolist`, `o.nolistsub`, `o.n2trail` → `0 1` |
| K-OL2 | `or e` → `xor a`: the discriminator is ALWAYS true | `o.overnolist`, `o.n5trail` → `2 0` — **and only those two**, because `ON 5 GOTO 40` and `ON 2 GOTO 40` fail at `esn_p1`'s `cp ','` site instead and cannot reach this test at all |
| K-OL3 | `esn_ok`'s *"malformed: stop here"* → `esn_bad` | `o.trail1`, `o.badafter` → `2 0` |
| K-OL4 | `esn_scan`'s *"no entries at all"* → `esn_bad` | `o.zeronolist` → `2 0` |

⚠️ **K-OL2's row set is the one I got wrong last time and it is narrower than it
looks**: two rows, not four. The rows that *look* like they should move
(`o.short`, `o.n2short`) leave through a different jump.
