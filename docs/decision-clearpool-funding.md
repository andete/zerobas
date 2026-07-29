# Funding the D-CLP carve — and headroom for `DEF FN`

Measured 2026-07-28 on a clean `feed02c`. Requirement: **22 B of main page 1**
for D-CLP ([`spec-basic-clearpool.md`](spec-basic-clearpool.md) §5), and
**200–400 B** if `DEF FN` is to follow without another funding round.

---

## 1. The clone frontier is exhausted

`clone_scout.py` reports **zero candidate groups**. Every earlier slice was
funded by collapsing a clone group it belonged to; that lever is gone. The
`ev_*_lp` note carried in the roadmap was stale. **Funding must now come from
promotion to the sub-ROM** (~3.4 KB free).

## 2. Sizing by label span was the wrong signal — twice

The four candidates first proposed (`do_name` 98 B, `do_open` 94 B,
`dpl_line` 89 B, `lrset_common` 82 B) were picked by label-to-label span.
`carve_scout.py --entries` says **all four are NOT page-0-evictable**: 298–299
fatal escapes each (6 for `dpl_line`), because they reach `exec_stmt` / `eval` /
`str_eval` and the walk continues *through* main page 1 into the low region.

A second sweep — all 419 page-1 spans ≥ 14 B — found 130 "clean" labels
totalling 2973 B, but most are **internal loop labels** (`sidr_lp`, `ep_live`,
`fig_have`, `rl_loop`, `psv_loop`, `esn_p1`), not entry points. A label is not a
routine and a span is not a size. **The unit is a coherent cluster: use
`--files … --census`, which separates SHARED services that must stay resident
from the movable verb.**

## 3. What actually blocks a promotion

A page-0 tenant runs with the BIOS and the main low region switched out; main
page 1 stays mapped. So **any path that leaves the cluster into main page 1 and
from there into the low region is fatal**, and that is transitive
([[carve-scout-walk-through-page1]]).

Almost every *statement* verb is blocked by the same two things: `jp exec_stmt`
(the statement-continuation tail) and `eval`/`str_eval`. Sweeping all 209
`do_*` / `ex_*` / `ev_*` entries: **172 sit at 298–299 escapes**, 37 under 25.

## 4. ⚠️ The scout's verdict was unsound — and the first bundle was built on it

`carve_scout.py --entries` computed the BIOS closure, **printed it, and left it
out of the verdict**, which came from low-region escapes alone. A page-0 tenant
has the BIOS switched out just as surely as the low region — the tool's own
docstring says so. Fixed in `d685857`; direct BIOS escapes are now tagged
`CALSLT` (re-expressible the way `sub/format.asm`'s sub-local CALSLT write path
already does it — a **price**, not a free pass) and indirect ones are fatal.

It was not academic. With BIOS counted:

| candidate | before | after |
|---|---|---|
| `do_bload` | CLEAN | **NOT evictable** — 7 BIOS callees |
| `try_init_slot` | CLEAN | **NOT evictable** — 2 |
| `format.asm` / `do_format` | NOT | NOT, now for the right reason (7) |

**`do_bload` and `format.asm` were the two largest items in the ≈350 B bundle
this document first proposed; both leave it.** They would have built — because
`check_tenant_closure.py`, the invariant the *build* enforces, is the strict one
and always checked both regions. **The scout that decided what to attempt was
looser than the check that decides what may ship**, which is the wrong way round.

The clean set drops from 130 labels / 2973 B to **99 labels / 2303 B**.

## 4a. The viable set, corrected

Filtering the 99 for real entry points (not internal loop labels), few callers,
and gate exposure:

| candidate | size | callers | note |
|---|---|---|---|
| `tok_skip` | 51 B | 2 | tokeniser, line-entry not inner-loop |
| `fld_lookup` | 40 B | 1 | `field.asm`, from `str_eval_one` |
| `ev_ff_eof` | 33 B | 1 | `EOF(#n)` |
| `fadd_free` | 31 B | 1 | `field.asm` |
| `vst_suffix` | 29 B | 1 | `vars.asm` |
| `init_filechan` | 27 B | 1 | ⚠️ **boot-ordering blocked — see below** |
| `basic/fat.asm` `fat_io_*` cluster | ~92 B | many | only worth it as one cluster |

≈**180 B** of low-risk singles, ≈**270 B** with the FAT cluster — before stub
costs of 3–6 B per re-pointed call site.

### ⚠️ `init_filechan` is boot-ordering blocked

It was recommended as "the lowest-risk item in the set". It is not usable at
all: [`basic/interp.asm`](../basic/interp.asm) `init` calls it at line 65, but
`init_ext_roms` — which discovers the sub-ROM slot and installs the trampoline —
runs at line 67. **`init_filechan` runs before the sub-ROM is callable.**
Promoting it needs a boot reorder, which is far more than 27 B is worth. Same
class of hazard already flagged for `sub_int_install`/`try_sub_slot`; it was
simply not applied to `init_filechan`.

### Still excluded on purpose

- **`trap_return_check`** (66 B, 1 caller) — the largest clean win and the wrong
  one: on the `RETURN`-from-trap path, and the T4/T5 gates measure handler cost
  in *jiffies* ([[traps-t4-sprite-slice]]). Same for `event_poll` / `ep_live`.
- **`psv_*`** (`playsvc.asm`, 48+35+28 B) — serviced from the ISR.
- **`sub_int_install` / `try_sub_slot`** — they are what make sub-ROM calls work.
- **`gosub_push`** (40 B, 3 callers) — hot control flow.
- **`parse_disk_fcb`** (28 B, 10 callers) — the stubs cost more than the move.

## 5. The near-misses — re-measured, and there is no cheap structural carve

⚠️ **§5 previously claimed `do_save` was "5 escapes from clean" and that
duplicating `div10` sub-side would unlock `save.asm`'s 572 B. That was the
BIOS-blind tool talking, and it is wrong.** With BIOS counted `do_save` has
**12** escapes:

| escape | why it is not a detail |
|---|---|
| `TAPOON` / `TAPOUT` / `TAPOOF` | `SAVE"CAS:"` writes tape **in real time** through the BIOS |
| `CHPUT` / `LPTOUT` / `CALSLT` | console + printer output |
| `div10` / `d10_lp` / `d10_skip` | via `list_walk`→`list_num`, ASCII SAVE detokenising a line number |
| `subrom_call` / `subrom_absent_error` | cluster-local plumbing, re-expressible |

The tape entries are the core of what `SAVE` *is*, and tape I/O is timing-
critical ([[tape-realtime-read-buffering]]) — reaching them through `CALSLT`
from a tenant is a hazard, not a cost. **`do_save` is not a near-miss.**

**And a page-1 tenant does not rescue it either.** A page-1 tenant sees the BIOS
and the low region but *not* main page 1 — which would suit `do_save`'s BIOS and
`div10` escapes exactly. But its closure also runs through `list_walk`/`list_num`
(`list.asm`), `pchar`/`pch_file` (`print.asm`) and `load_error` (`bload.asm`,
**52 callers**) — all main page 1. Blocked on the other axis.

Re-running the whole verb sweep with BIOS counted: of 209 `do_*`/`ex_*`/`ev_*`
entries, the genuinely clean ones are **26 small evaluator leaves totalling
293 B** (average 11 B) — `ev_f_*` deferred-error factors, `ev_ff_*` file and
input-device functions, `ex_end`, `ex_rem`. Bundling them behind one
index-dispatched tenant (the `evmc_*` pattern) would net **≈163 B after ~5 B of
stub per site**, spread over 26 routines that touch the input-devices, file,
cursor and error gates. **Poor value for the gate surface.**

`str_get_key` remains 2 escapes, both `ary_engine_call` — a tenant calling a
tenant, which is a nesting question, not a byte question.

## 6. Recommendation, corrected

1. **To unblock D-CLP (22 B): `tok_skip` (51 B, 2 callers) or `fld_lookup`
   (40 B, 1 caller).** Either alone funds the partition with margin, and neither
   is near a timing gate, the ISR, or the boot ordering.
2. **`DEF FN`'s 200–400 B is reachable by leaf bundling only just, and at poor
   value** — five to eight separate promotions for ≈180–270 B gross, each a new
   tenant index, ABI entry, stub and closure re-check, each adding gate surface.
3. **There is no cheap carve for `DEF FN`, in either direction.** §5 shows the
   structural near-misses are not near, and §4a shows the leaf bundle is poor
   value. The 567–1814 B prizes are real but each requires genuinely splitting
   an eval-bound verb into a resident parse stub plus a tenant body — design
   work with its own spec and gate, not a move. **`DEF FN`'s funding should be
   scoped as part of the `DEF FN` arc, not bolted onto D-CLP.**

⚠️ **Each promotion is a new tenant index, an ABI entry, a resident stub and a
closure re-check, and every one of them changes the DISK path.** The corpus
re-run is part of the work, not a follow-up — "builds green but was never run"
is this project's standing trap.

---

## 6.1 ✅ LANDED — `fld_lookup`, and the seam is not where §4a said it was

`fld_lookup` was taken over `tok_skip`, and the reason is one §4a's table does
not show: **`tok_skip`'s two callers are per-token LOOPS** (`if_skip_to_else`
and `skip_to_eol`, [`basic/interp.asm:1335`](../basic/interp.asm:1335)), so a
CALSLT at either site is paid once per token of every line walked — the whole
program-relink path. "2 callers" reads cheap in a caller count and is not.
`fld_lookup`'s single caller runs once per read of a FIELDed variable, already
downstream of a 512-byte `fch_select` LDIR pair.

⚠️ **The scout's CLEAN verdict was necessary, not sufficient, and re-reading its
own output is what showed why.** `--entries fld_lookup` prints

    directly called by the moved code : 1 (0 plumbing, re-expressible)
        BLOCKER   mk_rvdesc @ $287F
    reached THROUGH resident main page-1 : 0  <- FATAL if > 0
    VERDICT: page-0-tenant CLEAN

The verdict comes from the *indirect* count alone, by design (§4's fix made
BIOS callees fatal when indirect and a priced `CALSLT` when direct). So CLEAN
means "no unrewritable escape", **not** "move it and it works": `mk_rvdesc` is
main LOW REGION and is switched out under a page-0 CALSLT, and the other two
callees (`fld_find`, `fch_select`) are main PAGE 1 — legal in principle, but
the sub-ROM has **no import mechanism for main page-1 addresses**.
[`sub/basic-resident-abi.inc`](../sub/basic-resident-abi.inc) is generated with
a `< $3FE5` ceiling check because it exists for the opposite direction (page-1
tenants calling the low region). No page-0 tenant has ever called main page 1.

So the carve was **split at the table lookup, not at the routine boundary**:

| piece | side | why |
|---|---|---|
| `fld_find` + `fch_select` | resident stub | shared services with other callers (`fld_find` for LSET/RSET, `fch_select` for the whole file-channel surface) — neither could have moved, so keeping them costs the carve nothing |
| slice copy + descriptor build | tenant (`sub/fldlook.asm`, index 12) | a pure RAM leaf |
| `mk_rvdesc` | inlined sub-side (10 B) | cheaper and less fragile than a second generated address-import file |

The located entry pointer rides in **HL**, which `subrom_call` passes straight
through CALSLT — nothing marshals through a param block. `subrom_call`'s CF
means "sub-ROM absent" and never "found", so the stub asserts the found-CF
itself; it is the side that ran `fld_find`.

**Measured, from clean: page-1 free 3 B → 41 B. The carve returned 38 B**
(60 B of body out, 22 B of stub back), against D-CLP's 22 B requirement.
Lean `basic.rom` byte-identical; all three closure gates green; `unit-test`
53/53; `diskbasic-acceptance-repack` **32/34, the same two failures the HEAD
baseline has** (`GET(RDBLK)`, `CALL FORMAT` — both reproduced on `2a29b66`
with the carve stashed, so neither is this change; `CALL FORMAT` reads its BPB
as all-`$E5` on both the 720K and 360K menus, which is its own item).

**Falsified before believed:** a `ret` inserted at `fld_lookup_tenant`'s first
instruction turns `FIELD/LSET/RSET` RED (`differential: FAIL — CF-3300 differs`)
and restoring it turns it green again — so the gate is measuring the tenant, not
agreeing by luck.

### What the carve returned, and what it cost

| | before | after |
|---|---|---|
| main page 1 free | 3 B | **41 B** (carve) → **10 B** (D-CLP built in) |
| main low region free | 30 B | **4 B** |

Both walls are now very tight, and `clone_scout.py` still reports zero groups —
**the next slice needs its own promotion, and page-0 index 12 was the last row
that fits** (see below). The remaining viable singles from §4a are `ev_ff_eof`
(33 B), `fadd_free` (31 B), `vst_suffix` (29 B) and the `fat_io_*` cluster
(~92 B); each now costs a page-1 tenant index or a table relocation.

⚠️ **Index 12 is the LAST page-0 index that fits.** The entry table starts at
`$0010` and the `$0038` interrupt-trampoline vector is fixed: 13 rows × 3 B ends
at `$0036`, leaving **one** spare byte. A fourteenth page-0 tenant needs the
table moved (or a row that `jp`s onward), not just another line.
