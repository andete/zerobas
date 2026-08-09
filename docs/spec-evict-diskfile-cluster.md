<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — evict the disk/file command cluster to sub-ROM tenants (free ~3–4 KB of page-1)

Status: **ARC CONCLUDED after Phase 2 (2026-07-21, user-decided).** Phases 1 + 2 LANDED
(§11/§12). **Phases 3–5 deprioritized — the yield premise did not survive measurement** (see
▼ ARC CONCLUSION below): Phase 1 lifted the ONE large self-contained CALSLT-side chunk (+1179 B);
everything left straddles `eval`/the resident `fat_io_*` RAM cursor/`program.asm`, so the
remaining phases would free only a few hundred bytes total (not §6's ~1.5–2 KB) AND require
duplicating `fat_io_getbyte`/`putbyte` into a tenant. With page-1 free at a healthy 1134 B and no
funder pending, the user chose to stop here rather than pursue low-yield / rising-risk evictions.
Reopen only if a concrete page-1 funding need re-emerges. History below preserved as-written.

Originally: **SIGNED OFF 2026-07-19** (user, at end of the commissioning session) — **handed over
to a new session for implementation.** Commissioned 2026-07-19 (user: "we do need to evict more,
large code blocks coming — can we evict all load/save/open/close related in one big block?").
This is the scope/design doc for the largest planned eviction: the disk/tape file command
subsystem. It generalises the proven `CALL FORMAT` split ([spec-evict-call-format.md]) from one
verb to the whole cluster. Repack-only; the lean 16 KB `basic.rom` stays byte-identical
throughout (every moved byte is behind `IF ROM_BASE < $4000`).

## ▼ ARC CONCLUSION — why Phases 3–5 were deprioritized (measured 2026-07-21)

After Phases 1–2 landed, a measurement pass over the remaining verbs (LOAD/SAVE/BLOAD/BSAVE/
MERGE/RUN + the Phase 4–5 channel/field verbs) established that the eviction's high-yield window
has closed:

1. **Phase 1 already lifted the only large self-contained CALSLT-side leaf** — the 1666 B FAT12
   primitive/sector engine (§11), +1179 B page-1. That was the yield; the spec's §6 "Phases 2–5:
   ~1.5–2 KB" figure was computed against pre-Phase-1 byte counts and does not hold post-Phase-1.
2. **Phase 2 confirmed the new reality empirically** (§12): the two directory verbs freed only
   +17 B net, because they were already thin orchestration over Phase-1 tenant shims.
3. **Everything remaining straddles.** Each remaining verb body interleaves `eval` (resident —
   e.g. BSAVE's `expect_comma_eval` for start/end addresses), the `fat_io_*` byte cursor, and
   `program.asm` (`new_prog`/`relink`/`run_prog`, resident). None is a liftable CALSLT-side leaf.
4. **The `fat_io_*` cursor is already optimally placed.** It is a thin *resident* RAM-buffer
   layer (`FSECTOR_BUF`/`FREAD_OFF`) that already delegates every sector access to Phase-1 tenant
   primitives (`fat_read_file_sector`, …). Moving it gains ~nothing and would break the shared
   `ARL_GETBYTE` polymorphic vector (disk/tape/console/field byte sources all route through it) —
   the exact hazard §11 flagged when it deferred the cursor.
5. **Any further verb eviction is Phase-2-sized AND adds duplication.** The binary BLOAD/BSAVE
   loops could move (~tens–low-hundreds of bytes each) only by *duplicating* `fat_io_getbyte`/
   `putbyte` into the tenant (they must stay resident for the ascii `ARL_GETBYTE` path). Poor
   yield-to-risk, worsening for the disk-write and program-load verbs.

Net: the disk/file cluster is now split as well as it usefully can be without a redesign of the
byte-cursor/vector architecture. If a future feature creates real page-1 pressure, the best next
lever is likely NOT more file-cluster eviction but the untouched non-file targets or a C-BIOS
repack pass (see [[basic-rom-space-and-growth]]).

**▶ START HERE (new session).** Begin **Phase 1 — `fat.asm` anchor** (§4). First resolve the
Q-A shape decision (§9.1) empirically: prototype the fat-alone marshalling cost (~49 call-site
stubs) and measure, then choose fat-alone vs a cohesive fat+binary-verbs first bite. The sign-off
covers the full phased plan; §9's per-phase sub-questions (Q-A Phase-1 shape, Q-B INPUT#/PRINT#
round-trips) are to be pinned empirically **as each phase is reached**, not re-escalated for
sign-off. Phases 4–5 (sequential/random I/O — higher risk) get a go/no-go re-confirm with the
user when reached. Discipline: gate + adversarial VG-8020/CF-3300 pass per phase (§8); the
green-build-hides-bugs lesson is load-bearing. Funds D-F2-2 A2+VPEEK ([[df2-2-intarg-coercion-arc]],
impl parked at `scratchpad/a2-vpeek-impl.patch`) once Phase 1 frees page-1.

Related: [[subrom-tenant-playbook]] (the reusable how-to), [[math-pack-subrom-tenant]] (A-not-
preserved-across-CALSLT, page-0/1 visibility), [[load-error-is-not-abort]] (the shared error
handler's return contract — load-bearing here), [[makefile-subparts-stale-tenant]] +
[[ips-rebuild-after-basic-change]] (the build-staleness traps).

---

## 0. Why this needs its own spec (the classification)

The prior evictions moved **pure, self-contained** code (tokeniser, detokeniser, PRINT USING
scanners, math transcendentals, string heap): a tenant that takes marshalled inputs, computes,
returns outputs, and **never calls back into main**. Every such clean-pure target is now gone
(measured 2026-07-19; see [spec-basic-df2-2-intarg-coercion.md] §5's funder hunt). What remains
big is the disk/file cluster, which is **not** pure — it interleaves `eval` and disk `CALSLT`
mid-verb — so it cannot be lifted verbatim. It evicts only via a **per-verb split**, at cluster
scale. That is a different, larger, riskier move than any prior eviction, hence its own spec.

---

## 1. What the cluster is (in-tree survey, 2026-07-19)

Page-1 footprint (attributed by `tools`-free symbol-gap analysis over `build/basic-reloc.sym`):

| File | Page-1 B | Verbs / role |
|---|---:|---|
| `fat.asm` | 2092 | FAT12 primitive layer: mount/find/next-cluster/alloc/dir-create/dir-update/delete + `fat_io_*` (open/create/append/close/getbyte/putbyte). **out=0** (calls nothing external bar the disk-ROM CALSLT). |
| `files.asm` | 1894 | `OPEN`/`CLOSE`/`INPUT#`/`LINE INPUT#`/channel machinery (`init_filechan`, `fch_select`, `fch_valid`). |
| `field.asm` | 1188 | Random-access records: `FIELD`/`GET`/`PUT`/`LSET`/`RSET` (`fld_init`, `fld_lookup`). |
| `save.asm` | 1068 | `SAVE`/`BSAVE` (+ `do_bsave`). |
| `cload.asm` | 1064 | Tape `CLOAD`/`CSAVE` + `parse_close_run`. |
| `bload.asm` | 588 | `BLOAD` + the **shared** `parse_disk_fcb` / `load_error`. |

**Total ≈ 7894 B** of page-1. Not all evicts (eval-heads + the channel-select hot path +
`load_error` stay resident); realistic freeable bulk **≈ 3–4 KB**.

**External interface (measured, cluster = {bload,save,cload,files,field}):**
* **Inbound — 30 public entry points**, almost all from `interp.asm`'s statement dispatch
  (`do_load/save/run/bload/bsave/cload/csave`, `ex_open/close/input/line/kill/name/files/
  maxfiles/field/get/put/lset/rset/merge`, `init_filechan`, `autoexec_run`). The **exceptions
  that matter**: `fch_select`/`fch_valid` are called from `expr.asm` (EOF/LOF), `print.asm`
  (PRINT#), `strvar.asm` (string file reads) — i.e. **from inside `eval`/print context**;
  `load_error` from `format.asm`/`print.asm`; `fld_init`/`fld_lookup`/`read_into_strscr` from
  `vars.asm`/`strvar.asm`/`input.asm`.
* **Outbound — 42 distinct targets**: dominated by `fat.asm` (17, 49 calls — becomes internal
  once fat moves with the cluster), then `eval` (expr.asm, 15 calls), `interp.asm` parse
  helpers (`skip_spaces`/`upcase`/`is_letter`/`stmt_error`/`check_expr_errors`/`exec_stmt`),
  `program.asm` (`dispatch_line`/`new_prog`/`relink`/`run_prog`), and a long tail (vars, repl,
  print `pchar`/`print_crlf`, str-engine, list, input, `eval_chan`, `str_eval`).

---

## 2. The architectural constraint (the crux — precedent-backed)

A sub-ROM tenant call maps the sub-ROM into **either page 0 or page 1, never both** (verified
in `basic/subromcall.asm` + `sub/format.asm`; addresses from `build/basic-reloc.sym`):

| Tenant page | Page 0 = | Page 1 = | Tenant CAN | Tenant CANNOT |
|---|---|---|---|---|
| **sub page-0** | sub-ROM | main BASIC ROM | reach `eval`@$4A56, `fat`@$5F0E (page-1 main) | `CALSLT`@$001C (BIOS switched out) → **no disk I/O** |
| **sub page-1** | slot-0 BIOS | sub-ROM | `CALSLT` → disk I/O | `eval`/`fat` (main page-1 switched out) |

Every file verb **straddles** both worlds: it parses arguments with `eval` (page-1) and does
disk I/O via `CALSLT`→disk ROM ($001C, page-0 BIOS). **No single tenant call holds both.**
`sub/format.asm:10-13` states this verbatim — `CALL FORMAT` hit the identical wall and resolved
it with a **split**: the eval-using menu/dispatch stayed resident; the CALSLT-using build/write
bulk became a **sub page-1 tenant with its own duplicated CALSLT** (`sub/format.asm:63`,
because main's `fat.asm` write path is invisible to a page-1 tenant).

**Consequence for this eviction: the split is forced, not a choice.** Resident keeps the
eval/parse; the tenant (sub page-1) holds the CALSLT-side I/O bulk.

### 2.1 Why `fat.asm` stays BASIC-side — we do NOT move FAT to the disk ROM

The obvious "isn't FAT a disk thing?" reaction is wrong for zerobas, by a **deliberate, validated
Phase-1.5 decision** (`basic/PROVENANCE.md` §"disk DSKIO host engine"). The standard disk-ROM
interface every MSX1 disk ROM publishes is **`$4010` DSKIO — pure physical sectors** (read/write
N sectors at logical sector D to buffer HL). There is **no standard "open file by name" entry**:
each disk ROM resolves `"A:name"` (BPB/FAT/dir) *internally* and exposes only raw sectors. So the
file→sector FAT12 logic is **private to each disk ROM**, not delegable across the public boundary.

zerobas therefore **owns the FAT12 engine loader-side** (`basic/fat.asm`, ported from
`disk/fat.asm`) and drives *any* disk ROM through `$4010` DSKIO. This is the **disk-ROM-
independence tax**, and it is the right call — proven: `SAVE`/`LOAD`/`BLOAD`/`RUN` round-trip
byte-identically on our own `disk.rom` **and** a foreign National **CF-3300**, and cross-BIOS on
a real Philips **VG-8020** (`probes/disk/disk_probe_crossbios.py`, `disk_probe_*_disk.py` — ALL
PASS on both disk ROMs). The pre-Phase-1.5 alternative (calling the disk ROM's private
`bdos_entry`/`$F37D` FCB layer) **failed every disk verb on CF-3300** and is retired.

**So this eviction MUST NOT delegate FAT back to the disk ROM** — that re-breaks independence (the
loader would again depend on a private file layer no foreign disk ROM implements). The sub-ROM
tenant keeps `fat.asm` **BASIC-side** (still `$4010`-DSKIO-driven, still disk-ROM-independent),
merely relocated off main page-1 into the zerobas-BASIC sub-ROM. A sub page-1 tenant keeps page-0
BIOS mapped, so its `CALSLT`→DSKIO path is unchanged. This is precisely why `fat.asm` is the ideal
Phase-1 anchor (§4): a self-contained engine (`out=0`) that must stay BASIC-side by design yet has
no reason to occupy scarce main page-1.

---

## 3. The design — resident head / tenant I/O body

For each evicted verb:

```
  [resident head, main page-1]                 [sub page-1 I/O tenant]
  ex_<verb>:                                    tnt_<verb>:
    <eval/parse args>            marshal          <bulk disk logic>
    -> fill DISKOP param block   ----------->     read DISKOP block
       in page-3 RAM             subrom_call      call fat_io_* (SUB-LOCAL copy)
    call subrom_call(idx)                         -> its own CALSLT to disk ROM
    <- read results from block   <-----------     write results to DISKOP block, ret
    surface load_error on CF
```

**Moves into the tenant (sub page-1):** `fat.asm`'s I/O primitives (they already are pure
CALSLT-side code — the natural first tenant, §4) and each verb's **I/O bulk** (sector/cluster
walking, directory scan, byte-copy loops, FCB build once its inputs are marshalled).

**Stays resident (main page-1), non-negotiable:**
* **`eval` and every eval-consuming parse head** — a tenant cannot reach `eval`.
* **`fch_select`/`fch_valid`/`init_filechan`** — called from `expr.asm`/`print.asm`/`strvar.asm`
  *inside* eval/print context (`EOF(n)`, `PRINT#`), which the tenant cannot host. The channel
  table itself lives in RAM (page-3), reachable from both sides.
* **`load_error`** — the shared file-error handler (~85 call sites, [[load-error-is-not-abort]]):
  its `ret`-not-abort contract means nested tenant rejects must return CF and let the resident
  head `jp c,load_error` (the BSAVE-,Q bug pattern). The tenant NEVER jumps to `load_error`
  directly; it returns CF (format's "Cy cannot ride back through CALSLT" rule, `sub/format.asm:30`
  — so results ride in the DISKOP block, not the carry).

**`parse_disk_fcb`** (the shared 8.3/FCB parser, today in bload.asm, called by OPEN/SAVE/CLOAD):
it is *parse* (no CALSLT) but is invoked by many heads → **stays resident** (page-1), feeding
the marshalled filename into the DISKOP block. (This is the piece that made bload.asm look like
a clean leaf and is not — it is shared infrastructure.)

---

## 4. Phase plan (each phase independently gated + lead-verified)

Ordered to de-risk the pattern before scaling, and to minimise interim resident↔tenant churn.

1. **Phase 1 — `fat.asm` → sub page-1 tenant (the anchor).** It is the cleanest big move:
   `out=0`, already CALSLT-based, matches the page-1-tenant model exactly. Its ~13 public
   entries become the marshalled ABI (§5). **Interim cost:** its ~49 inbound call sites (across
   the 5 verb files, still resident this phase) convert to `subrom_call`s — a real but bounded,
   mechanical change. **OPEN Q-A (§9):** this interim marshalling is partly *undone* when the
   verbs later move into the same tenant page (verb→fat becomes sub-local again). Alternative:
   make Phase 1 a **cohesive sub-cluster** (fat + the heaviest, most self-contained fat users,
   e.g. the SAVE/BSAVE/BLOAD binary-image family) so callers are co-resident in the tenant from
   the start. Decide before Phase 1.
2. **Phase 2 — directory verbs** `KILL`/`NAME`/`FILES` — simplest (filename in → one I/O op,
   little interleave). Proves the head/body split on real verbs at low risk.
3. **Phase 3 — program load/store** `LOAD`/`SAVE`/`BLOAD`/`BSAVE`/`MERGE`/`RUN"f"` — parse
   filename+options resident, bulk transfer in the tenant. Interacts with `new_prog`/`relink`/
   `run_prog` (program.asm, resident) — those run in the resident head after the tenant load.
4. **Phase 4 — sequential file I/O** `OPEN`/`CLOSE`/`INPUT#`/`LINE INPUT#`. **Highest risk:**
   INPUT# interleaves reading (tenant) with delivery to `eval`/string-scratch (resident) — may
   need **multiple tenant round-trips** per statement (read-block → resident convert → read
   more). **OPEN Q-B (§9).**
5. **Phase 5 — random access** `FIELD`/`GET`/`PUT`/`LSET`/`RSET` — record buffer marshalling;
   `fld_lookup` stays resident (called from strvar mid-eval).

Land + gate + adversarial-pin each phase; never batch two.

---

## 5. Tenant / marshalling ABI

* **`DISKOP` param block** in page-3 RAM (always mapped across the slot switch), sized for the
  widest verb: filename (8.3 / raw), channel #, load/exec addresses, length, record #, mode,
  drive, and a **result field** (status byte — the carry surrogate, `sub/format.asm:30`). Shape
  mirrors the `ARY_*` block (`sub/arrays.asm`) and format's block. Exact layout: TBD in Phase 1.
* **`subrom_call` contract** (`basic/subromcall.asm`): `IX = SUBROM_ENTRY_BASE_P0 + 3*index`;
  CF=1 without calling if the sub-ROM is absent (reduced builds) → resident head errors; runs
  under DI with page-0 (or the tenant's non-mapped page) switched out; **CALSLT clobbers all
  registers** — the head guards anything live and reads all results from `DISKOP`, never regs.
* **Sub-local disk CALSLT:** the tenant carries its own `dskio_calslt`/`fat_io_*` (the one
  sanctioned duplication, exactly as `sub/format.asm` duplicates `write_sector`), because main's
  `fat.asm` is invisible to a page-1 tenant. After Phase 1, fat's primitives ARE the tenant's,
  so later verb bodies call them sub-locally (no duplication beyond fat itself).
* **A-not-preserved** across CALSLT ([[math-pack-subrom-tenant]]): all returns via `DISKOP`/FAC/
  RAM, never a live A/flag.

---

## 6. Space accounting (measure, don't estimate)

Per phase, record from `tools/check_reloc.py` (`__MEAS_PAGE1_END`) the page-1 free delta and
the tenant (sub) occupancy, and assert lean `basic.rom` byte-identity. Targets:

* Phase 1 (fat): frees ≈ **2 KB** page-1 gross, minus the ~49 marshalling stubs (~3–5 B each →
  ~200–250 B) → **net ≈ 1.7–1.8 KB**. Immediately funds D-F2-2 A2+VPEEK (33 B) + stage B (~40 B)
  with vast headroom.
* Phases 2–5: additional **~1.5–2 KB** as verb bodies move.

The sub-ROM must have room for fat + bodies; confirm sub page-1 occupancy has the budget before
each phase (the sub has spare after the tokeniser/detok/format tenants — measure).

---

## 7. Build wiring (the staleness traps — do not skip)

* Every new `sub/*.asm` include MUST be added to the Makefile `SUB_PARTS` or a **stale sub.rom
  ships silently** and green suites validate old code ([[makefile-subparts-stale-tenant]]).
  Force-rebuild the sub after a sub-only edit.
* Machine-based probes run the installed `zerobas-msx1.ips`, NOT `build/basic.rom` — **rebuild +
  reinstall the IPS** after any basic/ or sub/ edit or the disk gates test STALE code
  ([[ips-rebuild-after-basic-change]]).
* Update both `SUBROM_IDX_*` copies (resident + sub) when adding tenant indices.

---

## 8. Acceptance & gates (the guardrail — disk I/O is critical)

MUST stay green after every phase (this is the whole disk/file surface):
* `make diskbasic-acceptance` (34 lean + 34 repack) — the BASIC-side disk verb corpus.
* `make bdos-acceptance` / `bdos-cbios-selfcheck` — BDOS parity + C-BIOS self-consistency.
* `make unit-test`, `array-acceptance` (150), string/input/float/math/error/error-trap.
* Lean `basic.rom` byte-identity; `check_reloc`/`check_kwtable_identity`/`check_resident_abi`/
  `check_tenant_closure` + a manual page-0/page-1 closure audit per tenant.
* **Test-disk mutation guard** ([[test-disk-mutation-gotcha]]): /tmp copies, `git status` +
  restore after — disk WRITE verbs (SAVE/KILL/NAME/PUT) mutate the .dsk.
* **Adversarial + empirical pass mandatory per phase** ([[error-handling-arc]] recurring lesson):
  a green build has hidden catastrophic register/order bugs every prior slice; run the disk
  differential on a real VG-8020 + CF-3300 oracle, boot-per-case where feasible.

---

## 9. Open decisions (sign-off)

1. **Q-A — Phase 1 shape:** `fat.asm` alone (clean, but ~49 interim marshalling stubs partly
   undone later) vs a **cohesive fat + binary-image-verb sub-cluster** first (less rework, bigger
   first bite). Recommend deciding empirically: prototype fat-alone marshalling cost first, then
   choose.
2. **Q-B — INPUT#/PRINT# round-trips** (Phase 4): can sequential file I/O be structured as
   read-block-then-resident-convert (bounded round-trips), or does the interleave force the whole
   INPUT loop resident (evicting only the block reader)? Pin on the real verb before Phase 4.
3. **Q-C — `parse_disk_fcb` / `load_error` placement:** confirmed resident here — verify no phase
   needs them tenant-side (would force a duplication).
4. **Q-D — DISKOP block RAM budget & layout** (§5): confirm the widest-verb field set fits the
   available page-3 scratch without colliding with FCB/channel buffers.
5. **Scope confirm:** all five phases, or stop after Phase 1–3 (the high-yield, lower-risk part)
   and leave sequential/random I/O resident?

---

## 11. Phase 1 — concrete design (empirical Q-A resolution, 2026-07-19)

The ▶START measurement is done. **Q-A is resolved to a third shape, not either menu option**
(user-approved 2026-07-19): move **only the FAT12 primitive/sector layer**, keep the
`fat_io_*` byte cursor resident. Rationale is empirical:

**Measured layer split of `fat.asm` (2121 B, from `build/basic-reloc.sym`):**

| Layer | Span | Bytes | Profile |
|---|---|---:|---|
| FAT12 primitive/sector | `dskio_calslt $58E0` → `fat_io_open $5F0E`, + `fat_delete $60D5`→`$6129` | **~1666 (79%)** | coarse (per-sector/cluster/dir), CALSLT-pure, RAM-interfaced, no `eval`/vector coupling |
| `fat_io_*` byte cursor | `fat_io_open $5F0E` → `fat_delete $60D5` | ~455 (21%) | per-**byte**, reached via the `ARL_GETBYTE` **polymorphic RAM vector**, called from eval/print/input context |

**Why the cursor must NOT move now:** `fat_io_getbyte` is 18 of the ~54 sites (15 direct + 3
vector installs). `ARL_GETBYTE` (RAM) is pointed at *many* byte-sources (disk getbyte, tape
reader, console LINEBUF splitter, `CAS:` reader) and invoked indirectly from the resident
`ascii_read_lines` loop. If `fat_io_getbyte` moved into a page-1 tenant its address is only
valid while the sub is paged in → `call (ARL_GETBYTE)` lands on a random main byte. Fat-alone
would force a resident trampoline **plus** a page-switching `subrom_call` on a per-byte hot path,
undone later anyway. The cursor moves in Phase 3/4 with its consuming loops (getbyte then
sub-local again). This phase leaves the entire per-byte/vector surface resident and untouched.

**Tenant = the primitive engine (sub page-1), one index, selector-dispatched.** Rather than
burn ~13 P1 indices, use a **single** new `SUBROM_IDX_FATPRIM` (next free P1 index = **12**;
`SUBROM_ENTRY_BASE_P1=$4010`, indices 1–11 taken through `SCANSTMT`) whose tenant entry reads a
`DISKOP_OP` selector byte and internally `jp`s to the requested primitive with **HL/DE intact**
(`subrom_call` passes HL/DE through CALSLT, `basic/subromcall.asm:60-68`). Selector table uses
BC for indexing so HL/DE survive to the primitive.

**Uniform shim convention (robust against the register-bug trap — the load-bearing lesson).**
Every primitive is register-input, mostly RAM/CF-output; the *only* register outputs across the
whole set are: `fat_alloc_cluster`→HL (2 ext callers, field.asm 576/599), `name_cmp`→Z (1 ext,
files.asm:105), `read_sector`/`write_sector`→A=err (usually only CF consumed — Sonnet must
verify no site reads A). `fat_next_cluster`→HL is **internal-only** (fat_advance/fat_delete) →
stays tenant-local, no marshalling. So adopt ONE convention for ALL: on tenant exit, stash
`{HL, A, a CF/Z status byte}` into a small **`DISKOP` result block** (page-3 RAM); every resident
shim reloads HL+A and reconstructs CF/Z **identically**. Safe because DSKIO/CALSLT already
clobbers HL at every existing call site — no caller relies on HL-preservation across a primitive,
so a uniform reload changes nothing for the RAM-output primitives.

**Resident shims replace the moved bodies**, keeping all ~34 call sites (24 external verb→prim +
~10 cursor→prim) **byte-for-byte unchanged** (`call read_sector` still works — `read_sector` is
now a ~12-16 B resident shim). Net free ≈ **1666 − ~200 shim ≈ 1460 B** page-1 → funds D-F2-2
A2+VPEEK (33 B) + stage B with headroom. Sub page-1 has ~10 KB free (last tenant `scan_stmt_end`
≈ `$579E`, page-1 runs to `$7FFF`) → 1.6 KB fits easily.

**Lean byte-identity idiom (mirror `basic/format.asm:125-161`).** Primitive bodies live in a
shared `basic/fat-prim-body.inc` (byte-identical bytes). `IF ROM_BASE >= $4000` (lean 16 KB
cart): include the bodies inline exactly as today → `basic.rom` unchanged. `ELSE` (repack): main
emits only the shims; `sub/fatprim.asm` includes `fat-prim-body.inc` + the selector dispatch +
its own sub-local `dskio_calslt`/read/write CALSLT copy (the sanctioned duplication, exactly as
`sub/format.asm` duplicates `write_sector`, because main's is invisible to a page-1 tenant).

**Build wiring (§7 traps):** add `sub/fatprim.asm` (+`fat-prim-body.inc` dep) to Makefile
`SUB_PARTS`; add `SUBROM_IDX_FATPRIM equ 12` to **both** index copies; force-rebuild sub +
rebuild/reinstall the IPS before any machine gate.

**Q-C/Q-D confirmed for Phase 1:** `parse_disk_fcb`/`load_error` untouched (not primitives);
`DISKOP` result block is tiny (HL:2 + A:1 + status:1 + op:1 = 5 B) → trivially fits page-3
scratch without colliding with FCB/channel buffers.

---

## 12. Phase 2 — concrete design + outcome (KILL + NAME, LANDED 2026-07-20)

**Scope reshaped by measurement (user-decided).** Phase 1 had already evicted the FAT12
primitive/sector engine, so the directory verbs were left as thin orchestration over sub-ROM
shims. Measured freeable page-1 for the three §4 directory verbs: FILES ~150 B (but its emit
loop interleaves `CHPUT` + main-resident `print_crlf` — a head/body fork §4 didn't anticipate),
NAME ~44 B, KILL ~0 (its `dk_loop` ≈ the `subrom_call` boilerplate that replaces it). Given the
yield/risk had shifted from §4's assumptions and page-1 free was a healthy 1117 B with no pending
funder, the user chose **KILL + NAME only** (leave FILES resident, avoiding the CHPUT fork). The
value of the phase is proving the **selector-dispatched verb-body tenant** that Phase 3 scales up,
not the bytes.

**Tenant = one selector-dispatched entry (like fatprim), `SUBROM_IDX_DIRVERB=13`.**
`dirverb_tenant` reads `DISKOP_OP` and branches: `DISKOP_SEL_KILL=0` → `tnt_kill`,
`DISKOP_SEL_NAME_STAMP=1` → `tnt_name_stamp`. A separate value namespace on the same `DISKOP_OP`
cell as fatprim (only one `subrom_call` is in flight at a time). Both bodies call the Phase-1
primitives (`fat_delete` / `read_sector` / `fatprim_write_sector`) **sub-locally** — they are
co-resident in the same sub page-1, so no nested marshalling. `sub/dirverb.asm` is included after
`sub/fatprim.asm` in `sub/sub.asm`; it is a pure RAM+BIOS(CALSLT) leaf (no resident-ABI import).

**NAME is stamp-only (no new RAM).** The `$E0ED+` gap is fully claimed (DSV/TSV/FILES/FCH), so a
second 11-byte name buffer isn't free. The resident head keeps `fat_mount`+`fat_find` as the
existing shims (OLD name in `DISK_FCB_NAME`), then parses the NEW name into `DISK_FCB_NAME`; the
tenant only does read+overwrite+write via `FWR_DIRSEC`/`FWR_DIROFF`. This preserves the ORIGINAL
find-old-then-parse-new ordering. (A full-op NAME folding mount+find into the tenant would need
the buffer + reorder new-name parsing before the find; harmless anyway since `parse_disk_fcb`
errors and old-not-found both route to `load_error`, but stamp-only avoids the question.)

**Status polarity (each read only by its own head).** NAME_STAMP → 0 ok / 1 error; KILL →
deleted-any flag (0 = nothing matched → head raises "File not found" via `load_error`; nonzero =
ok). KILL mirrors the original `do_kill` bug-for-bug (a mid-loop I/O error is treated as "no
further match"). Lean cart keeps both verb bodies inline (byte-identical); repack emits the
`subrom_call` heads via the `ELSE` branches of `do_kill`/`do_name`.

**Outcome + gates (2026-07-20).** Page-1 free **1117 → 1134 B (+17 B)**; lean `basic.rom`
byte-identical. `check_tenant_closure --page1` OK (14 tenants incl. `dirverb_tenant`, no
main-page-1 escape); `subrom-abi-check` OK; `unit-test` 46/46. `diskbasic-acceptance` lean
**34/34** + repack **34/34** — boot-per-probe differential vs real CF-3300, incl.
`disk_probe_kill.py`/`disk_probe_name.py` (byte-identical disk images). Adversarial boot-per-case
(the paths the corpus skips): no-match `KILL"NOSUCH.FIL"` → "load error"; absent-old NAME → "load
error". /tmp disk copies; no committed `.dsk` mutated. Landed with the `.ips`/`.bps` repack
patches regenerated ([[ips-rebuild-after-basic-change]]).

**Q-A/Q-C/Q-D for Phase 2:** `parse_disk_fcb`/`load_error` stay resident (confirmed — the tenant
never reaches them; it returns `DISKOP_STATUS` and the head does `jp z/c,load_error`). No new RAM.
**NEXT = Phase 3** (program load/store LOAD/SAVE/BLOAD/BSAVE/MERGE/RUN, spec §4) — the first
genuinely high-yield phase.

---

## 10. Clean-room

Original code; the split mechanism, DISKOP marshalling, and sub-local CALSLT are own-design
(the `CALL FORMAT` precedent, MSX2 Technical Handbook CALSLT/EXBRSA/sub-ROM-signature ABIs). No
reference-ROM disassembly; the shared MSX-DOS-1 disk kernel is reimplemented by contract, never
copied ([[msx-diskrom-shared-kernel]], [[no-reference-rom-disasm]]). Record in
`basic/PROVENANCE.md` per phase on landing.
