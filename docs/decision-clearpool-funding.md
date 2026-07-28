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

## 4. The viable set

⚠️ `--entries` vets **one entry's** closure and does not know which routines are
moving with it. Where an escape's path runs through a routine *in the same
cluster*, it is re-expressible: a tenant does not need `subrom_call` because it
**is** the sub-ROM. Those are marked below.

| cluster | movable | verdict |
|---|---|---|
| [`basic/format.asm`](../basic/format.asm) (`CALL FORMAT`) | **132 B**, 0 shared | `do_format`'s single escape is `subrom_call` via `fmt_menu`→`fmt_sel_720`, **both in the file** → re-expressible. **Clean.** |
| [`basic/bload.asm`](../basic/bload.asm) `do_bload` | **~99 B** (76 private + 23) | **0 escapes.** Its two direct callees are `subrom_call`/`subrom_absent_error`, plumbing. **Clean.** ⚠️ `parse_close_run` (46 B, 6 callers) and `load_error` (52 callers) must stay resident. |
| `tok_skip` | 51 B, 2 callers | clean; tokeniser, line-entry not inner-loop |
| `fld_lookup` | 40 B, 1 caller | clean; `field.asm`, called from `str_eval_one` |
| `init_filechan` | 27 B, 1 caller | clean; boot-time, closure of 4 — **lowest risk in the set** |

**≈ 350 B gross**, less ~3–6 B per re-pointed call site. That funds D-CLP's
22 B and leaves `DEF FN` a real budget.

### Excluded on purpose

- **`trap_return_check`** (66 B, 1 caller) — the largest single clean win, and
  the wrong one. It is on the `RETURN`-from-trap path and the **T4/T5 gates
  measure handler cost in jiffies**, so sub-ROM call overhead lands exactly
  where those gates look ([[traps-t4-sprite-slice]]). Same reason for
  `event_poll` and `ep_live`. **A candidate's risk is which gate it sits under,
  not its size.**
- **`sub_int_install` / `try_sub_slot`** (`subrom-boot.asm`) — these are what
  make sub-ROM calls work at all. Chicken-and-egg.
- **`psv_*`** (`playsvc.asm`) — serviced from the ISR; page-1 tenants run under
  `DI` precisely so the ISR cannot fire mid-tenant.
- **`parse_disk_fcb`** (28 B) — 10 callers; the stubs cost more than the move.

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

## 6. Recommendation

1. **`init_filechan` alone (27 B, 1 caller, boot-time) funds D-CLP** and is the
   safest change in this document. If the goal is just to unblock the partition,
   stop there.
2. For `DEF FN` headroom, add **`format.asm` (132 B)** and **`do_bload`
   (~99 B)** — both self-contained, both with existing disk gates
   (`diskbasic-acceptance`, `fat-error-acceptance`, `bdos-acceptance`) that must
   be re-run because they are disk-path changes.
3. Leave the near-misses of §5 to their own slice.

⚠️ **Each promotion is a new tenant index, an ABI entry, a resident stub and a
closure re-check, and every one of them changes the DISK path.** The corpus
re-run is part of the work, not a follow-up — "builds green but was never run"
is this project's standing trap.
