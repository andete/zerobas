# SPEC — D-DEFFNEV: the parse evicted, and the wall read

Status: **MEASURED, NOT SHIPPABLE.** 2026-08-22, branch `deffn-draft` on top of
D-DUPSPAN2 (`7e9030c`). The tenant is a **sizing stub**: this slice answers one
question and says so in its own headline.

> **⚠️ ESTIMATED. It needs the same treatment this file gave the first draft:
> build it and read the wall.**
> — [`deffn-impl-2026-08-22.md`](deffn-impl-2026-08-22.md) §7(2), of the ~110 B
> the eviction was supposed to return.

This file is that build.

---

## 1. The reading

`__MEAS_PAGE1_END`, from a build with `G6/G7/G8_RESIDENT = 1` — i.e. **the
shipping feature set**, not the scaffold — read by neutralising ONLY the `$8000`
ceiling assert (`scratchpad/deffn_measure_over.py`; the wrap assert stays armed, the
source is restored byte-for-byte, and `git diff` is empty afterwards). Without
that, pasmo writes no `.sym` at all and an image that does not fit cannot be
measured.

| build | `__MEAS_PAGE1_END` | past `$8000` | delta |
|---|---|---|---|
| draft + D-DUPSPAN2 carve | `$8140` | 320 B | — |
| **+ the parse eviction** | `$80AC` | 172 B | **−148 B** |
| + the snapshot/leave merge (§4) | `$80A4` | 164 B | **−8 B** |

Main page-0 low free is **92 B** and unmoved throughout, so:

> ### the gap is 164 − 92 = **72 B**.

**`basic/deffn.asm` is 419 B → 271 B → 263 B.** The verb's main-ROM cost is
**450 → 294 B** against **222 B free** (92 low + 130 page 1, `make basic-reloc`,
2026-08-22 at `7e9030c`).

🟢 **THE ESTIMATE WAS LOW, AND IN THE USEFUL DIRECTION.** ~110 B was filed;
**148 B** was measured. The 38 B difference is that the estimate priced only the
five named routines and not what falls out with them — three of the five error
tails stop being reachable from main at all, because ERR 18, ERR 13 and ERR 5
are all dispositions the *tenant* now decides.

---

## 2. What is left in the main ROM, byte by byte (from the sym)

| piece | B | why it cannot leave |
|---|---|---|
| `ex_deffn` | 52 | not evicted — see §5 |
| `ev_fn` / `str_ev_fn` | 43 | the two factor entries; §5 |
| `fn_call` seed + `fn_enter` | 42 | moves **SP**, which a routine under CALSLT may not |
| the servicer (`fn_lp`…`fn_fin`) | 104 | it *is* the glue |
| `fn_leave` | 19 | SP again |
| `fn_deep` | 3 | ERR 7, raised before any tenant call |
| **total** | **263** | |

Everything else — the name resolve, the two lists walked together, the delimiter
agreement that is the whole arity rule, `fn_slot` and its ceiling, both
directions of ERR 13, the `$FFFF`-keyed result slot — is now the tenant's.

---

## 3. 🔴 A constraint the estimate did not have: a nested call eats the ABI

The draft kept its parse state in registers and on the Z80 stack, where nesting
takes care of itself. **A tenant cannot**: a CALSLT is not resumable, so the
phase, both cursors and the pending formal all have to live in RAM — and
`DEF FNB(X)=FNA(X+1)+X` evaluates FNA's actual **in the middle of FNB's own
parse**, through `eval`, through a second `fn_call`.

So the five ABI cells are not scratch: they are **part of the frame**, and they
go at the BOTTOM of it, inside `FN_CELLS`, so the one `ldir` that saves the live
prefix carries them exactly as it carries `FN_FEND`/`FN_SLOTP`/`FN_RTYPE`.
`o.nestsame` is the row that would have caught it.

🎯 **AND IT FITS EXACTLY, WITH THE ASSERT AS THE PROOF.** `FN_CELLS` 3 → 11,
`FN_PAREA` `$EA95` → `$EA9D`, `LINEBUF − FN_PAREA` = 99, `FN_AREA` = 99,
`FN_MAXP` = **9** — the measured nine-formal ceiling, with zero bytes to spare
and `IF FN_MAXP < 9` shipping underneath it.

## 3.1 🔴 And one the estimate priced at zero: a page-0 tenant has no import path

**MEASURED this session:** *no* page-0 tenant in this tree calls main page 1 by
absolute address, and there is no mechanism for it.
`sub/basic-resident-abi.inc` is generated for **page-1** tenants calling main's
**low** region and asserts every symbol is below the low ceiling;
`sub/deftype.asm` clones `skip_spaces` sub-locally for exactly this reason.

`tools/carve_scout.py --entries skip_spaces,is_letter,var_name_key,var_str_type,if_skip_to_else`
says **page-0-tenant CLEAN**, so the closure is legal — but legality is not
reachability. `var_name_key` and `deftbl_lookup` need sub-side clones. That is
**free in bytes** (sub page 0 has 3016 B free with the stub in) and it is work
the *"~46 B of new tenant glue"* estimate did not carry.

⚠️ Conversely `var_find_typed` / `var_alloc_or_find` are **not** a problem and
the scout says why: they reach `subrom_call`, which a tenant may not re-enter —
but the tenant *is* the sub-ROM, and `scv_find` / `scv_alloc` sit in
`sub/arrays.asm`, one page-local `call` away.

---

## 4. The design rule the draft's own defect wrote, applied twice

🔴 **THE LAST BOUNCE MAY NOT BE FOLLOWED BY ANOTHER.** An INT-typed factor
returns its value in **DE** (`FACTYP`=2; FAC is not written), and a CALSLT
clobbers DE. So "load the result" and "leave" must be the *same* request:
splitting them hands every `DEFINT` function a leftover register, which is
exactly the shape of the defect the 69-row battery found in the draft's own
`fn_leave` ([`deffn-impl-2026-08-22.md`](deffn-impl-2026-08-22.md) §4.2 — six
rows, six different bodies, one identical `-3392`).

Read from the other end, the same rule deletes the *string* path's last bounce
too: the result has already been snapshotted, so a bare "leave" request carries
nothing. Two dispatch arms and a tail: **−8 B, predicted 11, measured 8.**

---

## 5. 🔴 What this does NOT claim

* **The verb does not work on this branch.** `sub/deffn.asm` answers ERR 18 to
  everything, by construction, and says so in its own header. `make
  deffn-acceptance` fails 69 rows and was not run. A wall reading is a statement
  about the MAIN ROM's SIZE and about nothing else — the same standing rule as
  the scaffold in [`deffn-impl-2026-08-22.md`](deffn-impl-2026-08-22.md) §3, and
  a strictly weaker reading than that one, which at least RAN.
* **The servicer has never executed.** Its register discipline, its use of `A` as
  `subrom_call`'s documented result, and the claim that `str_eval` may be offered
  the body as well as the actuals are all UNMEASURED.
* **`ex_deffn` was not evicted.** Sketched at 52 → ~35 B, but the honest version
  needs an out-of-memory disposition the tenant cannot set (`penderr_set` is
  low-region, not page-0-tenant reachable), and that frays the estimate. FILED
  at ~10–17 B rather than guessed.
* 🔴 **The filed ~21 B `FN_WANT0` shave of `ev_fn`/`str_ev_fn` DOES NOT SURVIVE
  CONTACT.** Factoring their common prelude into an `fn_type` helper costs 11 B
  and saves 12: **1 B**, not 21. The two entries differ in their EXIT (a `ret`
  with IX, versus a `jp str_eval_ok`), and that is not shareable. Refuted, not
  deferred.

---

## 6. Where the remaining 72 B would have to come from

| source | B | status |
|---|---|---|
| cross-region dup-span carve | 43 | **measured available, not proved safe** — [`spec-basic-dupspan2.md`](spec-basic-dupspan2.md) §6; test `check_tenant_closure.py`'s blindness to `equ` FIRST |
| `ex_deffn` eviction | ~10–17 | sketched, §5 |
| `tools/clone_scout.py` near-clone refactors | ~96 est | a DIFFERENT class from dup-span: shared helpers, not `equ` aliases. 10 groups, unspent |
| passing the servicer's answer in `E` | ~9 | `subrom_call`'s own comment documents DE as a tenant argument; unverified while the tenant is a stub |

🔴 **`FN_WANT0` is NOT on this list any more.** §5.

**Per-file eviction is refuted as a source, measured rather than assumed.**
`carve_scout.py --entries` over `missing.asm`, `printusing.asm`, `list.asm`,
`usr.asm`, `repl.asm` and `field.asm` — 417 to 606 B each if they moved — all
return **NOT page-0-evictable**, with 310+ absent-region callees reached THROUGH
main page 1 apiece. `sub/deftype.asm`'s own header said so in 2026: *most
statements reach `eval`, and eval bottoms out in the float pack.*
