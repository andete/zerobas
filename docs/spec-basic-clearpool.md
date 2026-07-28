# D-CLP — the `CLEAR` string-pool partition

Status: **specced, awaiting sign-off. Not implemented.**
Characterization: [`docs/clearpool-vg8020-characterization.md`](clearpool-vg8020-characterization.md).
Gate (characterize mode today): `make clearpool-characterize` —
[`probes/basic/basic_probe_clearpool.py`](../probes/basic/basic_probe_clearpool.py),
53 rows, ten batteries. **6/51 gated rows agree**, plus 2 reported-never-gated.

Opened by the `BIN$`/`FRE` slice as D-BF-A(c). Landing it moves that slice's six
recorded-not-gated rows back into a gate.

⚠️ **§5's numbers are ESTIMATES, and this project's estimates have been wrong by
up to 100% in both directions** (`SWAP` 90–130 → 183; `FRE` 35–45 → 78; the
str-domain funding premise inverted entirely). **Step 1 of implementation is to
build the main-ROM side and measure it**, before any carve is sized — exactly
what [`docs/spec-basic-str-domain.md`](spec-basic-str-domain.md) §5 and
[`docs/spec-basic-width-domain.md`](spec-basic-width-domain.md) §4 did.

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

**New RAM: 4 bytes.**
- `POOLSIZE` (2 B) — the recorded `CLEAR n`. Initialised to 200 at cold boot;
  written only by `CLEAR <n>`. Needed as well as `POOLBASE` because §2.8
  requires the size to survive a change of ceiling.
- `POOLBASE` (2 B) — the derived boundary, `C − POOLSIZE`.

**`basic/clear.asm`** — evaluate the argument as today, then: `TMISMATCH` check
→ `type_mismatch_error`; `get_int16_checked` (already gives Overflow beyond
int16); reject negative → ERR 5; store `POOLSIZE`. The existing `clear_vars` /
`vars_reset` tail already reaches `heap_reset`, so nothing else changes here.

**`basic/str-engine.asm` `heap_reset`** — already computes
`C = min(HIMEM,TXTMAX)` and stores `FRETOP := C`. Add `POOLBASE := C − POOLSIZE`
immediately after, from the `C` it already has in `HL`. This is also what makes
§2.8 fall out for free: `,himem` moves `C`, and `POOLBASE` is re-derived from
`C` and the *recorded* size, so the pool keeps its size.

**`sub/strheap.asm`**
- `heap_alloc`'s collision floor changes from `ARYEND+2` to `POOLBASE`, and its
  failure raises **ERR 14** instead of ERR 7.
- `sh_free_gap` (i.e. `FRE("")`) becomes `FRETOP − POOLBASE`. The `strheap_gc`
  call stays — §2.5 shows reclamation is real on the reference too.
- ⚠️ The `strheap_aryend` walk disappears from both, since neither needs
  `ARYEND` any more. That walk is not free, so this direction **should return
  sub-ROM bytes**.

**`sub/arrays.asm`** — the two allocation ceilings (`scv_ceil_try` line 522,
`aal_ceil_try` line 948) change from `ld hl,(FRETOP)` to `ld hl,(POOLBASE)`, a
zero-byte swap. Their failure stays ERR 7.
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

## 5. Cost — ESTIMATED, not measured

| piece | region | estimate |
|---|---|---|
| `clear.asm` domain check + `POOLSIZE` store | main **page 1** | ~20 B |
| ERR 14 message string + table entry | main **page 1** | ~22 B |
| `heap_reset` — derive `POOLBASE` | main low region | ~12 B |
| `strheap.asm` floor + `sh_free_gap` | sub-ROM | ~0, likely **negative** |
| `arrays.asm` ceilings + dead retries | sub-ROM | likely **negative** |

Against a clean `a6323b9`: **main page 1 has 3 B free**, the low region 30 B,
the sub-ROM ~3.4 KB.

So the low-region and sub-ROM pieces are covered, and **the slice is blocked on
roughly 40 B of main page 1 that does not exist.** This is the carve
[`docs/spec-basic-width-domain.md`](spec-basic-width-domain.md) S-WID-2
predicted would be needed. `clone_scout.py` still lists `ev_*_lp` (~21 B) and
small groups in `list.asm` / `files.asm`.

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

- **S-CLP-1 — the carve.** ~40 B of main page 1 must be found before any of
  this lands. Options: (a) collapse `ev_*_lp` (~21 B by `clone_scout`, but it
  has LEAN members, so the lean cart's byte-identity must be re-proven);
  (b) the `list.asm`/`files.asm` groups; (c) promote something to the sub-ROM.
  **Recommended: measure first.** Build the main-ROM side against the current
  tree and read the actual overrun — the estimate above could be 20 B or 60 B,
  and sizing a carve against a guess is how the `SWAP` and `FRE` estimates went
  wrong.
- **S-CLP-2 — `POOLBASE` as stored state vs derived.** Stored costs 2 B of RAM
  and saves recomputing `C − POOLSIZE` at every allocation and every `FRE`.
  RAM is not the scarce resource here; ROM is. **Recommended: store it.**
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
