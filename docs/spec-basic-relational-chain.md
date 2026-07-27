<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — chained relationals, and operators after a string `PRINT` item

**Status:** ✅ **LANDED 2026-07-27.** `make logicops-acceptance` 193/193.
Implements decision **D-LOG-C** from
[`spec-basic-logicops-eqv-imp.md`](spec-basic-logicops-eqv-imp.md) §7. Both
defects were found by the `EQV`/`IMP` characterization's **calibration** battery
going red on rows built only from operators zerobas already implemented; contract
from [`logicops-vg8020-characterization.md`](logicops-vg8020-characterization.md)
§6.

## 1. Scope

Two silent-wrong-answer defects, both pre-existing, both reproducible on
`AND`/`XOR` long before `EQV`/`IMP` existed. D-KW-3 names the silent class the
keyword arc's exit criterion; neither of these is a *keyword* gap, so neither was
on anyone's list.

They were spec'd as one slice on the belief that they shared a routine. **They do
not** — see §2 — but they stayed one slice anyway: one gate, one probe, one
measurement session, and the same underlying shape (*an expression is cut short
and the remainder is silently misread as something else*).

## 2. What the correction to the earlier framing was

`spec-basic-logicops-eqv-imp.md` §7 said both defects "are the same routine
(`ev_rel`)". That was wrong, and the way it was wrong is the reusable part.

| | D-LOG-1 chained relationals | D-LOG-2 operator after a string item |
|---|---|---|
| first believed | `ev_rel` | `ev_rel` |
| **actually** | **`ev_rel`** ✅ | **`PRINT`'s `exp_strvar` path** |
| contexts affected | `PRINT`, assignment, `IF`, program mode | **`PRINT` only** |
| scope first believed | — | 4 logical operators |
| **actual scope** | — | **12 operators; 11 broken** |

Two follow-up measurements produced those corrections, and each one existed
because the *first* attempt at the row could not have failed:

* **The sentinel.** `X = "A" AND 1` then `PRINT X` printed ` 0 ` on both sides —
  the reference errored and left `X` at its power-on `0`, zerobas assigned `0`.
  Identical output, opposite behaviour. Seeding `X=99` first separates them, and
  says the assignment path was **already correct**. Same for `IF`.
* **The sweep.** Testing four logical operators found four broken. Testing the
  whole operator block `$F1 '+' .. $FC '\'` found **eleven** broken and exactly
  one (`+`) already handled.

## 3. The measured contract

1. **Relationals chain, left-associatively.** `1 = 0 = 0` is `(1 = 0) = 0` = `-1`.
   `1 = 1 = 1 = 1` = `0`. Compound operators participate: `1 <= 2 = -1` = `-1`.
2. **A string comparison's result is a number**, so a chain that *starts* with
   strings continues numerically: `"A" = "A" = -1` = `-1`.
3. **The RHS of any link may not be a string**: `1 = 1 = "A"` → `Type mismatch`.
4. **Any operator immediately after a string `PRINT` item is a `Type mismatch`** —
   all twelve of `+ - * / ^ AND OR XOR EQV IMP MOD \`.
5. **Raised BEFORE the item is emitted**: the reference prints `[|Type mismatch`,
   not `[A|Type mismatch`.
6. **Still legal after a string item:** juxtaposition (`PRINT "A" 1` → `A 1`), a
   relational (re-parsed as a comparison), and `+` between two *strings* (concat).
   An operator at the *start* of an item is untouched (`PRINT -1`).

## 4. Design

### 4.1 D-LOG-1 — a loop, where there was a `ret`

`ev_rel` computed one comparison and returned, leaving any further relop on the
cursor. The fix labels the relop scan `evr_scan` and jumps back to it after each
result instead of returning:

```
                ld      de,0                ; false = 0
                and     c                   ; intersect requested with actual
                jr      z,evr_chain
                dec     de                  ; true = -1
evr_chain:      jp      evr_scan            ; and look for the NEXT relop
```

The `ret nc` already at `evr_scan` terminates the chain when no relop follows, so
no new exit is needed. The LHS string probe stays **outside** the loop (a chained
LHS is always the previous comparison's numeric result) while the RHS probe at
`evr_rhs` is **inside** it — which is what gives clause 3 for free.

`ev_rel_str` (the string-comparison path, `str-engine.asm`) joins the same loop
after `flt_int_result`, which preserves IX — exactly the advanced cursor
`evr_scan` wants.

Repack-gated; the lean 16 KB cart keeps the single-comparison form and stays
byte-identical.

### 4.2 D-LOG-2 — a range test, ahead of the emit

The operator tokens are contiguous, so `op_after_str_q` is a range test in the
same shape and register contract as the existing `relop_peek`. It is consulted
at two places:

* **`exps_notrel`**, after `relop_peek` declines and **before `print_strval`** —
  clause 5. Putting it after was the first attempt and produced exactly the
  one-character divergence `[A|Type mismatch`: the right error, one item too late.
* **`str_lit_concat_q`**, widened from a bare `cp PLUS_TOKEN`, so a *literal*
  followed by any operator leaves the fast char-by-char path and reaches
  `exps_notrel` at all. Only `+` used to, which is precisely why `PRINT "A" + 1`
  was right and `PRINT "A" AND 1` was not.

## 5. Cost

| region | before | after | delta |
|---|---|---|---|
| main page-1 | 523 B free | **498 B free** | −25 B |
| main low region | 5 B free | **7 B free** | **+2 B** |
| lean `basic.rom` | — | — | **byte-identical** ✅ |

The low region *gained*: `ev_rel_str`'s tail got shorter turning two `jp`s into a
shared `call`+`jp`. All closure and kwtable-identity checks green.

## 6. Gating

`make logicops-acceptance` — **193/193**, every row a two-sided differential.
Batteries 6 and 7 carry these two families: the chain rows in `PRINT`,
assignment, `IF` and **program mode**, the full twelve-operator sweep, and the
four controls that must keep working.

**Falsified independently, both directions:**

| break | gate |
|---|---|
| remove the `jp evr_scan` chain loop | **23/33** |
| disable the `op_after_str_q` check | **21/33** |
| both intact | **33/33** (193/193 full) |

### 6.1 The trap this slice contained

The first working version was green on the full gate at 192/193 and **crashed
into garbage VRAM** on `PRINT "A" IMP 1` in isolation. The abort path took
`check_expr_errors` without popping `exp_strvar`'s operand-start guard;
`check_expr_errors` pops only its *own* resume address, so each occurrence
stranded one word on the stack. Harmless on some paths, fatal on others — and the
batched gate mostly hid it, because a reset between cases papers over a slow
stack leak that a boot-per-case run walks straight into.

**A deferred-error abort that jumps out of a guarded region has to unwind that
region itself.** This is the second register/stack-contract trap in two slices
(see the `HL` clobber in the `EQV`/`IMP` spec §5.1) — both invisible to every
static check, both found only by running it.

## 7. Files

| file | change |
|---|---|
| [`basic/expr.asm`](../basic/expr.asm) | `evr_scan` label; `evr_chain` loop (repack-gated) |
| [`basic/str-engine.asm`](../basic/str-engine.asm) | `ev_rel_str` tail joins the chain loop |
| [`basic/print.asm`](../basic/print.asm) | `op_after_str_q`; `exps_notrel` check ahead of the emit; widened `str_lit_concat_q` |
| [`probes/basic/basic_probe_logicops.py`](../probes/basic/basic_probe_logicops.py) | batteries 6–7 promoted from *recorded divergence* to **gated**; multi-line context cases |

## 8. Verification log

| check | result |
|---|---|
| `make basic-reloc` from clean | page-1 498 B, low region 7 B, lean byte-identical |
| kwtable-identity / resident-ABI / tenant-closure ×3 | OK |
| `make logicops-acceptance` | **193/193** |
| falsification ×2 (each fix separately) | 23/33 and 21/33 |
| `make string-acceptance` | PASS |
| `make error-acceptance` | ALL PASS |
| `make math-acceptance` | ALL PASS |
| `make float-acceptance` | ALL PASS |
| `make intarg-acceptance` | ALL PASS |
| `make direct-ctrl-acceptance` | 40/40 |
