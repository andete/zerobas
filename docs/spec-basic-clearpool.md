# D-CLP — the `CLEAR` string-pool partition

Status: **specced, awaiting sign-off. Not implemented.**
Characterization: [`docs/clearpool-vg8020-characterization.md`](clearpool-vg8020-characterization.md).
Gate (characterize mode today): `make clearpool-characterize` —
[`probes/basic/basic_probe_clearpool.py`](../probes/basic/basic_probe_clearpool.py),
53 rows, ten batteries. **6/51 gated rows agree**, plus 2 reported-never-gated.

Opened by the `BIN$`/`FRE` slice as D-BF-A(c). Landing it moves that slice's six
recorded-not-gated rows back into a gate.

✅ **§5 is now MEASURED, not estimated** — the main-ROM side is built and gated
behind `CLEARPOOL`. The first estimate said ~40 B of page 1; the measurement
says **22 B, and nothing in the low region**. Both corrections came from
building it, which is what S-CLP-1 asked for.

---

## 1. What is wrong

zerobas has **one free gap**; the reference has **two pools**. Strings allocate
down from a ceiling `C` into `[FRETOP, C)` and variables/arrays grow up to
`ARYEND`; `heap_alloc` fails only when the two meet. `CLEAR`'s `<string-space>`
argument is evaluated and thrown away
([`basic/clear.asm:61`](../basic/clear.asm:61)).

Consequences, all measured (characterization §2):

| # | surface | reference | zerobas |
|---|---|---|---|
| D-CLP-1 | `CLEAR n : FRE("")` | exactly `n` | the whole gap (~15867) |
| D-CLP-2 | free string space at boot | 200 | the whole gap |
| D-CLP-3 | a string body's cost to `FRE(0)` | 6 (the entry only) | 6 + the body |
| D-CLP-4 | exhausting the pool | `Out of string space` (ERR 14) | no error until RAM runs out |
| D-CLP-5 | `CLEAR -1` / `32768` / `"200"` | IFC / Overflow / Type mismatch | **nothing** |
| D-CLP-6 | `CLEAR 500,&H9000` | pool still 500 | gap shrinks to 4091 |

## 2. The contract to implement

From characterization §2, all measured:

1. `CLEAR n` sizes the pool to **exactly** `n`; `100.7` truncates to 100.
2. The boot default is **200**, and a **bare `CLEAR` keeps the current size** —
   `CLEAR 500 : CLEAR` reads 500. So do `NEW`, `RUN`, and `CLEAR ,himem`.
3. The pool is **carved from the same RAM**: `FRE(0)` drops by exactly the
   difference in pool size (3800 across `CLEAR 200` → `CLEAR 4000`).
4. A body is charged to the string pool, its **entry** to the variable pool.
5. `B$=A$` **copies** — the pool is charged per reference, not per body.
   A dead body is reclaimed; a pure temp is fully given back.
6. Overflowing the pool is **`Out of string space` (ERR 14)** and the failed
   allocation is **rolled back** — the pool reads its full size afterwards.
7. `CLEAR n`'s argument obeys the two-stage int16 rule plus a type check.
8. `,himem` does not resize the pool.

## 3. The design

A **single moving boundary**, not a second allocator — §2.1 of the
characterization (the exact 3800 difference) is what licenses this.

**New RAM: 2 bytes.**
- `POOLSIZE` (2 B, `$E232`) — the recorded `CLEAR n`. Initialised to 200 at cold
  boot; written only by `CLEAR <n>`, and deliberately not reset by `NEW`, `RUN`,
  a bare `CLEAR` or `CLEAR ,himem` (§2.4).
- **No `POOLBASE` cell** — the boundary is derived where it is used, sub-side
  (S-CLP-2, reversed; see §7).

**`basic/clear.asm`** — evaluate the argument as today, then: `TMISMATCH` check
→ `type_mismatch_error`; `get_int16_checked` (already gives Overflow beyond
int16); reject negative → ERR 5; store `POOLSIZE`. The existing `clear_vars` /
`vars_reset` tail already reaches `heap_reset`, so nothing else changes here.

**`basic/str-engine.asm` `heap_reset`** — **unchanged.** It was going to derive
the boundary here, but that spends the scarce low region on something the
sub-ROM can compute for itself (S-CLP-2, reversed). §2.8 still falls out for
free: `,himem` moves the ceiling and never touches `POOLSIZE`, so a boundary
re-derived at each use picks the change up automatically.

**`sub/strheap.asm`**
- a small sub-local helper yields the floor: `min(HIMEM,TXTMAX) − POOLSIZE`,
  from two published sysvars plus the recorded size.
- `heap_alloc`'s collision floor changes from `ARYEND+2` to that, and its
  failure raises **ERR 14** instead of ERR 7.
- `sh_free_gap` (i.e. `FRE("")`) becomes `FRETOP − floor`. The `strheap_gc`
  call stays — §2.5 shows reclamation is real on the reference too.
- ⚠️ The `strheap_aryend` walk disappears from both, since neither needs
  `ARYEND` any more. That walk is not free, so this direction **should return
  sub-ROM bytes**.

**`sub/arrays.asm`** — the two allocation ceilings (`scv_ceil_try` line 522,
`aal_ceil_try` line 948) change from `ld hl,(FRETOP)` to the derived floor. Their failure stays ERR 7.
- ⚠️ **Their GC-retry arms become dead code.** They retry once via `strheap_gc`
  because `FRETOP` can move; `POOLBASE` cannot. Removing both retries should
  return sub-ROM bytes and simplify two frames (the `RETRIED` slot in each IY
  frame goes with them).

**`basic/interp.asm`** — `err_msgtab` entry 14 currently points at
`err_unprintable` ([`basic/interp.asm:939`](../basic/interp.asm:939)). Point it
at a new `out of string space` string. ⚠️ **Put the string where `LOCATE` put
ERR 24's, not next to the table**: [`basic/missing.asm:70`](../basic/missing.asm:70)
records that inserting bytes beside `err_msgtab` pushes page 1's dense forward
`jr`s out of reach.

## 4. Scope boundary

**In:** everything in §2.

**Out:**
- **`DIM Q(20000)` → `Subscript out of range`.** Found by a calibration row
  (characterization §3); the reference bounds a dimension before allocating and
  zerobas allocates until it fails. An ARRAYS-arc divergence, unrelated to the
  pool. Recorded, not fixed here.
- **`hold-literal` in a STORED program.** §2.5 measured the direct-mode cost of
  `A$="ABCDE"` as 5 bytes of pool. A stored program may point the descriptor
  into the program text instead of copying, costing nothing. **Unmeasured** —
  see S-CLP-4.
- **`Out of string space` from the temp-descriptor stack.** The temp pool
  (`TEMPTOP`/`TEMPBASE`) is a separate structure with its own overflow; whether
  the reference reports ERR 14 or ERR 16 there is not measured.

## 5. Cost — MEASURED (main-ROM side), 2026-07-28

The main-ROM side is **written and gated behind `CLEARPOOL`** (`basic/sysvars.inc`,
default 0, forced 0 in the lean build so byte-identity is structural). Measured
from clean, with `SWAP_RESIDENT=0` as the lever so both configurations fit and
the deltas are exact:

| piece | region | measured | available | short |
|---|---|---|---|---|
| `clear.asm` domain check + `POOLSIZE` store, cold-boot default | main **page 1** | **25 B** | 3 B | **22 B** |
| ERR 14 message string | main low region | **22 B** | 30 B | — (8 B spare) |
| `heap_alloc` floor + `sh_free_gap` + the array ceilings | sub-ROM | not yet built | ~3.4 KB | — |

**So the carve is 22 B of main page 1, and nothing in the low region** — not the
~40 B this section first estimated, and not the "22 B + 2 B" of the first
measurement either. S-CLP-1 said measure before sizing it, and it was worth
doing twice. (Cross-check on the lever: `SWAP` off is worth 201 − 3 = 198 B of
page 1, exactly the figure recorded when it landed.)

**The low-region requirement disappeared by reversing S-CLP-2** — see §7.

The `clear.asm` block came down 27 B → 25 B by testing the sign in place
(`bit 7,d` + `jp nz,gb_illegal`, 5 B) instead of `ld a,d`/`rla`/`jr c` plus a
local `jp` (7 B).

⚠️ **`clone_scout.py` now reports ZERO candidate groups** — the clone frontier is
exhausted and this document's earlier `ev_*_lp` note was stale. Funding must
come from a **promotion to the sub-ROM**. Largest main-page-1 label spans (a
scouting signal, *not* routine sizes — [[promotion-funds-low-region]]):
⚠️ **and all four of those disk verbs are NOT page-0-evictable** —
`carve_scout.py` reports 298–299 fatal escapes each, because they reach
`exec_stmt`/`eval`/`str_eval` and the walk continues through main page 1 into
the low region. Each would need splitting into a resident parse stub plus a
tenant body: a redesign, not a move.

A sweep of all 419 page-1 spans ≥ 14 B found **130 that ARE page-0-tenant
clean, totalling 2973 B**. The useful ones pair size with FEW call sites, since
each site becomes a stub:

| candidate | size | callers | note |
|---|---|---|---|
| `init_filechan` | 27 B | 1 | boot-time, closure of 4 — **the lowest-risk in the list** |
| `psv_fetch` | 48 B | 1 | `PLAY` string-variable fetch, parse-time |
| `tok_skip` | 51 B | 2 | tokeniser, line-entry not inner-loop |
| `trap_return_check` | 66 B | 1 | ⚠️ **NO** — see below |

⚠️ **Not `trap_return_check`, despite being the largest single win.** It sits on
the `RETURN`-from-trap path, and the T4/T5 gates measure handler cost in
*jiffies* — sub-ROM call overhead there lands exactly where those gates look
([[traps-t4-sprite-slice]]: "the divergence was the handler's own cost").

## 6. The gate

`make clearpool-characterize` today; `make clearpool-acceptance` (with
`--gate`) once the slice lands. Ten batteries: `ctl` (6), `repro` (4),
`size` (9), `hold` (7), `indep` (4), `oos` (7), `dflt` (6), `dom` (5),
`hmem` (3), `rep` (2, never gated).

Three properties are load-bearing and are documented in the probe:

- **`FRE("")` is the one machine-independent memory readout**, which is what
  makes absolute rows legitimate here and nowhere else.
- **The oracle is checked against its own recorded answers** (`REPRO_EXPECT`)
  before any verdict is read as a finding.
- **No line may reach 40 characters**, enforced by an apparatus guard that runs
  before any emulator boots — the wrapped-echo fault made eleven rows of the
  first run read `<none>` *on the reference*, several of which then scored PASS
  against a zerobas `<none>` (characterization §1.3).

## 7. Sign-off questions

- **S-CLP-1 — the carve. ✅ MEASURED AND SCOUTED — see
  [`docs/decision-clearpool-funding.md`](decision-clearpool-funding.md).**
  The requirement is **22 B of main page 1 + 2 B of low region** (§5), and the
  clone frontier is dry, so it has to be a promotion to the sub-ROM. The
  candidates are disk verbs whose siblings are already tenants:
  **`do_name` (~98 B, the `NAME` rename statement)** — recommended, since it is
  the most self-contained and least-used of the four; `do_open` (~94 B) and
  `lrset_common` (~82 B) are on the hot file-channel path and their closures
  reach further; `dpl_line` (~89 B) belongs to `LIST`, which is console-coupled.
  A promotion needs its own closure walk ([[carve-scout-walk-through-page1]]:
  continue THROUGH main page-1 callees, not up to them) and returns far more
  than 22 B, so it also restores headroom for `DEF FN`.
  Requirement **22 B of main page 1**. The clone frontier is exhausted, so it
  must be a promotion; the viable set is `format.asm` (132 B), `do_bload`
  (~99 B), `tok_skip` (51 B), `fld_lookup` (40 B) and `init_filechan` (27 B),
  ≈350 B gross. **`init_filechan` alone funds D-CLP** and is the lowest-risk
  change available; the rest are for `DEF FN`'s headroom.

- **S-CLP-2 — `POOLBASE` stored vs derived. ✅ REVERSED, and the reversal is
  what removed the low-region blocker.** The original recommendation was to
  store it, reasoning "RAM is not the scarce resource, ROM is". That was right
  about RAM and wrong about *which* ROM: the scarce one is the **low region**
  (30 B), where `heap_reset` lives — while the sub-ROM, which is the only
  consumer of the boundary, has ~3.4 KB. Deriving it sub-side as
  `min(HIMEM,TXTMAX) − POOLSIZE` from two published sysvars plus the recorded
  size costs the low region **zero** bytes and still makes `CLEAR ,himem` keep
  its size (§2.8) — that form moves the ceiling and never touches `POOLSIZE`,
  so re-deriving picks the change up for free. There is now **no `POOLBASE`
  cell**; `$E234..$E23F` stays free.

- **S-CLP-3 — the default 200 at cold boot.** This changes behaviour for every
  existing program: today any string workload has ~15 KB, after this it has
  200 bytes unless it says otherwise. That is *correct* (it is what the
  reference does, and the charter is faithful MSX1 BASIC), but it is the single
  most user-visible change in the slice and it will make previously-working
  test programs raise `Out of string space`. **Recommended: take it, and
  re-run the full acceptance corpus** — `string-acceptance`, `diskbasic-*`, the
  arrays gates — because several fixtures allocate strings freely.
- **S-CLP-4 — the stored-program literal.** §2.5 measured `A$="ABCDE"` costing
  5 bytes of pool in DIRECT mode. If a stored program instead points into the
  program text, the pool accounting differs and a `hold` row would be wrong for
  stored programs. **Recommended: measure it before implementing** — it is two
  more probe rows and it changes what `heap_alloc` must do for a literal.
- **S-CLP-5 — `B$=A$` copies.** §2.5 measured the pool charged twice. zerobas's
  descriptor model shares bodies. Making assignment copy is a string-engine
  semantic change beyond the partition itself. Is it in scope, or does the
  slice land the partition and leave sharing as a documented deviation with its
  `hold-alias` row reported-not-gated? **Recommended: leave it out and report
  the row**, so the partition lands on its own; sharing is a second slice.
