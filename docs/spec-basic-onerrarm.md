# D-ONERRARM — `ON ERROR GOTO <non-line>` is untrappable on both references

*2026-08-29. Probe `scratchpad/onerrarm_probe.py`. **Measurement only — no code
change.** 12 rows, 4 DIFF, and **two hypotheses refuted**.*

## 1. What D-NGRAM10 found, and what it did not

One row: `ON ERROR GOTO A` reads `<Syntax error>` **untrapped** on a VG-8020 and
a CF-3300, and `ERR 2 AT 30` — **trapped** — on zerobas. Pre-existing (HEAD
gives the same reading). It was filed with a guess attached: *"the references
appear to drop the current handler before parsing the new target."*

**A guess in a filed item is an unrun claim.** This ran it.
[[a-justification-parenthesis-is-an-unrun-claim]]

## 2. Walking the statement's own parse, stage by stage

`ex_on_error` parses `ERROR_TOKEN | GOTO_TOKEN | $0E lo hi | (resolve the line)`,
and each stage can fail. A handler is always armed when these run — line 10 of
the fixture is `ON ERROR GOTO 900`.

| stage | row | VG-8020 | CF-3300 | zerobas | |
|---|---|---|---|---|---|
| 1 · GOTO token wrong | `ON ERROR PRINT` | ERR 2 AT 30 | ″ | ERR 2 AT 30 | **trapped, all three** |
| 2 · operand not `$0E` | `ON ERROR GOTO A` | `<Syntax error>` | ″ | **ERR 2 AT 30** | DIFF |
| 2 · operand not `$0E` | `ON ERROR GOTO "X"` | `<Syntax error>` | ″ | **ERR 2 AT 30** | DIFF |
| 3 · line undefined | `ON ERROR GOTO 12345` | ERR 8 AT 30 | ″ | ERR 8 AT 30 | **trapped, all three** |

🔴 **HYPOTHESIS 1 REFUTED — it is not "disarm before parsing".** Stage 1 fails
*earlier* in the same statement and traps on every side; stage 3 fails *later*
and traps too. If the handler were dropped up front, all three stages would be
untrapped. **Only the operand stage differs.**

## 3. The second hypothesis, and its discriminator

If the references never *ran* the statement — MSX BASIC crunches
`ON ERROR GOTO <number>` and might reject a non-numeric operand at
**tokenisation**, in direct mode — then "untrapped" would not be about trapping
at all. A rejected line is simply absent, and the program runs on.

| row | VG-8020 | CF-3300 | zerobas |
|---|---|---|---|
| `CLS : ON ERROR GOTO A : B=9` → print `B` | `<Syntax error>` | ″ | ERR 2 AT 30 |
| `CLS : ON ERROR GOTO "X" : B=9` → print `B` | `<Syntax error>` | ″ | ERR 2 AT 30 |
| 🟢 `CLS : ON ERROR GOTO 900 : B=9` → print `B` | **9** | **9** | **9** |

🔴 **HYPOTHESIS 2 REFUTED.** A line rejected at entry would leave `B=9` to run and
the row would read **9** — which the control shows this shape does report when
the program runs through. The references report the message and **no value**,
which is what an *aborted* RUN looks like. The line was stored, executed, and
raised untrapped.

## 4. What is actually established

Both references make a bad `$0E` operand in `ON ERROR GOTO` **untrappable**,
while the wrong-token stage before it and the undefined-line stage after it both
trap normally. zerobas traps all three. That is a **one-stage** difference, not a
disarm-ordering one, and the shape of any fix has to reproduce exactly that
asymmetry.

⚠️ **Not fixed here, and the cost is why.** `req_lineno` (D-NGRAM10) is now shared
by four verbs and only `ON ERROR GOTO` wants this exit, so an untrappable raise
means a second entry point or a flag — against 348 B of page 1. And "untrapped"
has to be *expressible*: it needs a raise path that skips the trap check, which
is not what `stmt_error` does.

🟢 **Controls:** `c.armed` and `c.rearm` confirm the handler really is armed at
these points (ERR 11 trapped on all three), and `d.next` confirms an error on the
line *after* a successful `ON ERROR GOTO` still traps. Without those, stages 1–3
would be measuring a missing handler rather than `ON ERROR`.
