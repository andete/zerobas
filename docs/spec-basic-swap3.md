# D-SWAP3 — `SWAP`'s third operand is the statement boundary, not a bespoke check

**Date:** 2026-08-24. **Commit:** (this slice). **Fix:** delete SWAP's
third-operand rejection block in [`basic/missing.asm`](../basic/missing.asm) and
let `exec_stmt`'s generic statement-boundary guard reject the leftover. **Cost:
−23 B — a MAIN page-1 CARVE** (page-1 free 68 → 91 B, read from
`make basic-reloc`). References: Philips VG-8020 and National CF-3300.

## 1. The filed item, and what it got half-right

`TODO.md` §"Language / verb surface": zerobas raised `Illegal function call`
(ERR 5) for a third `SWAP` operand where the references answer `Syntax error`
(ERR 2), and
[`docs/missing-vg8020-characterization.md`](missing-vg8020-characterization.md)
§4.5 recorded that same ERR 5 and called it *"the kind of detail that only a
measurement produces."* The item priced a 0 B fix: retarget `jp sw_illegal` at
the one raiser to `jp pl_syntax`.

Two things were wrong with that framing, and the second is the whole slice:

1. **§4.5 agreed for the wrong reason.** Its `SWAP A,B,C` fixture left `B`
   undefined, so what it measured was the SECOND-operand rule — `A=1:SWAP A,B` is
   `Illegal function call` because operand 2 must EXIST (`sw_absent`) — firing
   before the parse ever reached `,C`. With `B` DEFINED the references answer
   ERR 2. §4.5's own `SWAP A,B,` row shows ERR 2 because it happened to run with
   the variables in scope: the table is internally inconsistent about state.
2. **The error code was not the only divergence.** The references EXCHANGE the
   first two operands and *then* raise ERR 2 for the trailing token. A raiser
   that fires before the exchange gets the code right and the SIDE EFFECT wrong.

## 2. The mechanism — there is already a generic boundary guard

When any statement handler finishes with `jp exec_stmt`, the loop
([`basic/interp.asm`](../basic/interp.asm) `es_noentry`) skips spaces and, if the
next token is not a statement keyword, not `:` and not a letter, falls to
`jp stmt_error` — a trappable `Syntax error`. So a statement only has to consume
its own arguments and return; leftover garbage is the loop's problem.

zerobas's `SWAP` had grown a bespoke block that peeked past operand 2 for a `,`
and raised on its own — the wrong layer. The fix removes it: `SWAP` consumes
exactly `A,B`, falls into `sw_types`, exchanges, and `jp exec_stmt`s. A trailing
`,C` or bare `,` is then rejected by the generic guard — ERR 2, trappable,
first-error-wins — **after** the exchange, which is the reference's architecture.
`sw_absent` still owns the second-operand rule (ERR 5), and it fires while
resolving operand 2, before the exchange, so an undefined `B` never reaches the
boundary.

## 3. The measurement — 0 DIFF on 21 rows, references unanimous

`scratchpad/swap3_probe.py`, 21 rows × 3 machines, readout `[ERR R]` under
`ON ERROR GOTO 900` (an `UNTRAPPED <msg> in <line>` face distinguishes an
untrapped abort; `<A>` prints before the statement so "died AT the SWAP" is not
"never ran"). `R` reads a variable back where the row needs the side effect.

| row | statement (setup) | refs | zb before | zb after |
|---|---|---|---|---|
| s.3none | `SWAP A,B,C` (—) | `5 0` | `5 0` | `5 0` |
| s.3bund | `SWAP A,B,C` (`A=1`) | `5 0` | `5 0` | `5 0` |
| **s.3cund** | `SWAP A,B,C` (`A=1:B=2`) | `2 0` | **`5 0`** | `2 0` |
| **s.3all** | `SWAP A,B,C` (`A=1:B=2:C=3`) | `2 0` | **`5 0`** | `2 0` |
| **s.4all** | `SWAP A,B,C,D` (all def) | `2 0` | **`5 0`** | `2 0` |
| s.tc.def | `SWAP A,B,` (`A=1:B=2`) | `2 0` | `2 0` | `2 0` |
| s.tc.bun | `SWAP A,B,` (`A=1`) | `5 0` | `5 0` | `5 0` |
| s.tc.non | `SWAP A,B,` (—) | `5 0` | `5 0` | `5 0` |
| **s.ok3** | `SWAP A,B,C` read A (all def) | `2 2` | **`5 1`** | `2 2` |
| **s.ok3b** | `SWAP A,B,C` read B (all def) | `2 1` | (n/a) | `2 1` |
| **s.tc.va** | `SWAP A,B,` read A (`A=1:B=2`) | `2 2` | (n/a) | `2 2` |
| **s.tc.vb** | `SWAP A,B,` read B (`A=1:B=2`) | `2 1` | (n/a) | `2 1` |
| s.mm3 | `SWAP A%,B!,C` (`A%=1:B!=2`) | `13 0` | `13 0` | `13 0` |
| s.mm3v | `SWAP A%,B!,C` read A% | `13 1` | `13 1` | `13 1` |
| s.2none | `SWAP A,B` (—) | `5 0` | `5 0` | `5 0` |
| s.2bund | `SWAP A,B` (`A=1`) | `5 0` | `5 0` | `5 0` |
| s.ok | `SWAP A,B` read A (`A=1:B=2`) | `0 2` | `0 2` | `0 2` |
| z.45.3 | `SWAP A,B,C` (—) | `5 0` | `5 0` | `5 0` |
| z.45.tc | `SWAP A,B,` (—) | `5 0` | `5 0` | `5 0` |
| z.45.one | `SWAP A` (—) | `2 0` | `2 0` | `2 0` |
| z.45.lit | `SWAP A,1` (`A=1`) | `2 0` | `2 0` | `2 0` |

Before: 4 DIFF (the ERR-5/ERR-2 rows plus s.ok3's value). After: **0 DIFF**.
The two witnesses that matter:

* **s.ok3 `2 2` / s.ok3b `2 1`** — `A` became 2 and `B` became 1: the swap
  HAPPENED, then ERR 2. The clean-HEAD ROM read `5 1` (aborted before the swap,
  A unchanged). The side effect is now faithful, not just the code.
* **s.tc.va `2 2` / s.tc.vb `2 1`** — the bare trailing comma swaps-first too,
  the same rule.
* **s.mm3 `13 0`** — a type mismatch (ERR 13) still outranks the boundary: the
  type check in `sw_types` runs before the exchange and before `exec_stmt`, so
  `SWAP A%,B!,C` reports the mismatch and `A%` is unchanged (`s.mm3v 13 1`),
  matching both references. The carve did not disturb that ordering.

## 4. Knives — `scratchpad/swap3_knives.py`, 3/3 EXACT

The clean-HEAD before-run is the natural revert. The three knives falsify the
three load-bearing claims independently:

* **K-SW1** `sw_absent jp gb_illegal -> jp stmt_error`: the eight
  "B undefined -> ERR 5" rows move to ERR 2 and nothing else — proving those
  ERR 5 readings are the second-operand rule, which is why §4.5 saw ERR 5.
* **K-SW2** `ld (hl),a -> ld (hl),c` (operand-1 write): the value rows that read
  A after the swap move — the exchange writes operand 1 before the boundary.
* **K-SW3** `ld c,(hl) -> ld c,a` (operand-1 read): the value rows that read B
  move — operand 2 is written too.

## 5. §4.5 corrected, not deleted

[`docs/missing-vg8020-characterization.md`](missing-vg8020-characterization.md)
§4.5's `SWAP A,B,C -> Illegal function call` row is narrowed to name the
operand-2 state that produces it, with the DEFINED-B reading (ERR 2, swap-first)
recorded beside it.

## 6. What is NOT in scope

* The value column proved the swap-first side effect only for two operands
  DEFINED and same-typed. A cross-type extra-operand row (`SWAP A%,B!,C`) is
  measured (`s.mm3`, ERR 13) but the exchange never runs there; no row exercises
  a swap-first on a partial/near-boundary type.
* The generic-boundary insight applies to any verb with a bespoke
  trailing-token check. This slice touched only `SWAP`; a sweep for the pattern
  is not attempted here.
