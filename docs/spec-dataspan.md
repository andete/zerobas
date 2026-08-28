# D-DATASPAN — the filed measurement was not reproducible, and both its findings were apparatus

**2026-08-28.** Ships the edge rule D-PROLOGUE §12.5 filed on 2026-08-22 and left
open because *"that triage is the slice, not the edge rule."* The triage is done —
and it moved the numbers in both directions.

## 1. 🔴 The tracked script reproduced the CATASTROPHE, not the measurement

`TODO.md` quotes *"main 43 edges → 1 finding, `ex_sep`, 4 B; sub 77 edges → 4
findings, 97 B"*. Re-running [`scratchpad/dataspan_measure.py`](../scratchpad/dataspan_measure.py)
as tracked gives:

```
main  1195 findings  28820 B      in a 22510 B ROM
sub    124 findings   1444 B
```

That is §12.1's failure, the one the item explicitly says was avoided (*"never out
of empty ones — that is §12.1's 1227-span error"*). The cause is one line:

```python
return seen or True          # an EMPTY span emits nothing either
```

`seen or True` is `True`. An **empty** span is classified data-only and its
fallthrough edge is cut — and the commit that added this script is titled *"…the
obvious fix reports 27 KB in a 22 KB ROM"*. **The script implements §12.1's
demonstration; the item cites §12.5's measurement from it.** With empty spans
excluded (`--empty-too` now reproduces §12.1 deliberately), the item's numbers
come back exactly: main 1 finding / 4 B, sub 4 / 97 B.

## 2. 🔴 Then both `dw`-table findings turned out to be the rule's own artifact

A fallthrough edge and a **reference** edge to the same label are *one entry* in
the edge dict, so discarding "the fallthrough" discards the reference too.

`stmt_table` is a `dw` dispatch table that **contains `dw ex_sep`** *and* is
followed in source order by `ex_sep`. Cutting the fallthrough also cut the
dispatch entry — so main's only finding was manufactured by the rule. `em_table` /
`em_ill_direct` is the identical shape.

The fix is one clause: **a target the span NAMES keeps its edge**, because the
reference is real however the fallthrough is judged.

| | filed | reproduced | after the reference fix |
|---|---|---|---|
| main | 1 finding, 4 B | 1 finding, 4 B | **0** |
| sub | 4 findings, 97 B | 4 findings, 97 B | **3, 82 B** |

## 3. The triage — all three survivors were the arithmetic class

* **`sub_p1_table`** (72 B) — the page-1 entry table, dispatched into by the main
  ROM as `SUBROM_ENTRY_BASE_P1 + 3*index`. `page0_seeds`/`page1_seeds` already
  parse these tables to seed their *tenants*; the tables themselves were seeded by
  nothing. **Seeded, not allowlisted** — an allowlist entry claims "dead and kept
  on purpose", which would be false. `sub_p0_table` joins it.
* **`tkf_ref65535` / `tkf_ref32768`** (5 B each) — genuinely dead, **deleted**.
  They are `flt_to_int16`'s sign-dependent bounds, and `flt_to_int16` lives in
  `basic/float-arith.asm`, which is **not in `sub/sub.asm`'s closure**. All three
  loads (`dcc_bound_pick`) are main-side and **by name**, with no arithmetic over
  the table — checked, because arithmetic is exactly what this class is about.
  ⚠️ `tkf_ref32767` stays: `sub/tkfloat.asm:522` loads it. That file's header says
  *"the tkf_ref\* bound tables live INSIDE this body (used by tkf_cmp32767)"* —
  true of **one** of the three, and that plural is how two dead tables kept their
  place. **sub page 0: 2434 B → 2444 B free.**

## 4. Shipped

Fixes (10) and (11) in [`tools/check_dead_code.py`](../tools/check_dead_code.py):
the entry-table seeds, and the data-only fallthrough rule with both guards —
**empty is not data-only**, and **a named target keeps its edge**.

**Falsification.** `--blind` still exits non-zero, so the allowlist canary fires
and the sweep has not gone quiet; both entries are still detected as dead. The two
new predicates are checked directly rather than trusted:

| input | `_data_only` | |
|---|---|---|
| `db "hello",0` | **True** | a data table |
| `db …` + `ret` | False | has an instruction |
| empty span | **False** | §12.1 — an alternate entry point |

| input | `_names(…, 'ex_sep')` | |
|---|---|---|
| `dw ex_sep` | **True** | reference, edge kept |
| `db "hello",0` | False | genuine fallthrough, edge cut |

`main: 0 dead`, `sub: 0 dead (+2 allowlisted)`, 108 seeds.

## 5. What this cost and bought

**+10 B of sub page 0**, and the main ROM does not move. The bytes are not the
point: the gate now cuts 26 main and 37 sub fallthrough edges that never existed,
so a routine reachable only by falling off the end of a string table is reportable
for the first time.
