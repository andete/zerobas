# D-CLP — the `CLEAR` string-pool partition

Status: ✅ **LANDED.** `make clearpool-acceptance` — **51/51 gated rows**,
6 reported-never-gated (see §6). Funded by promoting `fld_lookup` to a page-0
sub-ROM tenant ([`decision-clearpool-funding.md`](decision-clearpool-funding.md) §6.1).
Characterization: [`docs/clearpool-vg8020-characterization.md`](clearpool-vg8020-characterization.md).
Gate: `make clearpool-acceptance` (`--gate`) —
[`probes/basic/basic_probe_clearpool.py`](../probes/basic/basic_probe_clearpool.py),
57 rows, twelve batteries. **51/51 gated rows agree**, plus 6 reported-never-gated
for three distinct reasons (§6). `make clearpool-characterize` is the same probe
without `--gate`. It read **6/51** before this slice.

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

**`sub/strheap.asm`** — ✅ built.
- `strheap_floor` yields `min(HIMEM,TXTMAX) − POOLSIZE`, from two published
  sysvars plus the recorded size, clamped at 0 (a user-set `HIMEM` can express
  a ceiling below the requested pool; letting the subtraction wrap would put the
  floor ABOVE the ceiling and hand out bodies over the top of RAM).
- `heap_alloc`'s collision floor changes from `ARYEND+2` to that — **no `+2`**:
  the old one cleared the live 2-byte `$0000` array sentinel, whereas the pool
  OWNS its floor address, and `CLEAR 100` then a 100-byte string must land
  exactly on it and read `FRE("")` = 0.
- Its failure raises **ERR 14** instead of ERR 7. ⚠️ The main-ROM glue does that
  by routing `SH_ERR=1` through a **different FPERR code** (`FPERR_STROOM`,
  `basic/sysvars.inc`) rather than a different code path — the five sites were
  already `ld a,<code>`, so the whole change costs **one byte**, the 11th entry
  in `fperr_to_err`. Array allocation failures keep FPERR=6/ERR 7 on purpose.
- `sh_free_gap` (i.e. `FRE("")`) becomes `FRETOP − floor`. The `strheap_gc`
  call stays — §2.5 shows reclamation is real on the reference too.
- ⚠️ **`FRE(n)` needed a second handler, which this section did not anticipate.**
  Both forms used to share op 15 because zerobas had one gap. With the pool real
  they answer different questions, so `FRE(n)` is a new op 17 `sh_free_vars` =
  `floor − (ARYEND+2)` — and that one takes **no** GC, deliberately: GC moves
  string bodies and cannot move either `ARYEND` or the floor, so it could not
  change the answer by a byte. Left on op 15, `FRE(0)` reads 200 at boot and the
  probe's `ctl-fre0` control catches it.
- ⚠️ **The PEAK, not the steady state, is what a sized pool measures — and
  zerobas's peak was 3×.** `A$=STRING$(100,"A")` charged 300 bytes at its high
  water mark (the `STRING$` temp, `str_set_key`'s H1 snapshot of it, and the
  variable's own body) where the reference charges 100. `FRE("")` hid it because
  FRE GCs first, so the resting number looked right while `CLEAR 100 :
  A$=STRING$(100,"A")` — which the reference accepts exactly — raised ERR 14.
  Two changes bring it to 1×, and each is falsifiable on its own row:
  op 16 `she_snap_keep` returns a source that is ALREADY a temp unchanged
  (str_set_key's own header always said temp sources were never exposed to the
  staleness hazard the snapshot exists for), and `sh_var_store` **adopts** a
  temp's body instead of allocating a second one, zeroing the temp's descriptor
  so one body never has two GC roots.
- The `strheap_aryend` walk leaves `heap_alloc` and `sh_free_gap`; it stays in
  the file for `sh_free_vars` and `scv_alloc`.

**`sub/arrays.asm`** — ✅ built. The two allocation ceilings (`scv_ceil_try`,
`aal_ceil_try`) change from `ld hl,(FRETOP)` to the derived floor. Their failure
stays ERR 7 — an array that will not fit ran out of VARIABLE space.
- ⚠️ **Their GC-retry arms are dead code and are gone.** They retried once via
  `strheap_gc` because `FRETOP` can move; the floor cannot. `aal_ceil_try`'s
  `push ix`/`pop ix` (which existed only to guard `strheap_gc`'s IX clobber)
  goes with it. The `RETRIED` slot in each IY frame is left ALLOCATED but
  unused: every later frame offset is absolute, and renumbering six of them to
  reclaim one byte of stack is a poor trade.
- `tests/test_arrays.py` case 8d asserted the retry (a tight FRETOP collides,
  GC recomputes it, the retry succeeds). It now asserts the opposite — a tight
  FRETOP is IRRELEVANT and provokes no GC — plus a new 8d2 proving the FLOOR is
  what bounds the region. Restoring `ld hl,(FRETOP)` turns both red.

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
- **`hold-literal` in a STORED program — ✅ MEASURED, and it stays OUT.**
  Direct `A$="ABCDE"` costs 5; `10 A$="ABCDE" : RUN` costs **0**, and so does a
  25-char literal, so it is zero rather than slack (characterization §2.5).
  The reference points a stored literal's descriptor straight at the program
  text. S-CLP-4 expected this to change `heap_alloc`; it does not — charging
  zero requires **storing by reference**, which is S-CLP-5's body-ownership
  question, not a pool question. Reported by the probe's `share` battery.
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

✅ **AS BUILT, from clean.** The carve (`fld_lookup` → a page-0 tenant) returned
38 B of page 1, and the finished slice spends 31 B of it plus 26 B of low region:

| wall | pre-carve | post-carve | as shipped |
|---|---|---|---|
| main page 1 free | 3 B | **41 B** | **10 B** |
| main low region free | 30 B | 30 B | **4 B** |

The 25 B page-1 figure above was the flag alone; the finished slice added 5 B for
`FRE`'s two-op split (§3) and 1 B for `fperr_to_err`'s 11th entry. The low
region's 22 B is the ERR 14 string plus 4 B for `str_snapshot_keep`'s entry head.
Both walls are now very tight — the next slice needs its own carve, and
[`decision-clearpool-funding.md`](decision-clearpool-funding.md) §6.1 records
that **page-0 tenant index 12 was the last one that fits**.

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

## 6. The gate — ✅ 51/51

`make clearpool-acceptance`. Twelve batteries: `ctl` (6), `repro` (4),
`size` (9), `hold` (7), `indep` (4), `oos` (7), `dflt` (6), `dom` (5),
`hmem` (3), and three that are REPORTED, NEVER GATED — for three *different*
reasons, which the battery names carry:

| battery | rows | why it can never be gated |
|---|---|---|
| `rep` | 2 | `FRE(0)` absolutes — a property of each machine's memory map |
| `share` | 3 | body OWNERSHIP (S-CLP-5, out of scope): zerobas owns a body per variable, the reference decides per source |
| `arr` | 1 | the ARRAYS-arc `DIM Q(20000)` divergence, found in passing (§4) |

⚠️ **`oos-vs-oom` was measuring two claims at once and has been SPLIT.** As
written it asserted both "out of string space is distinct from out of memory"
(a D-CLP claim, and true) and "which non-string error a huge DIM gives" (an
ARRAYS-arc claim, and divergent). The first is now gated on `DIM Q(5000)`,
which overruns free variable space on *both* machines; the second is the `arr`
row. Neither was silenced.

Three properties are load-bearing and are documented in the probe:

- **`FRE("")` is the one machine-independent memory readout**, which is what
  makes absolute rows legitimate here and nowhere else.
- **The oracle is checked against its own recorded answers** (`REPRO_EXPECT`)
  before any verdict is read as a finding.
- **No line may reach 40 characters**, enforced by an apparatus guard that runs
  before any emulator boots — the wrapped-echo fault made eleven rows of the
  first run read `<none>` *on the reference*, several of which then scored PASS
  against a zerobas `<none>` (characterization §1.3).

## 6a. The corpus is part of the work (S-CLP-3)

The 200-byte default is the most user-visible change in the slice, and it moved
fixtures in three different ways. All of these are the gate working, not the
gate being wrong:

| gate | what moved |
|---|---|
| `unit-test` (5 string files) | they emulate a cold boot by calling `heap_reset`, which does **not** set `POOLSIZE` — a real boot does that in `init`, ahead of `clear_vars`, and NEW/RUN/bare-CLEAR all deliberately keep the current size. Left at 0 the pool is **zero bytes wide**; they now seed it, as the harness's stand-in for the boot step |
| `unit-test` `test_arrays.py` | case 8d asserted the GC retry this slice deletes; re-pointed at the new contract, plus a new 8d2 proving the FLOOR is the bound |
| `array-acceptance` (12 rows) | the GC-stress and H1 churn cases were sized against zerobas's **old ~15.8 KB single gap** and now say `CLEAR 4000` / `CLEAR 14000` / `CLEAR 15000` explicitly. The heap they wanted is the heap they now ask for |
| `array-acceptance` `gc.bugB.phantom` | ⚠️ its window no longer exists — see below |

⚠️ **`gc.bugB.phantom` needed re-targeting, not re-sizing.** It required an
allocation to FAIL between the scalar insert and the store. After this slice,
`str_set_key`'s `SH_SRC` is always either a temp (adopted — cannot fail) or
`STR_EMPTY` (length 0 — trivially succeeds), so **`sh_var_store`'s OOM branch is
unreachable from the scalar LET path**; and `scv_ceil_try`'s GC-retry is gone, so
no GC runs in that window either. Those two facts were exactly what made a stale
slot observable as a live phantom root, so **BUG B's hazard is structurally
absent rather than merely untriggered**. The zero-fill itself is asserted
directly — and more strongly — by `tests/test_arrays.py`, which reads the slot
immediately after `scv_alloc` with no store in between. The probe case now pins
the surviving observable half: a fresh slot must be OWNED by the store, never
left holding whatever bytes were there.

Green after the fix-ups: `unit-test` 53/53, `array-acceptance` **149/151 — the
same two `ifc.instr.*` message-case rows that fail on the pre-slice baseline**,
`string-acceptance`, `str-domain-acceptance` 89/89, `abort-acceptance` 23/23,
`intarg-acceptance`, `missing-acceptance`, `width-acceptance` 76/76.

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
- **S-CLP-4 — the stored-program literal. ✅ MEASURED 2026-07-29, and the
  answer moved it into S-CLP-5.** Direct `A$="ABCDE"` costs 5 bytes of pool;
  `10 A$="ABCDE" : RUN` costs **nothing**, and a 25-char stored literal also
  costs nothing — so the answer is zero, not accounting slack. The reference
  points a stored literal's descriptor at the program text, whose bytes are
  permanent; a direct line's buffer is transient, so there it must copy.
  The question was phrased as "it changes what `heap_alloc` must do for a
  literal" — **it does not**. Charging zero requires storing by REFERENCE,
  which is S-CLP-5's machinery, so both rows are `share`-battery (reported,
  never gated) rather than something this slice implements.
  ⚠️ Worth recording before anyone builds it: a variable body that points into
  program text means `MID$(A$,1,1)="X"` writes into the **program**.
- **S-CLP-5 — `B$=A$` copies. ✅ SIGNED OFF: out of scope, report the row.**
  §2.5 measured the pool charged twice. zerobas's descriptor model shares
  bodies. Making assignment copy is a string-engine semantic change beyond the
  partition itself, so the slice lands the partition and leaves sharing as a
  documented deviation.
  ⚠️ S-CLP-4's result shows this is **one difference in two directions**, which
  is why no pool arithmetic reconciles either row: zerobas **owns a body per
  variable** (`sh_var_store` heap-copies whatever the rvalue descriptor points
  at), while the reference decides ownership **per source**. So an alias
  charges twice there and once here, and a stored literal charges nothing there
  and once here. The three rows (`hold-alias`, `hold-lit-prog`, `hold-lit-p25`)
  sit together in the probe's `share` battery for that reason.
