# D-POPRAISE — the discard-then-abort tails, and what the class is actually worth

**Status:** the `fp_runtime_error` group SHIPPED 2026-08-28 (−13 B of main
page 1; the wall READ 106 → 119 B free that day — a reading, not a standing
figure, and `make basic-reloc` is the only current one). The other three groups
MEASURED and priced below, not taken.

## 1. Where this came from

`TODO.md` has carried, since 2026-08-26 (filed by D-MIDOP,
[`docs/spec-basic-midop.md`](spec-basic-midop.md) §4), a 2 B carve at
`ems_typecheck` with a class attached and **no sweep behind it**:

> the same 2 B sit in `ems_err_pop2`/`ems_err_pop1` next door, **and in every
> other hand-rolled pop-then-raise tail in the tree**. The class is worth more
> than the bytes: `scratchpad/` has no sweep for "a pop that only exists to
> satisfy a raise that unwinds anyway". **Unpriced.**

[`scratchpad/popraise_sweep.py`](../scratchpad/popraise_sweep.py) is that sweep.

## 2. The denominator, and how it is derived rather than declared

A **tail** is one or more `pop rr` followed by an *unconditional* transfer to a
routine that never returns. The never-return set is a **fixed point seeded from
`raise_error`** — 120 routines — not a hardcoded list, so a routine that stops
raising drops out of the sweep instead of leaving a stale verdict behind.

**16 tails.** Two things the first cut got wrong, both caught rather than shipped:

* **A `pop` directly after a `push` is a MOVE, not a discard.** `push ix / pop hl`
  at [`basic/missing.asm:509`](../basic/missing.asm) was counted as a discard.
  A move has a reader; a discard by definition does not. Fixed, and it is the
  distinction the whole class rests on.
* **The first pricing counted only the pops.** An aliased-away tail that is
  entered solely by jumps disappears *entirely* — body and jump. Q2 went 8 → 21 B
  on that correction alone.

The sweep's `--selftest` re-derives five answers by name (`ems_typecheck`,
`ems_err_pop2`, `ems_err_pop1`, `elas_abort_fp`, plus the four documented
raisers) and exits non-zero if any is missed, so a run reporting "nothing here"
is known not to be a sweep that reports that by construction. It caught its own
first bug: the label *preceding* the first `pop` was never attached, so the three
named tails were found but anonymous.

## 3. Three questions the filing ran together

| | question | answer |
|---|---|---|
| **Q1** | delete the pops outright | **21 B**, ceiling. NOT TAKEN — it makes the code *depend* on `raise_error` resetting SP rather than merely survive it. That is Joost's call and stays 🙋. |
| **Q2** | merge byte-identical bodies | 21 B |
| **Q3** | **chain** tails that share a raise target but differ in pop count | **34 B** |

Q3 is the real number and Q2 cannot see it: a 2-word entry can **fall through**
into a 1-word entry, which is the shape `ems_err_pop2 → ems_err_pop1` has carried
in `str-engine.asm` all along. Grouping by *shape* hides it; grouping by *target*
shows it.

```
4x -> stmt_error         4 bodies  17 B  ->  one 4 B chain  = 13 B   (spans LOW/page 1)
4x -> fp_runtime_error   4 bodies  18 B  ->  one 5 B chain  = 13 B   SHIPPED
2x -> els_tc_common      2 bodies   8 B  ->  one 4 B chain  =  4 B
2x -> gosub_stk_over     2 bodies   8 B  ->  one 4 B chain  =  4 B
```

## 4. What shipped: the `fp_runtime_error` chain

`cee_abort_fp`, `cepb_abort_fp` (`basic/interp.asm`), `ela_abort_fp`,
`elas_abort_fp` (`basic/vars.asm`) — **all four in page 1**, so no cross-region
question arises. 18 B of four routines (measured 2026-08-28) wearing four
register names for one instruction sequence. Now one 5 B chain, with
`vars.asm`'s two as `equ`s.

**Why the register was free to change.** The four popped into HL, BC, AF and DE —
which is exactly what made them *look* like four routines. But the word is
discarded at every one, so the destination is observable only if something reads
it, and `fp_runtime_error`'s first instructions are `ld a,(FPERR) / dec a /
ld e,a / ld d,0 / ld hl,fperr_to_err`: it **writes A, DE and HL before reading
any register at all**. `pop af` additionally dropped the flags, which `dec a`
immediately redefines. DE is dead on every path out.

**The meanings differ; the mechanism does not.** `cepb` discards "our resume
address plus the caller's saved key"; `ela` discards a `[TYPE],[OFFSET]` frame.
Only the mechanism is code.

## 5. Falsification — and the arm that was a designed no-op

🔴 **This merge cannot be falsified by a knife on the pops.** D-MIDOP's K-MD2
already deleted *both* pops at `ems_typecheck` and moved **0 rows of 9**:
`raise_error` resets SP outright, so the discards are unobservable. A merge
"verified" by a pop-count knife is verified by an arm that never fires.

So the four **entries** are witnessed instead, one knife each
([`scratchpad/popmerge_knives.py`](../scratchpad/popmerge_knives.py) over
[`scratchpad/popmerge_probe.py`](../scratchpad/popmerge_probe.py)), by
retargeting that tail's abort and watching the ERR code move:

| knife | tail | rows moved |
|---|---|---|
| K-PR1 | `cee_abort_fp` | `f.clear` `f.if` `f.print` |
| K-PR2 | `cepb_abort_fp` | `f.let` `f.letstr` |
| K-PR3 | `ela_abort_fp` | `f.ary` |
| K-PR4 | `elas_abort_fp` | `f.arystr` |

**Seven rows, DISJOINT**, and the three `f.ctl*` controls moved under none of
them — a knife that reddens a control broke the harness rather than witnessing
anything. Baseline: 11 rows, **0 DIFF against both references**.

### 🔴 The first cut of that knife retargeted to `stmt_error`, and was a no-op

Three of four tails read **UNWITNESSED**, for a reason that had nothing to do
with the tails. `stmt_error` opens with `call check_expr_errors` — D-STMTPEND's
first-error-wins rule — so **with FPERR set it re-raises the identical code**.
The fourth arm was worse than useless: retargeting `cee_abort_fp` *itself* to
`stmt_error` made `check_expr_errors` jump straight back into `cee_abort_fp`, and
the "movement" that arm reported was a runaway, not a signal. Retargeting to
`gb_illegal` (`ld a,5 / jp raise_error`) consults no pending cell; all four then
witnessed cleanly.

**This is [[a-case-that-agrees-can-agree-for-the-wrong-reason]] inverted** — a
case that *disagrees* for the wrong reason. The instrument said "these three
tails are dead"; the truth was "this arm cannot see them."

## 6. Why the two chains stay separate

`stmt_error` and `fp_runtime_error` are *not* interchangeable, even though §5
shows `stmt_error` funnels a pending FPERR into `fp_runtime_error` anyway.
`stmt_error` additionally stores **`ERRMARK` = `$DD`**, and that cell has a
reader: [`basic/missing.asm:576`](../basic/missing.asm) loads it to decide
"no operand was parsed". Merging the two chains would save 4 B and change that.
Rejected on the reader, not on a hunch.

## 7. Not taken here

* **Q1, the 21 B of pops** — 🙋, unchanged. Deleting them buys bytes with a new
  dependency on SP being reset.
* **The `stmt_error` chain — 🔴 this section said "13 B nominal, ~10 B net" and
  the measurement refutes it. It is worth 5 B, and only one member is free.**
  What decides is not the address but the **call site's jump form**:

  | member | region | call sites | verdict |
  |---|---|---|---|
  | `ela_err` | page 1 | 1× `jp` (arrays.asm:849) | **free — 5 B, SHIPPED** |
  | `ee_synerr_pop` | LOW | 2× `jr` (arrays.asm:601, 707) | pinned; 4 B − 2 B = +2 B |
  | `ex_let_err` | page 1 | 2× `jr` (interp.asm:639, 675) | pinned; 3 B − 2 B = +1 B |
  | `ems_err_pop2` | LOW | 2× `jr` (str-engine.asm:1059, 1063) | pinned — it is the canonical |

  A `jr` caller **pins** its target next to itself: moving the body costs +1 B at
  every such site, which eats most of a 3–4 B body. Only `ela_err` is reached
  solely by `jp`, so only `ela_err` may move at no cost — `ela_err equ
  ems_err_pop2`, cross-region page 1 → LOW exactly as `elas_err equ
  ems_err_pop1` already is (D-XREG, gated by `check_tenant_closure.py`).
  Witnessed alone by **K-EL1** (row `s.ary`, `ERR 2` → `ERR 5` under a
  `gb_illegal` retarget — `stmt_error`'s own siblings would have been the §5
  no-op again). **Page 1 119 → 124 B free on 2026-08-28.**
  🎯 **Read the jump form, not just the address.** Doing so turned a 13 B
  nominal group into a 5 B real one, and it is the step that separates a nominal
  price from a net one anywhere in this class.
* **`gosub_stk_over`, 4 B** — `ct_gsfull`/`ct_svc_full` are adjacent in
  `traps.asm`, both page 1, and `gosub_stk_over` reads no register. Cheap, but
  **unwitnessed**: reaching either needs a full control stack or an over-nested
  trap, and no probe row does that today. Filed rather than shipped.
* **`els_tc_common`, 4 B** — would move `ems_typecheck` out of LOW into page 1,
  a net LOW +5 / page 1 −1. Defensible while LOW (39 B) is scarcer than page 1,
  but it is a region trade rather than a carve.
