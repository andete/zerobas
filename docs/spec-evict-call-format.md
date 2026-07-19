<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — evict `CALL FORMAT` to a sub-ROM tenant (free page-1 to fund S2b)

Status: **DRAFT — sign-off pending.** Funding slice for error-handling **S2b**: the S2b
main-resident glue needs ~140 B of page-1 that isn't there (17 B free; measured — see
[spec-basic-error-handling-s2b-packet.md](spec-basic-error-handling-s2b-packet.md) §8
and the WIP on branch `wip/s2b-mechanism`). String-dedup (lever 1) is dry and the S2b
tenant split (lever 3) is exhausted, so a **feature eviction** is required. The user
chose `CALL FORMAT` as the funder and chose to run it as **its own prior slice** (spec +
sign-off, land, then resume S2b) rather than folding it into S2b.

Repack-only: the lean 16 KB `basic.rom` stays **byte-identical** (the c3fc2d8 shared-
`.inc` pattern — lean keeps `do_format` resident inline, repack evicts it). Precedent:
[spec-evict-printusing.md](spec-evict-printusing.md) / commit c3fc2d8 (freed 217 B for
S2a the same way).

---

## 0. The classification correction (why this needs its own spec)

The S2b implementation agent proposed evicting `CALL FORMAT` as a *"clean page-0
Shape-B tenant, all callees main-page-1-only."* **That classification is WRONG**, traced
this session:

* `do_format` (basic/format.asm) calls `write_sector` (basic/fat.asm:87), which tail-
  calls `dskio_calslt` (fat.asm:61) → **`call CALSLT` ($001C)** — a **page-0 BIOS** entry.
* Per the tenant playbook §2, a **page-0 tenant runs with slot-0 page-0 (BIOS + low
  region) switched OUT** — so `CALSLT` is invisible. `write_sector` **cannot run from a
  page-0 tenant.** The agent checked callee *file locations*, not the *page-visibility*
  of the disk-call path.
* But `do_format` ALSO needs `print_string` / `read_line` / `upcase` — **main-BASIC
  page-1** routines, which a **page-1 tenant** (BIOS visible, main BASIC switched out)
  can't see either.

So `do_format` straddles both pages: **neither pure tenant shape works.** The design is a
**split** (playbook Shape C-adjacent), below.

---

## 1. What `CALL FORMAT` is (in-tree survey)

* `basic/format.asm` (254 lines), included **unconditionally** by `basic/main.asm:187`
  → present in **both** lean and repack. Statement dispatch: interp.asm:173-176
  (`CALL_TOKEN` / `_` → `ex_call` / `ex_call_us`), **not** behind `IF ROM_BASE<$4000`.
* Structure:
  * **Dispatch (small):** `ex_call` / `ex_call_us` / `exc_name` / `exc_skip` / `exc_go`,
    `fmt_match_format` + `fmt_name` "FORMAT". Matches the keyword, calls `do_format`,
    `jp c,load_error` on I/O error, else `jp exec_stmt`.
  * **The bulk (`do_format` + helpers):** the interactive geometry menu (`fmt_menu`:
    `print_string "1=360k 2=720k? "` + `read_line` + parse), then builds and writes every
    filesystem sector — boot/FAT/root — into `FSECTOR_BUF` (RAM) via `fmt_zero_buf`,
    `fmt_geom_byte`, `fmt_geom_word`, looping `write_sector`. Data: `GEOM_360K` /
    `GEOM_720K` tables, `fmt_menu_text`, `fmt_name`.
* Runtime dependencies of `do_format`, by page:
  | callee | lives | page-view need |
  |---|---|---|
  | `print_string`, `read_line`, `upcase` | main page-1 | needs **page-1 main** visible |
  | `write_sector` → `dskio_calslt` → `CALSLT` | fat.asm (pg1) → **BIOS $001C** | needs **page-0 BIOS** visible |
  | `FSECTOR_BUF`, `GEOM_*`, sysvars | RAM / own data | always visible |
  | `load_error`, `stmt_error`, `exec_stmt` | main page-1 (dispatch only) | resident glue, not in tenant |
* **Shared-routine caveat:** `write_sector` / `read_sector` / `dskio_calslt` are used by
  the *rest* of disk-BASIC (SAVE/LOAD/FILES/BSAVE…). They stay **resident** — the tenant
  must NOT move them; it carries its **own** minimal disk-write path instead (§3).

Clean-room status: already clean (basic/PROVENANCE.md §CALL FORMAT / §disk DSKIO host
engine). This eviction is a pure relocation — no algorithm change, no new provenance.

---

## 2. The split (the design)

**Resident stays main page-1 (repack):** the dispatch + the **console menu** + the
tenant call glue. Console I/O (`print_string`, `read_line`, `upcase`) is page-1 main and
trivially resident; keeping the menu main-side removes the "need main page-1 from the
tenant" half of the straddle.

**Tenant goes sub page-1** (`SUBROM_ENTRY_BASE_P1 = $4010` island — a page-1 tenant, so
**BIOS/`CALSLT` is visible**, mirroring the 163× DSKIO pattern the playbook §3A cites):
the pure sector-build + write loop. It reads the chosen geometry, zeroes/fills
`FSECTOR_BUF` from the `GEOM_*` tables (RAM only), and writes each sector to the disk via
its **own** `dskio_calslt`-equivalent (a ~10 B sub-local copy calling `CALSLT` directly —
legal on a page-1 tenant; do NOT call main's `write_sector`, which is switched out). It
touches **no main-BASIC page-1 code** — so the straddle is resolved.

### Control flow (repack)

```
ex_call/exc_go (resident):
    ... match "FORMAT" ...
    ld   hl,fmt_menu_text        ; MENU stays main-side
    call print_string
    call read_line               ; LINEBUF <- choice (page-1 console, resident)
    <parse choice -> A = 0 (360k) / 1 (720k); default/invalid -> reprompt or 360k>
    ld   (FMT_GEOMSEL),a          ; RAM param cell (page-2/3, visible to the tenant)
    <guard HL; ld ix, SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FORMAT; call subrom_call>
    ; subrom_call returns CF=1 WITHOUT calling if the sub-ROM is absent (reduced build)
    jp   c,load_error             ; absent OR the tenant reported an I/O error (see §4)
    jp   exec_stmt

format_tenant (sub page-1, SUBROM_IDX_FORMAT):
    ld   a,(FMT_GEOMSEL)
    <select GEOM_360K / GEOM_720K (both tables live sub-side now)>
    <build+write boot, FATs (×numFATs), root — fmt_zero_buf/geom_byte/word over RAM,
     each sector via sub-local dskio_write (CALSLT $4010, direction CY=1)>
    <on any DSKIO error: set the RAM error flag, return>
    ret                          ; CF/A per §4
```

**Geometry-menu ownership:** the interactive menu (choice of 360k/720k) is a real
behaviour to preserve (`fmt_menu`, format.asm:109) — it stays main-side verbatim. Only
its **text** (`fmt_menu_text`) is small; the reclaim is the *build/write* bulk, which is
the large part.

---

## 3. Tenant ABI

Per the playbook §4 recipe:

1. **Entry:** append `jp format_tenant` to the **page-1** entry table
   (`SUBROM_ENTRY_BASE_P1 = $4010`); new index `SUBROM_IDX_FORMAT` (next free, synced in
   BOTH `sub/equates.inc` and `basic/sysvars.inc`). Never reorder existing entries.
2. **Args → RAM:** `FMT_GEOMSEL` (1 B, new cell in a `SUB_*` scratch region, page-2/3).
   All parsing/console stays main-side (recipe: "parsing/`eval` always stays main-side").
3. **Main stub:** guard `HL`/live pointers (CALSLT clobbers all regs), `call subrom_call`
   with `IX` = entry. `CF=1` + no call if sub-ROM absent → `load_error` (absence path,
   same as the disk verbs' own reduced-build behaviour).
4. **Result ← RAM/CF:** §4.
5. **DI/EI:** `write_sector` today runs under the normal interpreter (interrupts on);
   the tenant issues several DSKIO CALSLTs. **Open (Q3):** does formatting take long
   enough to need the interrupt trampoline (spec-basic-subrom-trampoline.md), or does the
   existing per-sector DSKIO tolerate a DI window? Resolve by measuring format wall-time;
   default to the trampoline only if a bare-DI format visibly hangs (unlikely per the
   163× DSKIO precedent, which runs DI per call).

### Sub-local disk write (the one duplication)

The tenant needs `dskio_calslt`'s ~10 B (load `DISKSLOT` into the `SCAN_IY` id, `IX =
DSKIO_ENTRY $4010`, `scf`, `call CALSLT`). Duplicated sub-side (page-1 tenant sees
`CALSLT`); `write_sector`'s 5-line wrapper is likewise trivial to inline. `read_sector`
is **not** needed by FORMAT (write-only), so only the write path duplicates. Cost: ~15 B
sub-side, negligible against the page-1 reclaim.

---

## 4. Error reporting

Today: `do_format` returns `CF` (write_sector's DSKIO CY); `exc_go` does `jp c,load_error`.
Preserve exactly: the tenant returns its DSKIO error disposition in **RAM** (a 1-B
`FMT_RESULT` flag, since `subrom_call` uses `CF` for the absence signal). Main stub:
`ld a,(FMT_RESULT)` / `or a` / `jp nz,load_error`, folded with the absence `jp c,load_error`.
`load_error` (ERR 19 family) is unchanged — this eviction does NOT touch the error arc's
`load_error` semantics ([[load-error-is-not-abort]]).

---

## 5. Space accounting (measure, don't estimate)

Target: free **≥140 B** page-1 (S2b's deficit) with headroom. `do_format` + helpers +
`GEOM_*` + strings is the bulk of format.asm's 254 lines — the agent measured the
`ex_call..GEOM_360K` span at **377 B**. Evicting the build/write bulk while keeping the
dispatch + menu resident should reclaim **~200-280 B** page-1 (repack) — comfortably past
140 B, leaving reserve for the error arc's future polish (ERR 21, `ERROR 0`, `load_error`
unification). **Measure after each move** (`tools/check_reloc.py`); if the resident menu
glue is bigger than expected, the reclaim still clears 140 B by a wide margin.

Lean: `do_format` stays resident inline via the shared-`.inc` pattern → lean `basic.rom`
byte-identical (hard gate).

---

## 6. Build wiring (the staleness traps)

* New sub file `sub/format.asm` (or a shared `basic/format-body.inc` included inline by
  the lean cart AND by `sub/format.asm` under `ROM_BASE<$4000`, c3fc2d8 style). **ADD IT
  TO `SUB_PARTS`** ([[makefile-subparts-stale-tenant]] — a sub include missing from
  `SUB_PARTS` silently ships a STALE sub.rom) and to `DEPS`. Force-rebuild the sub.
* `SUBROM_IDX_FORMAT` synced in `sub/equates.inc` + `basic/sysvars.inc`.
* Rebuild + reinstall the IPS before machine probes ([[ips-rebuild-after-basic-change]]).
* Tenant closure: `tools/check_tenant_closure.py` (page-1 mode) must confirm
  `format_tenant` reaches only sub-local page-1 code, the BIOS (`CALSLT`/DSKIO), or RAM —
  and **NOT** main-BASIC page-1 (which is switched out for a page-1 tenant). This is the
  inverse of a page-0 tenant's audit — verify the checker covers the page-1 direction.

---

## 7. Acceptance & gates

* **Functional gate = `diskbasic-acceptance`** (34, lean + repack). `CALL FORMAT` is
  exercised there (a format-then-verify case); it is the oracle-locked CF-3300-byte-
  identical FAT12 check ([[msxdos-oracle-disk]] / the disk arc). A formatted disk must be
  byte-identical to CF-3300's format, before and after eviction.
* **Adversarial/empirical:** format a scratch `.dsk` (a /tmp copy — [[test-disk-mutation-gotcha]]:
  openMSX can write back to a committed `.dsk`; use /tmp + `git status`/restore) on the
  repack build and diff the resulting filesystem bytes against a CF-3300 format and
  against the pre-eviction zerobas format. The 360k AND 720k menu paths both.
* **Standing gates:** `unit-test`; array (150) / input / string / float / math /
  diskbasic (34 lean + 34 repack) acceptance; tape battery; repack-boot; **lean
  byte-identity**; kwtable/resident-abi/tenant-closure. Nothing outside disk-BASIC should
  move — but run the full battery (a shared-routine edit surprised the diskbasic suite
  before — [[diskbasic-option-surface-audit]]).
* **DoD includes RUNNING these** ([[gate-during-implementation]]).

---

## 8. Open decisions (sign-off)

1. **Split shape confirm.** Resident = dispatch + console menu + glue; page-1 tenant =
   sector-build/write bulk with a sub-local `CALSLT` write path. Confirm (vs. keeping the
   whole thing resident and funding S2b some *other* way — but the user already chose this
   funder).
2. **Menu resident vs. sub.** Recommend the interactive 360k/720k menu stays **main-side**
   (removes the page-1-main dependency from the tenant, the whole point). Confirm.
3. **DI window vs. interrupt trampoline** (§3.5). Recommend bare-DI (measure; the DSKIO
   precedent runs DI per call); trampoline only if a format visibly hangs. Confirm the
   "measure first" disposition.
4. **Implementation model.** Per [[opus-vs-sonnet-model-split]] this signed-off spec is a
   Sonnet impl task; the lead runs the adversarial disk-byte differential + tenant-closure
   audit after. Confirm.

---

## 9. Clean-room

Pure relocation of already-clean-room code (basic/PROVENANCE.md §CALL FORMAT). No new
external sources; the DSKIO/`CALSLT`/`$4010` contracts are the disk arc's existing
citations (MSX2 Technical Handbook disk-ROM chapter; MSX Assembly Page BIOS call list),
unchanged. To record on landing: "repack: evict CALL FORMAT build/write engine to a
sub-ROM page-1 tenant (free ~Nxx B page-1 for error-handling S2b); console menu +
dispatch stay resident; lean byte-identical."
