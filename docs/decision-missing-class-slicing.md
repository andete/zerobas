<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# The MISSING class — slicing, cost, and two scope forks

**Status:** PROPOSAL, 2026-07-27. **Awaiting sign-off (D-MC-1 … D-MC-4).**
Measurement input:
[`missing-vg8020-characterization.md`](missing-vg8020-characterization.md).
Roadmap item: [`TODO.md`](../TODO.md) "Keyword-completeness gaps", the
**MISSING (6)** bullet.

The SILENT-GAP class is empty (`2facfc0`). This is the next item in the keyword
arc, in the order the roadmap already set.

## 1. What the measurement changed about the plan

The roadmap costed this class on the assumption that the only per-keyword price
is main-ROM dispatch glue (5 B/token), because `kwtable.inc` entries and leaf
compute live in `sub.rom` where there is ≈8 KB free. **That is right about the
glue and wrong about the bodies.** These five are not leaf compute — four of
them touch interpreter-core state (the cursor, the variable table, the line
executor), and the characterization turned each into a real surface:

| word | what the measurement showed it must do |
|---|---|
| `LOCATE` | 3 optional args, byte-domain check → `Illegal function call`, then **clamp to `WIDTH`**, `Missing operand` on omission, and **apply args 1–2 before rejecting arg 4** |
| `SWAP` | resolve **two lvalues** (scalar or array element), require **exact type equality**, exchange N bytes, and reject when the **second** operand does not exist |
| `TRON`/`TROFF` | a flag, plus a **hook in the line executor** that prints `[nnn]` before every line entry — including loop re-entry and jump targets |
| `MOTOR` | parse `ON`/`OFF`/bare and call `STMOTR` |

## 2. Cost, measured against comparable statements already in the tree

Whole-statement spans from `build/basic-reloc.sym` (entry point to the next
`ex_*` entry point), so these are real implementations of comparable shape, not
guesses:

| analogue | measured | why it is the analogue |
|---|---|---|
| `ex_color` | **100 B** | three optional comma-separated arguments, the exact `LOCATE` parse shape (with *no* bound check and *no* clamp) |
| `ex_screen` | 86 B | one numeric argument with a range check |
| `ex_let_arr` | 151 B | resolves an array-element lvalue and stores |
| `ex_let` | 56 B | resolves a scalar lvalue and stores |
| `ex_key` | 39 B | small statement with an `ON`/`OFF` decode |
| `ex_width` | 40 B | one byte argument written to `LINLEN` |

Estimates, stated as ranges because they are estimates:

| word | estimate | reasoning |
|---|---|---|
| `LOCATE` | **110–135 B** | `ex_color`'s 100 B parse + byte-domain check + `WIDTH` clamp + `Missing operand` |
| `SWAP` | **90–130 B** | two lvalue *address* resolutions (the existing machinery stores, it does not hand back an address), a type-equality test, an N-byte exchange |
| `TRON`/`TROFF` | **50–75 B** | the flag pair is `ex_key`-sized; the line-executor hook plus a decimal line-number emit is the rest |
| `MOTOR` | **25–40 B** | see §3 — smaller than it looks |
| dispatch glue | **25 B** | 5 statement tokens × 5 B in the `exec_stmt` chain |
| **total** | **300–405 B** | |

**Page 1 has 311 B free** (clean `make basic-reloc`, `f293cff`; low region 11 B).

**So this slice does not fit.** Even the optimistic end consumes essentially the
whole budget, and the pessimistic end overruns by ~95 B. This is exactly what
the roadmap predicted: *"the MISSING-class words are what will block"* on the
deferred D-KW-2 lever.

## 3. `MOTOR` is nearly free, and its open question is already answerable

[`tape/tape.asm:175`](../tape/tape.asm:175) already implements **`STMOTR`
(`$00F3`)** with the MSX convention — `A=0` stop, `A=$FF` toggle, otherwise
start — because C-BIOS ships no motor routine and the tape patch had to supply
one. That maps 1:1 onto the three measured forms:

| BASIC | `STMOTR` A |
|---|---|
| `MOTOR` (bare) | `$FF` (toggle) |
| `MOTOR ON` | `1` |
| `MOTOR OFF` | `0` |

The body is a three-way parse and a `call`. It also retires open question **O-2**
from the characterization ("does the relay actually close?"): we own both sides,
so the PPI port-C bit-4 write is checkable at the emulator level rather than
being an article of faith about a screen scrape.

## 4. D-KW-2, the `exec_stmt` dispatch table — now the funding lever

Measured independently on the current tree, confirming the roadmap's estimate:

```
exec_stmt chain: 69 entries -- 138 B of `cp` + 207 B of branches = 345 B
table form:      69 x 3 B (db token, dw addr) + a ~16-24 B search loop = 223-231 B
                                                            saves 114-122 B
```

With D-KW-2 landed first, page 1 goes to **≈425–433 B** free and the five words
land with 20–130 B of margin. It also drops the per-word glue from 5 B to 3 B,
so the slice's own glue falls 25 B → 15 B.

Two caveats, stated rather than discovered later:

- **Three entries are not plain token compares** and need a home in the table
  design: `cp '_'` (a character, not a token), the `REM`/`ELSE` pair that share
  a target, and the `IF ROM_BASE`/`IF G6_RESIDENT`/`IF G7_RESIDENT`/`IF
  G8_RESIDENT` conditional-assembly blocks. A table built with `IF` guards
  around individual entries is fine; the search loop must not assume a fixed
  count.
- **The chain is currently an ordering optimisation.** Hot statements sit early
  and cost fewer compares; a linear table search is uniform. `PRINT` is ~35
  entries in today, so a uniform search is a wash-to-better for it — but this
  should be *stated* in the D-KW-2 spec rather than assumed, since `exec_stmt`
  runs once per statement.

Other levers, for completeness: the `fat_rand_*` clone collapse (~28 B, and the
clone-collapse well is otherwise dry), and the `ON`/`OFF`/`STOP` decode share
flagged in `spec-traps-t5-interval` §4.3 — **6 decode sites exist today**
(`program.asm` ×4, `graphics.asm`, `screen.asm`) and `MOTOR` would be a 7th, so
that share is now slightly more attractive than when it was deferred.

## 5. The forks that need your call

### D-MC-1 — fund with D-KW-2 first, or slice smaller?

- **(a) D-KW-2 first, then all five as one slice.** Lands the dispatch table as
  its own change (with its own gate: every existing statement still dispatches),
  then the five words in one go. Highest total work, but ends with ~425 B free
  *before* the slice and real breathing room after — which matches the standing
  preference for bank headroom over per-iteration scouting.
- **(b) Slice the words and take the space as it comes.** `MOTOR` + `TRON`/
  `TROFF` (~75–115 B) fit today. `LOCATE` alone (~110–135 B) fits today. `SWAP`
  would then be the one that blocks, and D-KW-2 happens anyway — later, under
  pressure, which is the situation the standing preference exists to avoid.
- **(c) Evict bodies to `sub.rom` instead.** `LOCATE` calls `eval`, so it is
  page-1-evictable only ([`page0-tenant-eval-eviction-constraint`]). This trades
  the dispatch-table work for tenant work and does not reduce total effort.

**Recommendation: (a).** D-KW-2 is a prerequisite the roadmap already
identified, the number is now measured twice, and it is the only option that
leaves the tree with headroom rather than at the wall.

### D-MC-2 — what to do about D-MISS-1 and D-MISS-2

The calibration battery found two live defects in code that is not under test
(the fourth slice running to do so). **Neither is in the MISSING class and
neither is caused by it.**

- **D-MISS-1** — numeric → string assignment raises `syntax error` instead of
  `Type mismatch`, in every form (7 rows), while the numeric-lvalue mirror is
  already correct. One clean cause: the string-lvalue assignment path never
  type-checks its RHS. Small, well-characterized, and `ON ERROR` currently sees
  the wrong code. **Recommend folding into this slice.**
- **D-MISS-2** — the string engine's argument-domain checks are largely absent:
  `CHR$`/`LEFT$`/`RIGHT$`/`MID$` accept out-of-range arguments silently and
  compute a wrong answer, while `STRING$`/`SPACE$`/`ASC` correctly raise. There
  are also **two** reference errors, not one (`Illegal function call` in byte
  range, **`Overflow`** beyond int16). This is 4+ functions, a shared domain
  check, and a second error path. **Recommend its own slice** — it is a
  string-engine change with a real surface, and bolting it onto a
  statement-dispatch slice would blur two gates. It should be recorded as a new
  roadmap item immediately, because these are silent wrong answers shipping
  today.

### D-MC-3 — `DEF FN` stays out

Confirming the existing position: `DEF FN`/`FN` is an arc (definition table,
argument binding, re-entrant evaluation, 200–400 B), not part of this slice.

### D-MC-4 — the two open questions to close during implementation

- **O-1**, `LOCATE`'s row clamp target, is genuinely unmeasured (§7 of the
  characterization): printing near the bottom scrolls before the scrape runs, so
  rows 22/23/24 all read as row 20. It must be settled with a scroll-free
  readout **before** the clamp is written, not after.
- **O-3**, the `cursor` third argument's effect, is invisible to a name-table
  scrape. Acceptance is measured; behaviour is not. Propose implementing it as
  accepted-and-ignored, **documented as a deviation**, unless a VDP-level readout
  turns out to be cheap.

## 6. What is already done

- `probes/basic/basic_probe_missing.py` + `make missing-characterize`
  (`missing-acceptance` for the `--gate` form) — 175 cases, 8 batteries.
- The full surface measured and recorded, boot-per-case.
- Three apparatus defects found and fixed before they reached a conclusion; two
  of them had already produced wrong readings (§2 and §2.1 of the
  characterization). The `MAX_ECHO` startup guard makes the worst of them —
  a row that AGREES while measuring nothing — impossible rather than unlikely.
