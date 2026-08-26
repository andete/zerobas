# TODO sweep — 2026-08-26 (D-TODOSWEEP), tranche 1

**Subject:** every open item in [`TODO.md`](../TODO.md), plus every closed block
carrying a residual marker. **Rule, set by the user: re-run everything, inherit
no claim** — an item is put to a machine even when it is recent and even when a
past sweep already blessed it.

⚠️ **THIS IS TRANCHE 1 OF N. 11 of 146 subject blocks carry a verdict.** The
audit below names the other 135 by id, so an unfinished sweep cannot read as a
finished one.

## 1. The denominator is an instrument, not a heredoc

`tools/todo_inventory.py` parses `TODO.md` into checkbox blocks and emits one
record per block; `--audit` sets a verdict file against it and reports items with
no verdict and verdicts with no item.

🔴 **THE 2026-08-09 SWEEP BUILT ITS DENOMINATOR WITH AN INLINE HEREDOC** — which
cannot be re-run against a later commit without being retyped, while its own
central finding was that a list nobody re-runs cannot be trusted. **The
instrument had the property it was measuring.** It is a tool now.

| | |
|---|---|
| blocks parsed | 367 (346 top-level, **21 nested** — an indented `- [x]` under an open parent is not an independent item) |
| open / done (top-level) | **109 / 237** |
| subject = open + done-carrying-a-residual-marker | **146** |
| verdicted in tranche 1 | **11** |

### 1.1 Two counts of my own disagreed, so I read

The done-block screen first reported **67**, then **37**. Reading settled it:
**27 of the 29 extra blocks matched on the bare word `OPEN`** — the BASIC verb,
in a file full of disk I/O. 37 is right.

⚠️ **AND NO CHEAP SCREEN EXISTS FOR THE OTHER 200 DONE BLOCKS.** The keyword
proxy flags 37 of 237; the file's own caveat convention (`⚠️`/`🔴`/`💰`/`🧹`/`📌`)
flags **171**; their union is 178. This project writes caveats on *closed* work
as a matter of style, so the convention cannot discriminate. **The only real
surface is reading 9,006 lines**, and that is filed as its own pass rather than
claimed here. The pickup list's own header records that this failure mode has
already happened.

## 2. Findings — tranche 1

Every row ran on `Philips_VG_8020`, `National_CF-3300` and the repack machine,
with a control on the same apparatus. Verdicts: `scratchpad/sweep_verdicts.json`.
Probes: `scratchpad/sweep_tranche1.py`, `scratchpad/sweep_paintflood.py`.

| id | item | verdict | reading |
|---|---|---|---|
| T131 | SCREEN-2 `PAINT` floods on the references | **LIVE** | `POINT(50,21)` below the wall: **vg8020 9, zb 4** — the filed claim exactly |
| T056 | `PLAY(n)` function unimplemented | **LIVE** | refs print `0`; zb raises **`Missing operand`** |
| T064 | `RUN <lineno>` in direct mode | **LIVE** | refs print `[B]`; zb prints **`[A][B]`** |
| T008 | `KEY n,"str"` unimplemented | **LIVE** | refs silent; zb raises **`Syntax error`** |
| T277 | Screen-editor REPL | **LIVE, REFRAMED** | see `docs/spec-basic-editscout.md` — the blocker named the wrong obstacle |
| T123 | third `SCREEN` argument's domain | **STALE AS FILED** | filed *UNMEASURED*; `SCREEN 0,0,0` and `0,0,99` are accepted on **all three** |
| T278 | editor / program-management bucket | **PARTLY STALE** | `TRON`/`TROFF`/`FRE`/`SWAP`/`ERASE` all SUPPORTED today; `RENUM`/`AUTO`/`DELETE` shipped. Down to `WAIT` + full `CLEAR` |
| T279 | keyword-completeness gaps | **STALE** | today's `kwsweep` has **no `MISSING=` line**; the item says "34 genuinely absent" |
| T029 | "main page 1 was 1 B free" | **STALE** | **89 B** |
| T047 | "page 1 2 B, low region 17 B" | **STALE** | **89 B / 39 B** |
| T122 | the pickup list's own RANKING | **STALE** | ranks 38/62 apparatus, 15 BASIC; the list is 109 open, split 60/39/3/7 |

**5 LIVE, 5 stale or partly stale, 1 live-but-reframed.** Nearly half the sample
did not survive re-running — and T122, the item that *is* the ranking, is one of
the stale ones.

🎯 **T056 IS THE SHARPEST.** A closed `D-PLAYOP` block sits directly beneath it
in the file, closed the same week, both about `PLAY` and a missing operand.
Reading would have merged them. **Running separated them**: D-PLAYOP fixed the
`PLAY` *statement*'s operand; the *function* form `PLAY(0)` still raises.

## 3. What the apparatus cost, said out loud

* 🔴 **THE FIRST RUN INHERITED EVERY PREVIOUS CASE'S SCREEN.** `reset=("NEW",)`
  does not clear, so the `[...]` span reader returned earlier cases' values —
  T008 "read" a `9` that `PAINT` had printed two cases before. **An accumulating
  screen reads as a plausible value.** Fixed by resetting with `CLS`.
* 🔴 **`WAIT 1,0` HUNG BOTH REFERENCES AND VOIDED EVERY CASE AFTER IT.** `WAIT`
  blocks on a port condition. In a batch that is not one lost row: T123 came back
  empty on both references for that reason alone, reading as *"the references
  printed nothing"* rather than *"the machine is still inside the previous
  case"*. **A blocking statement may not share a batch.** `WAIT` is therefore
  still UNMEASURED.
* ⚠️ **T131 NEEDED ITS OWN BOOT AND A 25 s STEP** — the references flood the
  whole screen, which does not finish inside a batch `step`. In tranche 1 it
  read as "no output on either reference", the `<NO OUTPUT>`-means-two-things
  trap.
* ⚠️ **`cf3300` RETURNED NO SPAN ON ANY T131 ROW, CONTROL INCLUDED** — an
  apparatus gap, not a finding. **T131 rests on ONE reference.**
* 🟢 **T131's SECOND CONTROL IS LOAD-BEARING**: `POINT` *above* the wall reads
  `9` on both sides, so zb's `PAINT` does fill — it just does not cross. Without
  it, zb's `4` could have meant "PAINT did nothing at all".

## 4. Audit — the sweep cannot pretend to be finished

```
subject ids            : 146
verdicts supplied      : 11
subject with NO verdict: 135
verdicts for NON-subject: 0
```

Re-run with `python3 tools/todo_inventory.py --audit scratchpad/sweep_verdicts.json`.
