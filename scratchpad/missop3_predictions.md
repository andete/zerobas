# D-MISSOP3 — predictions, PINNED BEFORE THE PROBE RAN

2026-08-26, on the tree D-EVFERR left. Walls: main p0 low 45 B, **main p1 99 B**,
sub p0 2464 B, sub p1 1622 B.

## 0. The filed justification being re-run

TODO.md:762 leaves three rows open with:

> *"Predicted not to move under the evaluator fix, and they did not — they reach
> an abort by another route."*

🔴 **That was measured on 2026-08-23, and D-EVFERR changed which deferred code
reaches the statement boundary at five factor sites three days later.** Its knife
K-EV2 showed `A$=(1+2` moving to **24** when the paren site's code changed, so
`missing.asm`'s `els_tc_common` demonstrably READS the deferred code. Whether
these three still answer 2 is a question about today's tree.

## 1. Row-by-row

| row | statement | refs | zb | confidence |
|---|---|---|---|---|
| `r.key` | `KEY1,` | 24 | **2** 🔴 | high — filed, re-verify |
| `r.lets` | `A$=` | 24 | **2** 🔴 | high — filed |
| `r.letsp` | `A$=+` | 24 | **2** 🔴 | medium — §6.1 names it, never tabulated |
| `r.midd` | `MID$(A$,2)=` | 24 | **2** 🔴 | high — filed |
| `r.keyok` / `r.letsok` / `r.middok` | well formed | 0 | 0 ✅ | controls |

## 2. The denominator TODO.md:762 names as UNMEASURED, NOT GREEN

Each row is a **required slot that ends where a value was needed**, which is the
exact shape the D-MISSOP rule calls ERR 24. So **the principled prediction is 24
on both references for every one of them** — and that is a RULE being predicted,
not ten independent guesses. Any row where the references say something else is
worth more than a row that confirms.

zerobas side: the rule has no shared implementation, so each verb answers with
whatever its own parse does. Absent LINE-style hand-written checks I expect
`Syntax error` (2).

| row | statement | refs | zb |
|---|---|---|---|
| `d.swap` | `SWAP A,` | 24 | 2 🔴 |
| `d.ongoto` | `ON 1 GOTO` | 24 | 2 🔴 |
| `d.width` | `WIDTH` | 24 | **24** ✅ (`get_byte_arg` may already) |
| `d.draw` | `DRAW` | 24 | 2 🔴 |
| `d.play` | `PLAY` | 24 | 2 🔴 (TODO.md:1569 files the refs at 24) |
| `d.open` | `OPEN` | 24 | 2 🔴 |
| `d.using` | `PRINT USING` | 24 | 2 🔴 |
| `d.inputch` | `INPUT#` | 24 | 2 🔴 |
| `d.field` | `FIELD` | 24 | 2 🔴 |
| `d.printch` | `PRINT#` | 24 | 2 🔴 |
| `d.swapok` / `d.widthok` / `d.playok` | well formed | 0 | 0 ✅ |

**Predicted: 21 rows scored, 13 DIFF.**

⚠️ **A GAP NAMED RATHER THAN DROPPED**: bare `INPUT` and `LINE INPUT` are VALID
statements that prompt and wait, so no row here can measure them — the probe
would hang, not answer. `INPUT#` is the reachable parse error in that family.
The waiting forms stay unmeasured and this line is the record of it.
