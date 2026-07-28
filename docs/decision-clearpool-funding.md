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

## 5. The near-misses, for later

Worth a targeted restructure rather than a move, and each is its own slice:

- **`do_save` / `ex_save` — 5 escapes.** Three are `div10`/`d10_lp`/`d10_skip`
  reached via `sav_ascii_flag`→`list_walk`→`list_num` (ASCII SAVE detokenising
  a line number); the other two are cluster-local plumbing. Duplicating `div10`
  sub-side, or moving `list_walk` with it, unlocks **`save.asm`'s 572 B**.
- **`str_get_key` — 2 escapes**, both via `ary_engine_call`: a tenant calling
  another tenant.
- The four disk verbs of §2 return **567–1814 B** each *if* split into a
  resident parse stub plus a tenant body. That is the structural carve, and it
  is where the real headroom is.

## 6. Recommendation, corrected

1. **To unblock D-CLP (22 B): `tok_skip` (51 B, 2 callers) or `fld_lookup`
   (40 B, 1 caller).** Either alone funds the partition with margin, and neither
   is near a timing gate, the ISR, or the boot ordering.
2. **`DEF FN`'s 200–400 B is reachable by leaf bundling only just, and at poor
   value** — five to eight separate promotions for ≈180–270 B gross, each a new
   tenant index, ABI entry, stub and closure re-check, each adding gate surface.
3. **The efficient path to `DEF FN` headroom is the structural carve of §5,
   not a bundle.** `do_save` is 5 escapes from clean and three of them are one
   helper (`div10`); clearing it unlocks **`save.asm`'s 572 B in a single
   move**, and the four disk verbs return 567–1814 B each if split into a
   resident parse stub plus a tenant body. One restructure beats eight moves.

⚠️ **Each promotion is a new tenant index, an ABI entry, a resident stub and a
closure re-check, and every one of them changes the DISK path.** The corpus
re-run is part of the work, not a follow-up — "builds green but was never run"
is this project's standing trap.
