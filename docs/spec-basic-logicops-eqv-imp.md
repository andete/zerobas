<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — `EQV` / `IMP` via a table-driven logical layer

**Status:** SPEC, 2026-07-27 — **awaiting sign-off**. A measured spike exists in
the working tree (see §4/§5); nothing is committed. Implements
[`decision-kwgaps-slicing.md`](decision-kwgaps-slicing.md) §4.1 lever **L2**,
the slice D-KW-1 named as next. Behavioural contract comes entirely from
[`logicops-vg8020-characterization.md`](logicops-vg8020-characterization.md).

## 1. Scope

Add `EQV` and `IMP` to the repack build, clearing **2 of the 8 SILENT-GAP**
words in the [keyword sweep](kwsweep-msx1-coverage.md). Today `PRINT 5 EQV 3`
parses `EQV` as a variable and prints three separate values — the most alarming
failure in that table.

**In scope:** the two operators, the precedence layer restructure that pays for
them, their kwtable entries (crunch + `LIST` come free from the shared table),
and a standing acceptance gate.

**Out of scope**, and each wants its own decision — see §7:

* **D-LOG-1** chained relationals (`1 = 0 = 0`), **D-LOG-2** string LHS to a
  logical operator (`"A" AND 1`). Both found by this work, both **pre-existing
  and reproducible on `AND`/`XOR`**, both one layer down in `ev_rel`.
* The lean 16 KB cart. It stays byte-frozen and ships without `EQV`/`IMP`.

## 2. The contract — all measured, none asserted

From the characterization; every clause has a measured row behind it.

1. **Semantics.** `EQV a b = NOT (a XOR b)`; `IMP a b = (NOT a) OR b`. Bitwise,
   16-bit. `IMP` is **not** commutative.
2. **Precedence.** `NOT` > `AND` > `OR` > `XOR` ≡ `EQV` > `IMP`, below the
   relational layer, which is below arithmetic. `XOR` and `EQV` are **provably
   indistinguishable** (mutually associative), so their relative level is a free
   choice — this spec puts `EQV` one level looser purely to keep the table in
   manual order.
3. **Associativity.** Left. Observable only on `IMP`.
4. **Operand domain.** Signed 16-bit; floats **truncate toward zero** (not
   round); out-of-range → `Overflow`; string operand → `Type mismatch`.
   Identical to the existing `AND`/`OR`/`XOR`/`\`/`MOD` operand protocol
   (`fac_to_int_strict_reset`), so no new conversion behaviour is introduced.
5. **Tokens.** `EQV` = `$F9`, `IMP` = `$FA` — oracle-measured from the VG-8020's
   own crunch emission, filling the hole between `XOR` `$F8` and `MOD` `$FB`.

## 3. Design — one generic layer replacing three hand-rolled ones

`ev_xor`/`ev_or`/`ev_and` were byte-for-byte uniform at 34 B each (`clone_scout`
flagged `ev_*_lp` as 5 × 31 B), differing only in a token compare and a 6-byte
apply block. Adding two more copies would cost **+68 B**. Instead:

* **A precedence table**, loosest first: `db token, dw apply-leaf`, `$00`
  terminated. The level is a **pointer into that table**, carried in `HL`, so the
  next-tighter level is just the next 3-byte entry — no index arithmetic — and
  the terminator is what drops through to unary `NOT`.
* **A shared 2-byte apply loop** (`lg_apply`), with a 2–3 byte ALU leaf per
  operator (`and e` / `or e` / `xor e` / `xor e`+`cpl` / `cpl`+`or e`). Twelve
  bytes of leaves cover all five operators, against ~49 B of inlined apply
  blocks.

The lean build keeps the original chain verbatim under `IF ROM_BASE < $4000` /
`ELSE`, so `basic.rom` stays byte-identical.

Entry point renamed `ev_xor` → **`ev_logic`** (aliased to `ev_xor` in the lean
branch); the five call sites that enter at the lowest precedence layer —
`eval`, `ev_f_paren`, `usr.asm`, and two more in `expr.asm` — move to it.

## 4. Cost — measured, not estimated

Measured from clean (`rm -rf build && make basic-reloc`), which is the only
measurement this repo trusts:

| region | before | after | delta |
|---|---|---|---|
| main page-1 | 518 B free | **523 B free** | **+5 B** |
| main low region | 5 B free | 5 B free | 0 |
| `sub.rom` kwtable | 913 B | 925 B | −12 B of ~4 KB spare |
| lean `basic.rom` | — | — | **byte-identical** ✅ |

**Six operator levels cost 5 bytes less than the three they replace.** The
decision doc estimated "≈ 0 net bytes"; the measurement beats it slightly. All
tenant-closure and kwtable-identity checks stay green.

## 5. Gating

`make logicops-acceptance` — **156/156**, every row a two-sided differential
against the VG-8020.

**The gate is falsifiable, and was falsified.** Deleting the `cpl` from `lg_eqv`
takes it to **115/156** (41 failures). Per the standing lesson that a green gate
can be measuring nothing, this was run, not reasoned about.

Regression suites over the touched evaluator: `math-acceptance` ALL PASS,
`float-acceptance` ALL PASS (further suites in §8).

### 5.1 The trap this slice actually contained

The first build was green — assembler, `check_reloc`, `check_tenant_closure`,
`check_kwtable_identity`, all OK — **and it crashed the interpreter into garbage
VRAM on every float operand**, including `2.7 AND 0`, which had worked for
months.

`fac_to_int_strict_reset` clobbers `HL`. The hand-rolled layers never noticed
because their level was implicit in the code position and `HL` was dead there;
carrying the level **in a register** is exactly what makes the table-driven form
need a guard the original never did. Integer operands kept working throughout,
so the failure was invisible to every static check and to more than half the
gate.

The fix is a one-line reorder (`push hl` before the call) and costs zero bytes.

**This is the recurring arc lesson, on its ~19th occurrence:** green suites and
static reasoning missed it; the empirical differential caught it. It is also a
specific, reusable one — **a refactor that moves state from the code position
into a register inherits every clobber contract the original was free to
ignore.**

## 6. Files

| file | change |
|---|---|
| [`basic/expr.asm`](../basic/expr.asm) | table-driven layer + leaves + `logtab`; old chain under `ELSE`; 5 entry call sites → `ev_logic` |
| [`basic/sysvars.inc`](../basic/sysvars.inc) | `EQV_TOKEN` `$F9`, `IMP_TOKEN` `$FA` |
| [`basic/kwtable.inc`](../basic/kwtable.inc) | `EQV`/`IMP` rows, repack-gated |
| [`basic/usr.asm`](../basic/usr.asm) | `ev_xor` → `ev_logic` |
| [`probes/basic/basic_probe_logicops.py`](../probes/basic/basic_probe_logicops.py) | new — characterization + gate |
| [`Makefile`](../Makefile) | `logicops-characterize`, `logicops-acceptance` |

## 7. Decisions — sign-off needed

**D-LOG-A — land the slice as spiked?** The implementation exists, is gated
156/156, is falsified, and is net **+5 B**. Recommend **yes**.

**D-LOG-B — `EQV` looser than `XOR`, or the same level?** They are measurably
indistinguishable, so this is free either way. The spike puts `EQV` on its own
looser level (1 extra table entry = 3 B) to keep the table reading in manual
order. Collapsing them onto one level would save 3 B and be equally faithful.
Recommend **keep them separate** — the 3 B buys a table that matches the
documented order, which is worth more than 3 B of a 523 B budget.

**D-LOG-C — what happens to D-LOG-1 (chained relationals) and D-LOG-2 (string
LHS)?** Both are SILENT-GAP class — wrong answers, no error — and D-KW-3 already
named that class the arc's exit criterion, but neither is a *keyword* gap, so
neither is on the §4.3 list. Recommend a **joint follow-on slice**: they are the
same routine (`ev_rel`), one gate, and the probe rows already exist and are
already red. Not this slice.

**D-LOG-D — is the `ev_*_lp` clone group now closed?** Yes. `clone_scout`
listed it at ~104 B as the last page-1 group of any size; this slice consumes it
as the decision doc required (*"must not be done standalone… folding it into the
`EQV`/`IMP` slice buys seven operator layers for what five cost"*). What remains
of that shape in the whole tree is `fat_rand_*` at ~28 B, which is not worth a
session.

## 8. Verification log

| check | result |
|---|---|
| `make basic-reloc` from clean | page-1 **523 B**, low region 5 B, lean byte-identical |
| `check_kwtable_identity` / `check_resident_abi` / `check_tenant_closure` ×3 | OK |
| `make logicops-acceptance` | **156/156** |
| falsification (delete `cpl` from `lg_eqv`) | **115/156** — the gate measures its subject |
| `make math-acceptance` | ALL PASS |
| `make float-acceptance` | ALL PASS |
| `make intarg-acceptance` | ALL PASS |
| `make error-acceptance` | ALL PASS |
| `make string-acceptance` | PASS (all four cells) |

Those five were chosen because they are the suites that run *through* the
expression evaluator — the routine this slice restructures — rather than because
they mention logical operators.
