<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# Decision — funding `TIME`/`TIME=n` **and** trap slice T5 `INTERVAL` with ONE carve

Status: **✅ SIGNED OFF 2026-07-26 — D-FUND-1 option (a), the full SAVE-family
write engine.** Measured on `82a5ebc`,
tree clean, `main`. This answers §4 of
[`handover-time-and-t5-interval.md`](handover-time-and-t5-interval.md) — *"the
coupling — this is the actual first task"* — and nothing here is implemented
yet ([[spec-before-implementation]]).

**Recommendation: carve the SAVE/BSAVE/CSAVE *write engine*
([`basic/save.asm`](../basic/save.asm)) into a sub-ROM PAGE-1 tenant beside
`bload_tenant` and `fatprim_tenant`. Measured movable set = 458 B / 445 B net of
one copy; 4 direct dependencies, all four already dissolved once by the BLOAD
carve.**

---

## 1. The deficit, measured

`make basic-reloc` on the current tree:

| wall | free |
|---|---|
| page-1 `$4000–$7FFF` (`__MEAS_PAGE1_END` `$7FEA`) | **22 B** |
| page-0 low region `$2812–$3FFF` (`__MEAS_LOW_END` `$3FFB`) | 5 B |

Both threads are **pure page-1** needs, and this was re-checked rather than
inherited from the brief:

* `TIME` read is a factor function beside `ev_f_erlfn` **`$4D6F`** → page 1.
  `TIME=n` is a statement executor → page 1.
* T5's down-counter goes in `event_poll` **`$5AE6`** → page 1. (T3's KEY handler
  had to be *low-region* because its event source fires from inside C-BIOS's
  keyboard scan; INTERVAL's source is the `H.TIMI` seam itself, where a frame
  skipped by `htimi_guard` is a ≤1-frame deferral, exactly as for PLAY. So T5
  does **not** inherit T3's low-region constraint.)

| need | spec estimate | ×1.8 (the arc's measured optimism) |
|---|---|---|
| `TIME` + `TIME=n` | 52–75 B | 94–135 B |
| T5 `INTERVAL` | ≥48 B | ≥86 B |
| **total** | **100–123 B** | **180–221 B** |

Deficit after the 22 B in hand: **~100 B at the estimates, ~160–200 B at the
arc's historical multiplier** (T2 came in 70 B low; T3 came in 106 B = 1.8× low
*while calling itself deliberately pessimistic*).

**Promotion cannot help.** It moves low-region content *into* page 1 — it
relieves the low wall at page 1's expense, and low is the emptier wall
([[promotion-funds-low-region]]). The only lever is a **carve**.

## 2. How the candidate was chosen — a page-1-tenancy sweep

`tools/carve_scout.py` answers the **page-0**-tenancy question (fatal escape =
a call into the main low region `$2812–$3FFF`). Every remaining candidate here
is eval-bound, and eval bottoms out in exactly that region, so page-0 tenancy is
closed to all of them ([[page0-tenant-eval-eviction-constraint]]).

The question that is still open is the **mirror**: a **page-1** tenant runs with
main page 1 switched *out* and main page 0 — BIOS **and** the low region, i.e.
the whole float pack — switched *in*. Its only fatal escape is a call to a MAIN
routine `>= $4000` that is not itself moving. That is the shape BLOAD was
carved in, and it is the question a **frontier** scout answers: not the
transitive tail (which runs to ~900 labels the moment `exec_stmt` is reached and
tells you nothing), but the **direct dependencies you must dissolve**.

Sweep of every `basic/*.asm` page-1 file, sorted by movable bytes, with the
direct-dependency count:

| file | page-1 B | direct deps | verdict |
|---|---|---|---|
| `expr.asm` | 2077 | 23 | eval core — hot path, reject |
| `files.asm` | 1877 | 36 (incl. `exec_stmt`) | reject |
| `program.asm` | 1948 | 24 (incl. `exec_stmt`) | interpreter core, reject |
| `graphics.asm` | 1393 | 14 (incl. `exec_stmt`) | already twice-evicted |
| `interp.asm` | 1322 | 76 | the dispatcher itself, reject |
| **`save.asm`** | **1068** | **10, none of them `exec_stmt`** | **CANDIDATE** |
| `cload.asm` | 890 | 16 | **backup candidate**, §5 |
| `vars.asm` | 685 | 6, all tiny | variable engine — a CALSLT per variable access, reject |
| `field.asm` | 668 | 13 (incl. `exec_stmt`) | reject |
| `printusing.asm` | 459 | 8 (incl. `exec_stmt`, `pchar`) | reject |
| `strvar.asm` | 275 | 10 | reject |
| `playsvc.asm` | 229 | **0** | H.TIMI service routine — must be resident, reject |

Two of these deserve their rejection spelled out, because a bare byte count
flatters them:

* **`vars.asm` (685 B, six trivial deps)** is the *cleanest* carve on the board
  by the scout's arithmetic and the worst by any other measure: every variable
  read and write in the language goes through it. A CALSLT per `A=A+1` is not a
  trade.
* **`playsvc.asm` (229 B, zero deps)** is self-contained because it is the PLAY
  interrupt service routine. It runs from the `H.TIMI` seam; it cannot be behind
  a CALSLT.

`save.asm` is the only large file whose frontier contains **neither `exec_stmt`
nor a hot path** — it never jumps back into the interpreter loop, because every
one of its verbs already returns cleanly.

## 3. The recommended carve — the SAVE-family write engine

**Split the file the way BLOAD was split: parse stays resident, the I/O engine
moves.** `eval` appears in `save.asm`'s frontier exactly three times
(`b4_expr`, `expect_comma_eval`, `csav_speed`) and all three are argument
parsing, which the resident stub keeps — it marshals an already-evaluated
parameter block, precisely the `fatprim`/`fcbname`/`bload` pattern.

### 3.1 The moved set — measured, 30 labels

BSAVE disk body (`bsv_open`…`bsv_fin`), BSAVE tape body
(`bsv_cas_exec`…`bsv_cas_fin`), SAVE disk body (`sav_data`…`sav_fin`), the tape
tokenised-program writer (`tape_save_basic`, `tsb_*`, `tape_name_emit`,
`tne_loop`, `tape_putword`), the cassette block buffer (`cas_flush_block`,
`cas_fb_lp`, `cas_wbyte`) and the disk write cursor (`disk_write_begin`,
`disk_putword`, `disk_putbyte`, `disk_write_end`).

```
MOVED: 30 page-1 labels = 458 B
DIRECT main-page-1 deps to dissolve: 4
     40 B  fat_io_putbyte    <- disk_putbyte
     35 B  fat_io_create     <- disk_write_begin
     15 B  load_error        <- bsv_cas_data, bsv_cas_exec, bsv_cas_id, ... (+6)
     11 B  fat_io_close      <- disk_write_end
```

`cas_wbyte` (13 B) is a **copy**, not a move — `pch_file` still calls it — so
**445 B actually leaves page 1**.

### 3.2 All four dependencies are already-solved patterns

| dep | dissolution | precedent |
|---|---|---|
| `fat_io_create` / `fat_io_putbyte` / `fat_io_close` | sub-local **copies**. They call `fat_mount`/`fat_find`/`fat_open`/`fat_dir_create`/`fat_flush_data_sector`/`fat_dir_update`, **all already fatprim-tenant selectors** (`DISKOP_SEL_*` 2,3,5,11,12,13) — so in the tenant they are ordinary in-page calls, not `subrom_call` round trips | `sub/bload.asm` did this for the **read** cursor |
| `load_error` (62 external callers) | leaf returns an error **code**; the resident stub raises the disposition | the playbook's leaf-returns-a-code shape, used by BLOAD |

`basic/fat.asm` was independently frontier-scanned: **0 main-page-1 escapes**,
closure 42 — so copying the write cursor sub-side is legal by measurement, not
by taste.

### 3.3 Why this cluster qualifies on the non-byte criteria

* **Cold by construction.** `SAVE` / `BSAVE` / `CSAVE` are user- or
  program-initiated, once per invocation. One CALSLT per *file written*.
* **The tape path is already DI.** `subrom_call` enters DI; the cassette writer
  wants that anyway. Where BLOAD's tape *read* had to re-enable interrupts and
  rely on `htimi_guard`, the write path has the same escape hatch already
  documented in `sub/bload.asm`'s header.
* **No `jp (hl)` hazard.** BLOAD had to keep `load_handoff` resident because
  `,R` jumps into the loaded program and never returns. The save family has no
  such tail — every path returns.
* **Room exists.** `build/sub.rom` page 1 has **4097 B** of trailing `$FF`.

### 3.4 What stays resident (the residue, and why it is honest to name it)

~623 B of `save.asm` stays: all three verbs' argument parsing (`do_bsave` +
`bsv_dev` + `bsv_is_disk`, `do_save` + `sav_dev` + `sav_is_disk`, `do_csave` +
`csav_*`, `bsave_opt4`/`b4_*`, `expect_comma_eval`), the `,A` ASCII-listing
paths (`sav_ascii_flag`, `ascii_save`, `sav_cas_flag`, `cas_ascii_save` — they
drive `list_walk`/`pchar`, i.e. the **page-0** detokeniser tenant, which a
page-1 tenant cannot reach), and the four routines with external callers
(`tape_parse_name`, `cas_write_ea_header`, `cas_ascii_finish`, `cas_wbyte`).

### 3.5 The number to expect

| | B |
|---|---|
| moved | 458 |
| less `cas_wbyte`, copied not moved | −13 |
| plus marshalling stubs, 3 verbs + param staging (est.) | +45 |
| **projected net** | **~400** |
| **× 0.74** — BLOAD projected 356, measured **262** | **~296** |

Against a deficit of **~160–200 B** at the arc's historical multiplier, that is
a margin of ~100 B, and it funds **both** threads from one measure-and-classify
pass rather than paying that cost twice.

⚠️ The projection is not the deliverable. Per the handover's §5.1, the number
that gets reported is the one read off `make basic-reloc` **after** the carve
lands, with the tripwires lifted.

### 3.6 ✅ AS BUILT — measured, and for once the estimate did NOT run optimistic

**`make basic-reloc`: page-1 free 22 B → 332 B. +310 B**
(`__MEAS_PAGE1_END` `$7FEA` → `$7EB4`). Low region unchanged at 5 B — the carve
is entirely page-1, as designed, so the two walls stay uncoupled here. Lean
`basic.rom` **byte-identical**; `save_tenant` is the 22nd page-1 tenant and
`check_tenant_closure.py --page1` reports **no main-page-1 escape**.

Against §3.5's ~296 B projection that is **+14 B better**, and it is the first
estimate in this line of work that did not come in low (T2 −70 B, T3 −106 B,
BLOAD −94 B). The reason is not virtue: the projection was computed by applying
BLOAD's 0.74 optimism factor to a *census that had already been narrowed by an
external-caller grep* — `disk_write_*`, `tape_name_emit`, `cas_wbyte` and
`cas_flush_block` were moved to the "stays resident" column **before** the
estimate, not discovered there afterwards. Correcting a number twice for the
same error is how an estimate ends up pessimistic.

**What actually moved** (five contiguous blocks, extracted verbatim into
`basic/sv-*.inc`): BSAVE's disk engine, BSAVE's tape engine, SAVE's tokenised
disk engine, the shared cassette tokenised writer, and `tape_putword`. Each
repack stub re-declares the **same entry label** the resident parse already
reaches by `jr`/fall-through, so not one parse instruction changed — which is
what kept the lean cart byte-frozen through a five-way split.

**Gated, not just built** ([[gate-during-implementation]]):

| gate | result |
|---|---|
| `make basic-reloc` (5 closure/identity checks) | green |
| `make diskbasic-acceptance-repack` vs the CF-3300 oracle | **34/34**, incl. SAVE/BSAVE, SAVE(ASCII), BSAVE(.bas), BSAVE/BLOAD(VRAM) |
| `basic_probe_tape_save.py` — lean cart (regression control) | 16/16 |
| `basic_probe_tape_save.py --machine …REPACK_DISK` | 15/16 |
| `make unit-test` | 52/52 |

The tape probe needed a `--machine` option to exist at all: it was hard-wired to
the lean cart, and **the lean cart is byte-frozen**, so without it the default
run is a regression control and nothing more — the carve would have been
unverifiable on the only side it changes. That is the same gap that produced a
wrong "unverifiable" verdict during T3 ([[control-that-fails-must-be-fixed]]).

The one failing case — multi-block cassette ASCII `LOAD"CAS:"` — is
**pre-existing and was proved so rather than assumed**: a control built from the
parent commit in a throwaway worktree, installed under the same machine name,
reproduces it with a **byte-identical** buffer. It touches the cassette READ
path, which this carve does not move. Tracked, with its hypothesis explicitly
marked untested, in [`disk/docs/tier2-review-queue.md`](../disk/docs/tier2-review-queue.md).

## 4. Open decision

**D-FUND-1 — carve the SAVE-family write engine as a sub-ROM page-1 tenant?**
**✅ DECIDED 2026-07-26: (a).**

* (a) **Yes, as scoped above** ← **CHOSEN** — one tenant covering BSAVE + SAVE + CSAVE write
  engines. *Recommended.* Largest measured movable set with a 4-item frontier,
  every item of which has a landed precedent.
* (b) Yes, but **BSAVE only** first (528 B closure, 8 deps incl. the parse
  side) — a smaller step that probably still clears the deficit, at the cost of
  splitting `disk_write_*` awkwardly between the two builds.
* (c) A different candidate (§5).
* (d) Don't carve; shrink the need instead — accept a reduced `TIME` (§3 of
  [`spec-basic-time.md`](spec-basic-time.md) costs an integer variant at −11 B,
  already rejected on correctness) or defer T5. **Not recommended**: the two
  threads were coupled precisely so that one carve serves both.

## 5. The backup candidate, if D-FUND-1 goes another way

`basic/cload.asm`'s **tokenised** tape-program reader — `do_tape_prog` and its
tail, **320 B**, six direct deps (`new_prog` 22, `relink` 16, `load_error` 15,
`print_string` 9, `cal_refill` 8, `ascii_read_lines` 6). It is SAVE's mirror
and shares the cassette block buffer with it. The ASCII branch
(`cas_ascii_load` → `ascii_read_lines` → `dispatch_line` → `tokenise`) is the
part that is not evictable, and it is a *branch*, not the trunk — the T3-era
verdict "`cload.asm` is NOT EVICTABLE" was correct **for the file as a whole and
for page-0 tenancy**, which is the question that was asked then.

## 6. Method notes worth keeping

* The frontier scout used here is `tools/p1scout.py` (written for this decision
  as a scratchpad p1scout.py, promoted to `tools/` at 6f8ac0f — the old path is
  deliberately not spelled out: a citation names a path, and that one no longer
  resolves); if D-FUND-1 is
  adopted it should be promoted to `tools/` beside `carve_scout.py` and
  `promote_scout.py`, because **`carve_scout.py` cannot answer the page-1
  question at all** and every remaining candidate is a page-1 candidate.
* **Reporting the transitive escape set is useless; report the frontier.** Every
  file whose code ever reaches `exec_stmt` shows ~900 "escapes", which says only
  that the interpreter is connected. The 4-vs-882 difference for `save.asm` is
  the same measurement asked the right way — the same trap, in a new shape, as
  the T3 carve's 470/149/381 ([[traps-t3-key-slice]]).
* The unit was still chosen by **external-caller census first** (§3.1/§3.4), not
  by file size: `save.asm`'s 1068 B is not the answer, 445 B is.
