# D-PLAYOP — predictions, PINNED BEFORE THE PROBE RAN

2026-08-26, on `2258c6b`. Walls: main p0 low 45 B, **main p1 85 B**.

## 0. The filed claims, which are what gets run first

`TODO.md`:1711, filed 2026-08-22 by D-DUPSPAN §6.3:

* *"`PLAY` and `PLAY:PRINT 1` → **ERR 24** on both"*
* *"`PLAY ,"E"` → ERR 2 on both and here"*
* *"**TWO of `pl_syntax`'s four call sites move, not four** — the `or a` and
  `COLON` tests, not the `','` one"*
* *"The fourth (a 4th voice string) is **UNMEASURED** — do not assume it into
  either half"*
* *"`pl_syntax`'s header cites the VG-8020 for the ERR-2 claim; that citation is
  right for one site and wrong for two"*

## 1. 🔴 THE FILING COUNTS INSTRUCTIONS AND `pl_voice` IS A LOOP

`basic/play.asm:74` is `jr pl_voice`, so the three entry-side tests at `:42`
(`or a`), `:44` (`cp COLON`) and `:46` (`cp ','`) are re-entered **after every
comma**. Each therefore has **two entry conditions** — the FIRST voice and a
SUBSEQUENT one — and the filing's "two of four call sites move" is a claim about
instructions, not about rows.

That is the D-ONLIST shape exactly: *the same instruction answered differently
depending on how it was reached*. Every site gets both rows here.

| row | statement | site | entry | refs | zb |
|---|---|---|---|---|---|
| `p.bare` | `PLAY` | `:42` | first voice | **24** | 2 🔴 |
| `p.colon` | `PLAY:PRINT1` | `:44` | first voice | **24** | 2 🔴 |
| `p.comma` | `PLAY,"E"` | `:46` | first voice | 2 | 2 ✅ |
| `p.trail` | `PLAY"A",` | `:42` | **subsequent** | **24** | 2 🔴 |
| `p.trailcolon` | `PLAY"A",:PRINT1` | `:44` | **subsequent** | **24** | 2 🔴 |
| `p.dblcomma` | `PLAY"A",,"C"` | `:46` | **subsequent** | 2 | 2 ✅ |
| `p.four` | `PLAY"A","B","C","D"` | `:73` | — | 2 | 2 ✅ |
| `p.ok` | `PLAY"A"` | — | control | 0 | 0 ✅ |
| `p.ok3` | `PLAY"A","B","C"` | — | control | 0 | 0 ✅ |
| `p.empty` | `PLAY""` | — | control (header: empty is allowed) | 0 | 0 ✅ |
| `p.num` | `PLAY 5` | — | control (header: Type mismatch) | 13 | 13 ✅ |

**Predicted: 11 scored, 4 DIFF.**

## 2. The rule being predicted, so a row can refute it

D-MISSOP3's refined rule, applied to a verb it was not derived from:

> **A required slot that ends where a VALUE was needed is `Missing operand`
> (24); an EMPTY operand terminated by `,` is `Syntax error` (2).**

`p.trail` / `p.trailcolon` are the rows that can break it: if the reference
treats a TRAILING comma as *"the list is finished"* rather than *"another voice
was promised"*, they read `0` and the rule does not reach the loop's second
iteration.

⚠️ **`p.four` IS THE ONE THE FILING SAYS NOT TO ASSUME**, and I am predicting 2
for it anyway — a prediction is not an assumption as long as it is written down
before the run and scored after.

⚠️ **NOT MEASURED HERE: whether PLAY QUEUES ANYTHING BEFORE RAISING.** The seam
work found wrong ORDERING at SWAP and PAINT (effect-then-raise vs
raise-then-effect); this probe reads the error code only, so a
`PLAY"A",` that plays voice A and then raises would be indistinguishable from
one that raises first. Named, not covered.
