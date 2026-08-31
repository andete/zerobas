# D-CLOSALIAS — the closure gate could not see a sub-local `equ` alias

*2026-08-31. `tools/check_tenant_closure.py`. No ROM change.*

## 1. The bug, and how it was found by being obeyed

D-NGRAM14 wrote `fexp_underflow equ fexp_overflow` in `sub/fp_exp.asm` — the
D-DUPSPAN2 shape, which keeps the name and every call site while collapsing two
identical tails. `subrom-closure-check` refused it:

```
FAIL: page-1 escapes ...
  fexp_underflow = 4F5C  <- main-BASIC page-1 (switched out under a page-1 call)
```

Both names resolve to **the same address** in `build/sub.sym`. The routine is
sub-local page-1 and always was.

The cause is one line, and it is *deliberate*:

```python
sub_local = set(graph)      # every label DEFINED in the sub image
```

`build_callgraph` finds definitions with `^name:`. An `equ` is not a label, so
an alias falls through to the external branch — and at an address `>= $4000` the
external branch means *main BASIC, switched out*. **The checker reported a
sub-local routine as a main-ROM escape, at its own correct address.**

⚠️ **The label-only rule is not a mistake and must not be widened.**
`build_datagraph`'s own header records why: *"an `equ` is a VALUE, only a
`label:` is a LOCATION"* — treating every `equ` as an address reports **63
spurious escapes** on a clean tree (token numbers, PSG ports, buffer
capacities). The fix has to be narrower than the rule it repairs.

🔴 **AND THE FIRST RESPONSE WAS THE WRONG WAY ROUND.** D-NGRAM14 abandoned the
alias and pointed the callers at `fexp_overflow` directly. That cost nothing
*there* — but D-DUPSPAN2's entire method is aliasing, and the next sub-side alias
would have hit the same wall.

## 2. The fix: an alias of a sub-local label is sub-local

```python
_ALIAS = re.compile(r'^([A-Za-z_]\w*)\s+equ\s+([A-Za-z_]\w*)\s*$', re.I)
```

Only an `equ` whose right-hand side is a **bare identifier already known
sub-local** counts, resolved to a fixed point so an alias of an alias resolves
too. `X equ 12`, `X equ real_body+3` and `X equ $4F5C` are untouched — so the
rule can only ever add a symbol the tree already proves is sub-local.

## 3. 🔴 The unit arms pass on a tree where the fix does nothing

Eight arms, four of them controls that a constant, an expression, an address
literal and an alias-of-an-unknown stay *out*. They all pass — and `L1` reports
the honest problem:

```
PASS  L1 on the live sub tree it adds a BOUNDED set (0 alias(es): none)
```

**Zero.** The alias that motivated the fix was reverted with D-EXPNEG, so on
today's tree the rule is vacuous. Unit arms on a vacuous rule prove the *helper*
works and say nothing about the **gate**.

## 4. The end-to-end falsification: one plant, two checkers

A **byte-identical** plant — rename one existing `jp fexp_underflow` to
`jp fexp_und_alias` and add `fexp_und_alias equ fexp_underflow`:

| | verdict |
|---|---|
| planted, checker **without** the fix | 🔴 `FAIL: fexp_und_alias = 4F66 <- main-BASIC page-1` |
| planted, checker **with** the fix | 🟢 `OK: 587 routines ... No main-page-1 escape` |
| ROM hashes, planted vs reverted | **identical** — all four, checked, not assumed |

The red arm and the green control are the same plant on the same apparatus, and
the identical hashes are what say the plant changed a *name* and nothing else —
so the two verdicts differ by the checker alone.

## 5. What this unblocks

`docs/spec-basic-dupspan2.md` collapses 27 aliases across 16 files by exactly
this construct. Every one of them in `sub/` was, until now, a symbol this gate
would have called an escape. None had been tried; the one that was, was
abandoned rather than investigated.
