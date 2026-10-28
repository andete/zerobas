# Sub-ROM space: the DEMAND side (read-only analysis, 2026-10-11)

Scope: what needs ROM space in zerobas today, which wall actually binds, what
moving code to (more) sub-ROM would cost and buy. Every number below is tagged
**[M]** measured (with its source and date) or **[I]** my inference / estimate.
Nothing was built or run except `python3 tools/tier_table.py --all` and a
read-only sizing script over the existing `build/*.sym` files.

---

## 0. The one-paragraph answer

**[M]** The binding wall is **main** (low region + page 1 together): **39 B**
free on the clean 2026-10-11 build (19 B low, 20 B page 1,
`scratchpad/casrbrk_walls.out:788-789`). The sub-ROM is *also* full: **137 B**
page 0, **94 B** page 1 (`:792-793`). The disk ROM has **3868 B** in holes,
largest **843 B** (`:796-804`). **[M]** Main went from **877 B** free on
2026-10-05 (space plan, `docs/plan-main-rom-space-2026-10.md`, "Progress" table)
to 39 B on 10-11 — ~840 B consumed in six days by TIER 1–4 work (105 commits
since 10-05, `git log`). **[I]** So demand is not a one-off backlog; it is a
*rate* of roughly 100–150 B/day of main while the tier queue is being worked.

**[M]** The measured record says a bigger sub-ROM does **not** convert into main
bytes by itself: page-0 eviction of verbs is structurally closed (anything that
prints or raises reaches the BIOS, which a page-0 tenant switches out) and
page-1 eviction "only reaches HOT leaves" (every cold verb's closure pulls
`eval`, which is main page 1) — memory `carve-routes-measured-shut`, 08-24 and
09-24 entries; `scratchpad/evict_scout.out` (09-24). The only *priced*
sub-to-main conversions on the books are **~183 B** of main for **~134 B** net
of sub page 1 (space plan Phase C: C5-LOW 80, SBH-1 77, C6 26). Beyond that,
turning sub space into main space needs a new eviction *shape* (a per-verb
eval-bounce co-routine, or a sub-side copy of the evaluator), which is design
work the sibling report must price. **[I]** The honest demand-side verdict:
more sub space is **necessary** (the sub walls block ~5 open items and all of
Phase C) but **not sufficient** to relieve main; the visibility rules of the
slot architecture, not the sub-ROM's size, are what cap eviction today.

---

## A. The walls today, and what each region is

### A.1 Readings **[M]** — clean build 2026-10-11, `scratchpad/casrbrk_walls.out`

| region | free | where | source line |
|---|---|---|---|
| main **low region** | **19 B** | `$2765-$3FFF`, `__MEAS_LOW_END @ $3FED` | `:788` |
| main **page 1** | **20 B** | `$4000-$7FFF`, `__MEAS_PAGE1_END @ $7FEC` | `:789` |
| sub **page 0** | **137 B** | `$0000-$3FFF`, "callable-from-main island" | `:792` |
| sub **page 1** | **94 B** | `$4000-$7FFF`, "BIOS-visible island" | `:793` |
| **disk.rom** | **3868 B** in 32 holes; largest usable **843 B** at `$48DE` | `$4000-$7FFF`, pinned entries | `:796-804` |

The same readout confirms the image shapes: relocated main image 22683 B, low
region holds 6280 B (`:787`); kwtable single copy lives in the sub only
(1189 B, `:798`); 19 page-0 tenants / 943 routines, 29 page-1 tenants / 770
routines (`:803-804`).

There is no "tape wall" printed by `make basic-reloc`; the tape bodies are laid
into a C-BIOS gap (`$09EE..tape_end`, `tools/build_mainrom.py:16-27,75`) and
`build_mainrom.py` *refuses* overlap rather than reporting free bytes. **[I]**
Treat tape as a fixed-size pocket with no slack figure, not as a wall with a
reading.

### A.2 What lives where, in plain terms

Sources: `docs/concepts/rom-layout.md` (whole), `docs/subrom-tenant-playbook.md`
§1–§3, `docs/spec-basic-subrom.md` WAVE-1 amendments, `basic/main.asm:54-526`
(include order), `basic/subromcall.asm` header comments.

* **Main ROM, slot 0, `$2765-$7FFF`** is ONE contiguous assembly
  (`basic/main.asm`). The `"AB"` header is pinned at `$4000`, so the image is
  split into:
  * the **low region** `$2765-$3FFF` — C-BIOS space reclaimed by the repack.
    Holds what *must* be visible while main page 1 is switched out: the string
    engine, `input.asm`, the float pack (`float.asm`, `float-arith.asm`), the
    tenant dispatcher (`subromcall.asm`), the screen-editor and KEY-trap hooks,
    the arrays glue, `poke/sound/title`, and the low string pool
    (`basic/main.asm:74-141, 403`). Pinned here because **page-1 sub tenants,
    the disk ROM and the `$0038` ISR path call these with page 1 being someone
    else's ROM** (`tools/promote_scout.py` docstring; `subromcall.asm` "SITED
    LOW" comment).
  * **main page 1** `$4000-$7FFF` — the interpreter proper: `interp.asm`,
    `expr.asm` (eval), `vars.asm`, `print.asm`, `program.asm`, `files.asm`,
    `graphics.asm` glue, FOR/NEXT/IF, traps, the statement dispatch
    (`basic/main.asm:248-385`). This is the **hot path**: every statement is
    dispatched and every expression evaluated here. **[M]** The 2026-07-30
    structure review found *zero* contract forcing anything into page 1 — it is
    all "pressure-placed" (memory `rom-region-structure-review`).
  * **Both regions share one budget.** Which region a routine lands in is
    decided only by where its `include` sits relative to `__MEAS_LOW_END`;
    promotion moves the split 1:1 and cannot raise the sum (memory
    `carve-routes-measured-shut` 09-08; `TODO.md:11178 (T-CA3CA6)-20455`). Price every
    main item against low + page 1 **combined**.
  * **Islands**: four runs of C-BIOS padding below `$2765` that hold small
    leaves and read-only tables (`basic/islands.asm`; space plan A2/A3). They
    are ~full after Phase A (plan §2: islands 1/2 ~183 B, gap-1 77 B, all spent).

* **Sub-ROM, slot 3-2, 32 KB, `"CD"` signature** — reached only by `CALSLT`
  from a main stub (`subrom_call`, `basic/subromcall.asm:60-74`). A call maps
  *one* page, so the two pages see different worlds (playbook §2):
  * **page-0 tenant** (`$0010` table, 19 rows, `sub/sub.asm:132-231`): runs
    with the **BIOS and main's low region switched OUT**, main page 1 and RAM
    visible. So it may call `eval`-side page-1 helpers but can neither print
    (`pchar → CHPUT`), raise (`raise_error → BREAKX`), nor touch the float
    pack or string engine. Interrupts are off unless it opts into the RAM
    trampoline. Tenants: the tokeniser, LIST detokeniser, **array engine**,
    **string heap**, PRINT USING pieces, SCREEN-2 graphics engine, DEFINT…,
    READ/DATA value, BEEP, FIELD lookup, LSET/RSET store, DEF FN, LOF, KEY$.
  * **page-1 tenant** (`$4010` table, 29 rows, `sub/sub.asm:456-693`): runs
    with **main page 1 switched OUT**; sees BIOS, low region, RAM. So it can
    print and do float maths but cannot call `eval`, `skip_spaces`, the var
    store or anything else in main page 1. Tenants: the maths pack
    (SQR/ATN/EXP/LOG/`^`/SIN/COS/TAN/RND), CALL FORMAT, RESUME's scan, the FAT
    primitives, directory verbs, PLAY's parser, the line editor, cassette
    matching, TITLE, FCB names, CIRCLE's parser, BLOAD, SAVE, the error
    messages, ASCII line parse, PRINT USING numbers, the line reader, cursor,
    cassette GET, sequential I/O.
  * **Consequence that is the whole story:** a tenant always hides one of the
    two things a BASIC verb needs — the BIOS/low region (page 0) or the
    evaluator (page 1). Memory `page0-tenant-eval-eviction-constraint` states
    the rule and its corollary: *"the only cheap candidates are COLD routines
    whose closure is eval-free."*
  * **The duplication tax [M]:** because a page-1 tenant cannot see main page
    1, bodies it needs are assembled *twice*. Today five `basic/*-body.inc`
    files appear in both images: `fatio-body` 111, `tokskip-body` 89,
    `pdfcb-body` 47, `cascap-body` 46, `sv-tne` 34 = **327 B** (my sizing
    script over `build/basic-reloc.sym` + `build/sub.sym`, read-only; the
    07-30 review priced the class at 457 B "contract-forced").

* **disk.rom, slot 3-1, 16 KB** — Disk BASIC behind hooks plus the MSX-DOS
  kernel, with **pinned** entry addresses, so its free space is holes between
  pins (`tools/check_disk_walls.py`; `docs/concepts/rom-layout.md` "disk ROM").
  Items that live here must fit a hole, and the hot `$607B..$75A5` region "has
  no room" (`docs/TODO-done.md:26000 (T-12AD22), 30048`).

### A.3 Approximate size map **[I, computed]** — what is actually in each region

Computed by a read-only script over `build/basic-reloc.sym` / `build/sub.sym`
(label-span attribution per source file; a file's last routine runs to the next
file's first label, so figures are ±a few %). Totals reconcile with the readout
(low 6299 ≈ 6280 + pad; page 1 16368 = 16384 − 20 + header words).

Main page 1 (16368 B): `program.asm` 2417 · `expr.asm` 2023 · `files.asm` 1654 ·
`interp.asm` 1234 · `graphics.asm` 1211 · `vars.asm` 705 · `print.asm` 705 ·
`cload.asm` 634 · `field.asm` 622 · `save.asm` 546 · `strvar.asm` 440 ·
`traps.asm` 426 · `printusing.asm` 407 · `screen.asm` 382 · `missing.asm` 375 ·
`edctrl.asm` 294 · `bload.asm` 244 · `playsvc.asm` 229 · `deffn.asm` 218 ·
`usr.asm` 216 · `list.asm` 201 · `repl.asm` 181 · `clear.asm` 164 · `play.asm`
145 · smaller glue.

Main low (6299 B): `float-arith.asm` 2405 · `str-engine.asm` 1931 · `arrays.asm`
686 · `input.asm` 443 · `float.asm` 365 · `subromcall.asm` 144 · `sound` 94 ·
`edscreen` 85 · `keytrap` 54 · misc.

Sub page 0 (16320 B): `graphics.asm` 4907 · `strheap.asm` 3213 · `arrays.asm`
1400 · `kwtable.inc` 1189 · `tkfloat.asm` 994 · `tokenise.inc` 779 ·
`detok.inc` 731 · `pu-render.inc` 702 · `deffn.asm` 659 · `keystr` 385 ·
`printusing` 246 · `readdata-body` 219 · smaller.

Sub page 1 (16368 B): `fat-prim-body.inc` 1840 · `math-coeffs.inc` 1607 ·
`playparse.asm` 1509 · `lineedit.asm` 1182 · `fp_sqrt` 804 · `randio-body` 765
· `errmsg` 672 · `circleparse` 654 · `punum` 616 · `readline` 565 · `fp_exp`
503 · `fatprim.asm` 477 · `fp_rnd` 430 · `fp_sin` 426 · `fp_log` 368 ·
`fp_atan` 359 · `bload.asm` 375 · `casmatch-body` 306 · `bload-body` 292 ·
`format-body` 276 · `fp_pow` 195 · `fcbname-body` 188 · smaller.

**[I]** Reading this against the eviction rules: what remains in main page 1 is
(a) the evaluator/dispatch/variable core (~6 KB: interp, expr, vars, strvar,
print, program's line store/edit) — hot and un-evictable by rule; (b) disk/file
glue that calls `eval` and raises (files, field, program's LOAD/SAVE parts);
(c) the cold peripheral verbs that *print or raise* (cload 634, field 622, save
546, printusing 407, bload 244, list 201, playsvc 229 ≈ 2.9 KB) — exactly the
five candidates Route B refused on 2026-08-24.

---

## B. Demand inventory

### B.1 The 13 BUDGET-tagged items **[M]** (`python3 tools/tier_table.py --all`, today; blocks read at the line numbers shown)

| TODO line | item | tier served | wall that blocks it | bytes stated |
|---|---|---|---|---|
| 4340 | carve inventory re-run (D-LONGRUN) — funding for `PLAY X<var>;` | TIER 1 | **main** (combined) | ~30 B short |
| 6712 | D-NGRAM exact repeats — three candidates left | funding | main | small, unpriced |
| 11443 | D-PEEPHOLE flag-changing class | funding | main | ceiling "really 1 B" |
| 11526 | IXH/IXL half-index idiom | ROM/speed | main 2 B; the live axis is **speed in sub** | 2 B |
| 11997 | `ems_typecheck` pops (D-POPRAISE Q1) | funding | main (low/page 1) | 21 B, 🙋 |
| 12341 | 4 B dup-span prefix (tooling) | funding | main | 4 B, "not worth taking" |
| 16289 | `clone_scout` label-block pricing | apparatus/funding | main | 0 today ("finds nothing") |
| 19011 | bare-`jp raise_error` family | funding | main | ~2 B, ruled carve-freely |
| 20837 | `ex_mid_stmt` shadowed abort | funding | **low region** | 3 B, 🙋 |
| 30954 | D-MKIREUSE `hk_mki` twin | TIER 6 rule | **main page 1** (~4 B) vs **disk.rom** (~95 B reclaimable) | 4 B main / 95 B disk; 🙋 which rule yields |
| 32561 | slim the file-channel context | TIER 4 (RAM) | **RAM** 1024 B to free; "ROM cost NOT measured" (`:363`) | ROM unpriced |
| 34546 | NO-ORACLE RAM bucket | apparatus | **RAM census**, no ROM | — |
| 34758 | `err_verify`/`brk_msg` last main-resident messages | funding | main page 1; blocked by a missing oracle reading, not by bytes | 8 + 6 B |

**[I]** Of the 13, **nine are funding mechanisms** (carve routes, worth 0–30 B
each and mostly exhausted), **two are RAM** (no ROM wall), one is a rule
conflict (D-MKIREUSE), one is oracle-blocked. The BUDGET bucket therefore does
*not* describe the demand; it describes the supply tools. The demand is in the
tier items that say "carve first".

### B.2 Open items that are waiting on bytes but are not tagged BUDGET **[M]** (grep of TODO.md for "carve first" / "does not fit" / "no room", 2026-10-11; owning item and line)

| TODO line | owning item | tier | wall | bytes stated |
|---|---|---|---|---|
| 26710 | D-FORFAST exactness test (NEXT 2.37× the VG-8020) | TIER 5 | main page 1 | ~20 B |
| 29069 | D-INPQUOTE2 (what follows a closing quote) | TIER 3/6 | main | ~59 B "does not fit in main" |
| 18692 | D-FCBSHAPE: `chan_gate` at LSET/RSET/MERGE | TIER 4 | main page 1 | 16–24 B |
| 17706, 18107 | D-FCBSHAPE S1–S3 (fixed disk table, ruled by Joost 09-27) | TIER 4 | **sub page 1** ("0 B free … carve first") | ~20 B+ sub p1 |
| 3420 | PAINT span stack re-architect (grow below SP; ruled 09-27) | TIER 4 | **sub page 0** (graphics tenant) | unpriced, "sub-ROM carve first" |
| 20869 | SCREEN 3 | TIER 1 (keyword) | **sub page 0** 170–280 B + 6 B main | 176–286 B |
| 25331 | `WAIT` keyword (token `$96`) | keyword | main page 1 20–25 B + body in sub p1 | ~25 B main |
| 23019 | D-LITREF next slice (READ literal points at program text) | TIER 4/6 | main (combined) | "70 B combined … carve first" |
| 16989 | DEF FN formals aliasing — the pool route (ruled YES 09-27) | TIER 6 | main | unpriced |
| 11589 | `String too long` precedence — ownership refactor (ruled YES) | TIER 6 | main (string engine, low) | unpriced |
| 9016 | CONT inside a program raises with line (ruled YES) | TIER 6 | main | unpriced, small |
| 26215 | T6 row type / enumeration | TIER 1 (rung def.) | main, per keyword | "a carve comes first" |
| 31123, 30932 | D-STRINGEMPTY, D-MKIRANGE-class T6 fixes | TIER 6 | main | each a few B; **ruled "TIER 6 spends no main bytes"** (`:30962`) |
| 34335 | `INPUT$` on a cassette source (`str_inputd_read` calls `fat_io_getbyte` directly) | TIER 3 | main page 1 | unpriced, "does not fit" |
| 34587 | `ld (VALTYP),a` in the cold hook | TIER 6 | main page 1 | 3 B |
| 33725 | tape half of the eviction rule (`cload.asm` 864 B then) | structure | **sub** (both pages) | ~860 B of sub |
| 30730 | D-BOOTKEYS plain boot "76 B short" | TIER 4 | RAM (free-RAM parity), not ROM | 76 B RAM |

Ambiguous walls **[I]**: D-MKIREUSE (main vs disk.rom, a rule question);
D-FCBSHAPE (sub p1 for the tenant, main for the gates); `WAIT` (main stub +
sub body); the file-channel slimming (RAM to free, ROM cost unknown).

### B.3 Demand summarised **[I]**

* **Main-bound, priced**: PLAY X ~30 · FORFAST ~20 · INPQUOTE2 ~59 · FCBSHAPE
  gates ~20 · WAIT ~25 · LITREF ~70 · VALTYP 3 · err_verify/brk 14 · MKIREUSE 4
  ≈ **245 B** of main for the *priced* queue, against **39 B** free.
* **Main-bound, unpriced** (ruled YES by Joost, each a slice): DEF FN alias
  pool, String-too-long ownership, CONT line, T6 enumeration per keyword,
  INPUT$ cassette source. Historical slice costs in this tree run 20–100 B of
  main each (e.g. D-ASCIINUM, D-LITREF 70 B, D-INPQUOTE ~30–40 B, `TODO.md:14400 (T-59C37A)`).
* **Sub-bound**: SCREEN 3 (170–280 B p0), PAINT span-stack re-architect (p0),
  FCBSHAPE S1–S3 (p1), Phase C's C5-LOW/SBH-1 which *need* 181 B of sub p1 to
  *give* 157 B of main. The sub walls (137/94 B) block all of these today.
* **disk.rom-bound**: nothing open is blocked by disk.rom space (3868 B free);
  the `$607B..$75A5` kernel region is the only tight pocket.
* **RAM-bound**: TIER 4 items (DIM reserve done to 116 B; channel context 1024
  B; BOOTKEYS 76 B) — not ROM at all, but each ROM fix for them costs main.
* **Rate [M]**: 877 → 39 B in six days (space plan progress table → today's
  readout). **[I]** At that rate any one-off carve of a few hundred bytes buys
  days, not months.

---

## C. What could move out of main, if the sub side had room

### C.1 What the record already says **[M]**

* **Route B, page-0 eviction of verbs: closed.** 2026-08-24 carve scout: five
  candidates (cload, field, save, printusing, list, playsvc; 177–762 B each)
  "all five refused" because a verb that prints or raises reaches `CHPUT` /
  `BREAKX` through resident page-1 code, and the slot config persists through
  that call (memory `carve-routes-measured-shut`, Route B; `tools/carve_scout.py`
  docstring: *"the walk must continue through [page 1]"*).
* **Route C, page-1 eviction: only hot leaves.** 2026-09-24
  `scratchpad/evict_scout.out` ranks the top page-1 closures by net bytes:
  `htimi_service` 360 (the ISR), `ev_f_notword` 312 and `ev_f_var` 217 (the
  evaluator), `play_service` 210 (ISR), `tgt_parse` 137 / `var_name_key` 110
  (variable lookup), `for_name` 110, `if_skip_to_else` 104 … The first cold
  rows are the tape byte readers `cas_in_getbyte` 102 / `cal_getbyte` 90, and a
  tape-block move was refuted on timing (SBH-10, space plan §1).
* **Dup-span, clone, `jp→jr`, promotion**: all measured shut or renewable at
  single bytes (`carve-routes-measured-shut` 09-08; `TODO.md:1021 (T-5E5DB1)-4360`).
  Promotion cannot raise the combined budget.
* **De-eviction is refuted** (smallest tenant body 74 B vs largest stub ~42 B;
  memory `rom-region-structure-review`) — so there is no "bring code back"
  lever either.
* **`input.asm` (458 B) DECLINED** for eviction (pindata slice, same memory).
* **Priced sub-to-main conversions still unbuilt (space plan Phase C):**
  C5-LOW **+80 main / −102 sub p1**; SBH-1 **+77 / −79**; C6 (eviction step 13
  sample) **+26 main / +47 sub p1**. Net: **+183 B main for −134 B sub p1**,
  gated on "eviction step 13" of `disk/docs/spec-diskcode-eviction.md`, whose
  §6.6ba says *"what is left of step 13 is nothing"* except `DSKO$`/`DSKI$`.
* **The hunt's 50 unbuilt candidates** (space plan §5) are unpriced
  lower-ranked estimates; the plan says to re-run the hunt after Phase B.

### C.2 What is cold in main today **[I, from the size map and the include headers]**

| body | B (approx.) | cold? | why it cannot be a tenant *today* |
|---|---|---|---|
| `cload.asm` | 634 | yes (tape load) | prints, raises; tape timing (page-1 tenant must not wait: memory `page1-tenant-must-not-wait`) |
| `field.asm` | 622 | per FIELD/GET/PUT | calls `eval`, raises |
| `save.asm` | 546 | yes | prints, raises; part already a sub tenant (`sub/save.asm` + `sv-*.inc`) |
| `printusing.asm` | 407 | per PRINT USING | glue around three sub tenants already; eval-bound |
| `missing.asm` | 375 | yes | raises (by definition) |
| `bload.asm` | 244 | yes | glue around the BLOAD tenant |
| `playsvc.asm` | 229 | **no** — ISR, every frame | data-referenced from `htimi_guard` |
| `list.asm` | 201 | yes | prints; detok already a tenant |
| `usr.asm` | 216 | cold | small |
| `edctrl.asm` | 294 | prompt only | calls the editor (page 1) |
| `format.asm` | 78 | yes | already mostly in disk.rom (B-7) |

**[I] Estimate.** The cold verb bodies sum to ~2.9 KB, but each is glue around
`eval` plus printing/raising. Under the *existing* tenant shapes (playbook
§3 A/B/C) the record says the cheap part is gone: every candidate that was
scouted either refused outright or yielded only its pure-RAM leaf, which is
already a tenant (BLOAD, SAVE, PRINT USING, LIST, FAT all have one). Realistic
main bytes freeable **without a new eviction shape**: the priced **~183 B**
(Phase C) plus perhaps **50–150 B** of further small leaves — call it
**≤ 300 B**, i.e. a few days of demand at the measured rate.

**[I]** With a *new* shape — the eval-bounce co-routine (`GFX_DREQ` style,
proven by `sub/circleparse.asm`, "a protocol per verb plus a resident stub",
Route C in the 08-24 memory) — each cold verb could leave a 30–60 B resident
stub + its eval calls and move the rest. Ceiling across cload/field/save/
printusing/list/missing/bload: perhaps **1.2–1.8 KB** of main. Cost: a
per-verb protocol design, every error path turned into a result code, DI
during the tenant (or the trampoline), and the page-1-tenant-must-not-wait
rule for anything that reads keys or tape. That is weeks of slices, each with
its own gate, and it is the sibling's design question whether a larger/banked
sub makes it *cheaper* (e.g. by affording a sub-side copy of `skip_spaces`/
`eval`'s front end so the bounce is rarer).

**[I]** A note the sibling should weigh: the thing that would make
whole-verb eviction *cheap* is a tenant that sees **both** main page 1 and the
low region/BIOS. No slot-3 ROM can — any page it occupies hides main's. Only a
page-2 ROM island would (ruling R4's first option), and the plan already
records its cost: program text sits at `$8000`, so a page-2 island hides the
program during the call (`docs/plan-main-rom-space-2026-10.md` §4 R4).

---

## D. The cost of a tenant call, and the hot tenants

### D.1 Measured **[M]**

* **~130 cycles per tenant call** — `basic/subromcall.asm` D-STUBINL header
  ("⏱ ~130 cycles per tenant call"; path: `ld a,(SUBSLOT_OK)` / `or` / `scf` /
  `ret z` / `push de` / build IY / `pop de` / `di` / `call CALSLT` / `ei` /
  `or a` / `ret`, `:60-74`). The inline-index stubs (`sc_inl*`, B-11) add a few
  bytes of stack juggling on top; the three per-element/per-string hot paths
  keep the open-coded `ld ix` "for that reason" (`ary_engine_call`
  `basic/arrays.asm:563-565`, `call_strheap` `basic/str-engine.asm:71-73`,
  `str_set_key` `basic/vars.asm:1070`).
* **[I]** 130 cycles at 3.58 MHz ≈ **36 µs**. For scale, the measured GOTO
  loop iteration costs ~18 ms on zerobas (1797 jiffies / 2000 iterations at
  50 Hz, `docs/spec-basic-interpspeed.md` §2 table) — one slot crossing is
  ~0.2 % of it.
* **The CALSLT hypothesis was tested and REFUTED** (`docs/spec-basic-interpspeed.md`
  §5, 2026-09-02): *every scalar variable store crosses a slot once*
  (`var_alloc_or_find → ary_engine_call → subrom_call`, unconditionally), yet
  the marginal cost of that store is **2.87×** the CF-3300 — at or *below* the
  2.5–3.1× baseline — and the FOR/NEXT loop that crosses *no* slot per
  iteration is the *more* slowed one (3.06×). Conclusion filed there: *"the
  eviction is not what makes this tree slow"*; the 2.5–3.8× lives in resident
  interpreter code (dispatch + expression evaluation, D-INTERPSPEED
  `TODO.md:7695 (T-C1D0BC)-13560`).
* **kwtime rows for tenant-backed functions** (`scratchpad/openwild_kwtime.out`,
  file dated Oct 7, columns `ref ms / zb ms / zb/ref / alone`): `sqr` 39.8 →
  327.6 = **8.23×**, `cos` 5.23×, `exp` 3.67×, `atn` 3.58×, `log` 3.57×;
  resident functions `abs` 0.93×, `len` 0.90×, `peek` 0.97×, `sgn` 0.95×,
  `int` 1.25×. **[I]** The maths tenants are 3.5–8× slower, but at 36 µs the
  call itself cannot explain tens of ms; that gap is the BCD algorithms in
  `sub/fp_*.asm` on top of the baseline. (The `--negative` block in the same
  file deliberately slows rows to prove the gate catches it — ignore its
  "146×" lines.)
* **D-FORFAST**: `nextkw` 2.37× the VG-8020 after D-FORFLOAT, dominated by BCD
  add/compare, no tenant call on the path (`docs/TODO-done.md:23537 (T-F3005D)-26690`).

### D.2 Which tenants sit on a hot path **[M, from `sub/sub.asm` and the call sites]**

| tenant | page | called… | hotness |
|---|---|---|---|
| `ary_engine` (idx 4) | 0 | every scalar store (`var_alloc_or_find`), every array element | **per assignment / per element** |
| `strheap_engine` (idx 5) | 0 | 13 glue sites via `call_strheap`, `str_set_key` | **per string operation** |
| `readdata_tenant` (10) | 0 | per READ item | per statement (READ) |
| `deffn_tenant` (14) | 0 | per FN call, 4 dispatch sites | per FN evaluation |
| `tokenise_ei` (1), `dtk_tenant` (2) | 0 | per typed/ASCII-loaded line; per LISTed line | editor/LOAD, not RUN |
| `graphics_tenant` (8) | 0 | per graphics statement, long-running (EI via trampoline) | per statement |
| `fp_sqrt`…`fp_rnd`, `fp_pow` (p1 1–9) | 1 | per transcendental / `^` | per operator (rare) |
| `cursor`/`readline`/`lineedit` (26/25/15) | 1 | once per key at the prompt (main waits) | editor |
| `scan_stmt_end`, `errmsg_tenant` | 1 | RESUME NEXT; error print | error paths |
| `fatprim`/`dirverb`/`seqio`/`casget`/`bload`/`save` | 1 | disk/tape verbs | cold, I/O |
| `htimi_guard` (resident, low) | — | every frame: skips PLAY/traps while a page-1 tenant owns page 1 | ISR |

**[I] Implication for a bank-switched option.** The per-call cost that matters
is on `ary_engine` and `strheap_engine`: both are page-0 tenants, both are hit
on every store / string op. An ASCII8-style bank select is one memory write
(~13 cycles) plus a byte of bookkeeping — ~10 % on top of the 130-cycle call,
~0.02 % of a statement. **Speed is not the argument against banking**; the
argument is correctness surface: the interrupt trampoline, `htimi_guard`'s
"who owns page 1" test (`subromcall.asm` reads only the primary-slot field),
nested DSKIO CALSLTs from the FAT tenant (D-BLDI/D-HOOKDI/D-LOADDI on 10-10
were all slot/DI bugs in exactly that seam), and every closure gate
(`check_tenant_closure.py`) would need a bank dimension. The two hot tenants
and the ISR-reachable stubs should sit in whatever is *fixed*.

**[I] On "never evict a runtime-hot path"** (Joost, 2026-07-11, spec WAVE-1
block; the memory's `flt_to_int16` "CALSLT-per-factor would wreck the
interpreter"): the measured data since then says a *single* crossing per
statement is lost in the noise, but a crossing per *factor* or per *byte*
would not be (D-LOADRUN: `dpl_*` per-byte path already ~2× its own,
`TODO.md:1021 (T-5E5DB1)-4337`). The rule stands as a rule about *density* of crossings.

---

## E. MSX2 demand — an order-of-magnitude **[I, estimate from public knowledge; nothing in the tree sizes it]**

What the tree says **[M]**: MSX2 is "out of charter, far future" — *"Later
generations — a clone axis (has oracles) … the V9938/V9958 SCREEN 4–12 modes +
blitter, MSX-DOS 2, R800 timing, and the extra BASIC verbs"* (`docs/TODO-done.md:29190 (T-5C8467)-35010`).
No sizing exists anywhere in `docs/` or `TODO.md` (grep for MSX2 port /
extension finds only Technical-Handbook citations).

Public facts the estimate rests on: MSX2 (BASIC 2.0) added SCREEN 4–8, `SET
PAGE`, `SET ADJUST`, `COLOR=` (palette), `COLOR SPRITE`/`SPRITE$` extensions,
`COPY` (VRAM↔VRAM/array/disk), `SET BEEP/TITLE/PROMPT/PASSWORD/SCREEN/VIDEO`,
`GET/SET DATE/TIME` with the RTC, `VDP(9..)`, `PUT KANJI` (JP), extended
`PAINT`/`LINE`/`PSET` with logical operators, `CALL` conventions unchanged. The
MSX2 system put these behind a **16 KB SUB-ROM** (page 0, `"CD"`, slot found
via `EXBRSA`), shared between BIOS extensions (V9938 drivers, palette, RTC) and
the BASIC verbs that call them; the main BIOS/BASIC stayed 32 KB.

Estimate for zerobas, by family:

| family | est. bytes | reasoning |
|---|---|---|
| SCREEN 5–8 drivers via the V9938 command unit (LINE/CIRCLE/PAINT/PSET/POINT re-targeted, page/palette state) | 2–3 KB | the MSX1 graphics tenant is 4.9 KB bit-mapped; the V9938 does the rectangle/line/fill work in hardware, so the driver is thinner but there are four modes |
| `COPY` family (VRAM↔VRAM, array, disk file, with logical ops) | 1.5–2.5 KB | four source×dest shapes plus a header format on disk |
| `COLOR=`, `COLOR SPRITE`, palette, `SET PAGE/ADJUST/SCROLL`-class | 0.8–1.2 KB | register-level, small per verb |
| `SET BEEP/TITLE/PROMPT/PASSWORD/SCREEN/VIDEO` + `GET/SET DATE/TIME` + RTC driver | 0.8–1.2 KB | RTC block read/write + battery-backed settings |
| extended sprites (mode 2), `VDP()` 9+, `PUT SPRITE` colour per line | 0.4–0.6 KB | |
| tokeniser/keyword table/dispatch entries, docs/strings | 0.3–0.5 KB | ~25 new reserved words |
| **total** | **≈ 6–9 KB, upper bound ~12 KB** | |

Two structural consequences the proposal should carry **[I]**:

1. **Visibility again.** Nearly every MSX2 verb parses arguments with `eval`
   (main page 1) *and* drives hardware through BIOS/sub-ROM entry points (page
   0). Under today's rules that is the shape that cannot be a whole tenant;
   the MSX1 graphics split (resident glue evaluates, tenant does pure
   geometry) would have to be repeated verb by verb, with a resident stub each
   (20–40 B of **main** per verb, ~0.5–1 KB of main for the set). So an MSX2
   port needs main bytes too, not only sub bytes.
2. **The `"CD"` slot is spoken for.** zerobas's tenant ROM is a `"CD"` ROM in
   slot 3-2 and writes its slot to `EXBRSA` (`docs/concepts/rom-layout.md`, "The
   sub-ROM and its tenants"). On an MSX2 machine `EXBRSA` must point at the
   *real* MSX2 SUB-ROM (C-BIOS's, with the published `$0000`-table entries)
   or MSX2 software and the BIOS itself break. So a port either moves zerobas's
   tenant ROM out of 3-2 (3-3 is the obvious home, which is option 1's slot)
   or makes zerobas's sub ROM *be* the MSX2 SUB-ROM with the published entry
   table in its page 0. Either way the second-sub-ROM question and the MSX2
   question are the same slot-map question.

---

## F. What the three options buy, demand-side **[I]**

| | sub walls (137/94 B) | main wall (39 B) | speed | MSX2 |
|---|---|---|---|---|
| **1. second 32 KB sub ROM in 3-3** | fully relieved; SCREEN 3, FCBSHAPE S1–S3, PAINT re-architect, Phase C unblocked (+183 B main) | only via *new* eviction shapes (co-routine, or a sub-side evaluator copy); ≤300 B cheaply, 1.2–1.8 KB with per-verb redesign | no per-call change (same CALSLT) | a 32 KB home for 6–12 KB of MSX2 verbs; but 3-3 is also the obvious new home for the tenant ROM if 3-2 must become the real SUB-ROM — one slot cannot be both |
| **2. banked ROM (8 KB banks)** | as 1, with more total room | as 1 | +~13 cycles/call; the hot page-0 tenants and ISR-reachable stubs must be in the fixed window | as 1, with the same slot-map caveat |
| **3. do nothing** | Phase C and the sub-bound TIER 1/4 items stay blocked; sub p1 carves (C5-LOW, SBH-1) cannot land | each main slice keeps paying a carve first; the measured rate says a few days per carve | — | not possible |

The demand-side bottom line: **the sub walls are a real, cheap-to-fix blocker
for a handful of ruled items and for the only priced main relief (Phase C);
the main wall is the structural one, and no amount of sub-ROM relieves it
without a new way for a tenant to reach `eval`.** The architecture question the
sibling should answer is therefore not "how many KB" but "which pages must a
tenant be able to see" — and the honest answer from the record is that every
slot-3 layout hides one of main's two pages.

---

## G. Measured vs inferred, in one place

**Measured [M]** (file:line, date): walls 19/20/137/94/3868 B
(`scratchpad/casrbrk_walls.out:788-804`, 2026-10-11) · 877 B on 10-05 and the
Phase A/B table (`docs/plan-main-rom-space-2026-10.md` "Progress") · 105
commits since 10-05 (`git log`) · tier counts and the 13 BUDGET rows
(`tools/tier_table.py --all`, today) · every TODO line quoted above · ~130
cycles per call (`basic/subromcall.asm` D-STUBINL header) · the CALSLT
hypothesis refuted and the 2.87× marginal store (`docs/spec-basic-interpspeed.md`
§5) · kwtime function ratios (`scratchpad/openwild_kwtime.out`, Oct 7) ·
Route B/C/D findings and the 09-24 evict ranking (memory
`carve-routes-measured-shut`, `scratchpad/evict_scout.out`) · de-eviction
refuted, 457 B duplication (memory `rom-region-structure-review`) · 19 + 29
tenants (`sub/sub.asm`, readout `:803-804`) · Phase C prices (plan §1, §3).

**Inferred / estimated [I]**: the per-file size map (my script over the .sym
files, ±few %) · "≈100–150 B/day" demand rate · "≤300 B cheaply, 1.2–1.8 KB
with co-routines" · the 36 µs / 0.2 % scale argument · banking's ~13-cycle
cost · the MSX2 6–12 KB table and the `EXBRSA`/3-2 conflict · every row of
table F.
