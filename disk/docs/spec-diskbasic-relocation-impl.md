<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Implementation spec: relocate disk-BASIC verbs `basic.rom` → `disk.rom`

**Status: PHASE A DELIVERED — stopped at FILES (user, 2026-07-09).**
Commit `29210b6` built the STATEMENT-expansion dispatcher (the "one gap") and relocated
**FILES** to `disk.rom`. basic.rom went from byte-full ($7FFF) to ending at **$7F74**
(~139 B reclaimed). All gates green: diskbasic-acceptance 34/34 (FILES bare+wildcard converge
vs CF-3300), bdos-acceptance 12/12, bdos-cbios-selfcheck 11/11, unit-test 38/38; loader path
intact. **KILL + NAME deferred** — on contact they proved to be *write-path* ports
(BDOS-gate-adjacent) for only ~125 B combined relief: KILL(wild) needs a wildcard multi-delete
composed on the disk side (disk `fat_find` is exact-match + BDOS-veneer-entangled; `fdel_body`
is single-name), NAME needs a second shared name buffer + a dir read-modify-write. User chose
the best relief-per-risk stop at FILES. D4 (dead-symbol reclaim) is **N/A** — `name_cmp`/
`fat_delete` remain used by the loader + the in-basic KILL/NAME. The dispatcher (`ex_stmt_ext`
+ the disk `$4004` `statement_ext`) is now a reusable seam for any future relocation. See the
outcome note in §8. Original sign-off spec follows unchanged for the record.

---

**Original status: SPEC FOR SIGN-OFF (2026-07-09).**
Input: [spec-diskbasic-relocation.md](spec-diskbasic-relocation.md) (direction decided by
user). Project rule: spec + sign-off before any code (memory `spec-before-implementation`).

This spec's first job (per the input's mandate) was to **find the real seam and measure the
byte relief.** It did — and the measurement **materially changes the premise.** §1–§4 present
the finding and options with hard numbers; §5 recommends; §6 details the recommended design;
§7 the verification; §8 the decisions that need your sign-off. **§4 is an escalation point.**

---

## 1. Executive finding (measured, not estimated)

The input framed the central problem as a **`fat.asm` coupling** (files.asm ~15 + field.asm
~13 calls into the FAT engine). That is real — but it is **the smaller of two coupling
axes.** The dominant one, unflagged in the input, is coupling to the **interpreter core**:

| Coupling axis | Call sites (files.asm + field.asm) | Can the target move to `disk.rom`? |
|---|---|---|
| → `basic/fat.asm` FAT engine | **28** (measured) | Engine is self-contained, but **pinned** to `basic.rom` for loader interop |
| → **interpreter core** (`eval`, `str_eval`, `var_*`, `skip_spaces`, `is_letter`, `upcase`, `exec_stmt`, `stmt_error`, `load_error`, `parse_disk_fcb`) + the **CAS: tape path** | **163** (measured) | **No** — it *is* the interpreter; cannot move, cannot cheaply duplicate |

**Why the second axis is the wall.** `basic.rom` (slot 0) and `disk.rom` (slot 3‑1) both
occupy page 1 (`$4000–$7FFF`) and are **never mapped simultaneously** — to run code in
`disk.rom` you page slot 3‑1 into page 1, which pages `basic.rom` *out*. So any verb body
moved to `disk.rom` loses plain-`CALL` reach to **both** the FAT engine **and** the
interpreter core. Every one of those 163 + 28 call sites would become a cross-slot `CALLSLT`
with register/slot juggling — and the verbs interleave parse (`basic.rom`) with I/O
(`disk.rom`) *within a single statement*, so the slot would thrash back and forth mid-verb.

**Consequence:** a wholesale "move `files.asm` + `field.asm`, dispatch via STATEMENT
expansion" is **not viable** as scoped. The ~3 KB payload the decision hoped to free is
**interpreter-woven**, not disk-management-leaf. Only a **462 B** subset (`FILES`/`KILL`/
`NAME`) is cleanly separable. Details and options below.

---

## 2. Measured inventory (current build)

### 2.1 `basic.rom` — byte-exactly full ($4000–$7FFF, ends $7FFF, zero fill)

Module sizes from the assembled symbol table (`pasmo` sym; boundaries are consecutive
first-labels in `main.asm` include order):

| Module | Range | Size |
|---|---|---|
| `basic/fat.asm` (FAT12 engine) | `$5877–$60C0` | **2121 B** |
| `basic/bload.asm` (loader read) | `$60C0–$630C` | 588 B |
| `basic/cload.asm` (cassette load) | `$630C–$6744` | 1080 B |
| `basic/save.asm` (loader write) | `$6744–$6B70` | 1068 B |
| **`basic/files.asm`** (FILES + channel) | `$6B70–$72D2` | **1890 B** |
| **`basic/field.asm`** (random record) | `$72D2–$7769` | **1175 B** |
| `basic/format.asm` (CALL FORMAT) | `$7769–$78E2` | 377 B |

`files.asm` + `field.asm` = **3065 B** (the theoretical ceiling of relief). But see §2.3.

### 2.2 `disk.rom` — 42 % full, 8440 B internal ≥64 B gaps (measured by scanning `$00` runs)

| Gap ORG | Size | | Gap ORG | Size |
|---|---|---|---|---|
| `$681D` | **3464 B** | | `$50E3` | 708 B |
| `$5602` | **2531 B** | | `$75A8` | 528 B |
| `$5FE8` | 147 B | | `$4EE1` | 215 B |
| smaller (`$4465`,`$48B2`,`$4E4E`,`$4FBB`,`$53AA`,`$77BB`,`$7F55`) | ~800 B total | | | |

Plenty of room; placement is not the constraint. **Confirm gaps on a fresh build before
pinning ORGs** — they shift with any `disk/*.asm` edit.

### 2.3 Verb payload split (within `files.asm` / `field.asm`, by assembled address)

| Sub-payload | Bytes | Coupling character |
|---|---|---|
| **`FILES`** (`do_files`+helpers, `$6B70–$6C5D`) | 237 | **thin parse** (`parse_disk_fcb`) + `fat_mount`/`read_sector`/`name_cmp` + **CHPUT output** |
| **`KILL`** (`$7133–$7163`) | 48 | thin parse + `fat_delete` |
| **`NAME`** (`$7163–$7214`) | 177 | thin parse + `fat_find`/`read_sector`/dir write |
| `OPEN`/`CLOSE`/`INPUT#`/`LINE INPUT#`/channel-mgr (`$6C5D–$7133`) | 1238 | **interpreter+CAS-woven**, per-byte `fat_io_*` |
| `MERGE` (`$7214–$72D2`) | 190 | interpreter+CAS-woven |
| **all of `field.asm`** (`FIELD`/`GET`/`PUT`/`LSET`/`RSET`) | 1175 | interpreter-woven (`eval`, `str_eval`, `var_*`), `fat_alloc`/`dir`/`fat` |
| **Cleanly separable (FILES+KILL+NAME)** | **462** | 5 heavy interpreter/CAS calls total in this span |
| **Interpreter/CAS-woven (channel + record)** | **2603** | saturated with `eval`/`str_eval`/`var_*`/`exec_stmt`/CAS |

### 2.4 The two FAT engines already in the tree (decisive for reuse)

`disk/fat.asm` (1380 lines) is a **parallel FAT12 engine** to `basic/fat.asm` — it defines
the *same* primitive names: `fat_mount`, `fat_find`, `fat_alloc_cluster`, `fat_dir_create`,
`fat_dir_update`, `fat_read_fat_sector`, `fat_write_fat_entry`, `read_sector`, `write_sector`,
`name_cmp`, `toupper`, plus the `fac_*`/`ffds_*`/`fnc_*`/`frs_*` helpers. The project **already
accepts FAT duplication** (loader-side DSKIO engine vs BDOS-side FDC engine). What
`disk/fat.asm` does **not** expose is the **per-byte sequential channel** (`basic/fat.asm`'s
`fat_io_open`/`getbyte`/`create`/`putbyte`/`close`/`append`) — it has record-framed
`bdos_seqwrite` (128 B) + `fat_read_file_sector` instead. So `disk/fat.asm` already covers
**everything FILES/KILL/NAME/FIELD need** except a per-byte stream.

RAM co-existence is already engineered: `basic/fat.asm` uses `FSECTOR_BUF $E5C0`/`FWBUF
$E7C0`/`FAT_* $E9C0+`; `disk/fat.asm` uses `SECTOR_BUF $E2A0`/`WBUF $E560+`. They overlap
partially but never run concurrently ([sysvars.inc:610](../../basic/sysvars.inc:610)).

### 2.5 The dispatcher gap and the cross-slot idiom that already exists

- `basic/interp.asm` dispatches statements from a **linear `cp TOKEN / jp z,handler` chain**
  ([interp.asm:719](../../basic/interp.asm:719)); an unknown statement falls to `stmt_error`
  ([interp.asm:921](../../basic/interp.asm:921)). There is **no** slot-walk / STATEMENT
  dispatcher (the "one gap", [msx1-basic-bios-coupling.md](../../basic/docs/msx1-basic-bios-coupling.md)).
- `disk/init.asm` lays `"AB"` + **STATEMENT vector = 0** at `$4004`
  ([init.asm:18](../init.asm:18)); the provider side is unimplemented.
- The cross-slot mechanism is **already proven**: `basic/fat.asm:dskio_calslt` does
  `CALSLT ($001C)` into `disk.rom`'s `$4010` using the **`DISKSLOT`** slot id captured by the
  INIT scan. The same `DISKSLOT` + `CALSLT` reaches a `$4004` STATEMENT handler directly — for
  the single built-in disk we do **not** need a full slot-walk (a slot-walk is the
  faithful-but-heavier general form; see §8-D3).

---

## 3. Seam options — evaluated against the measurement

The input listed four options. Verdicts with measured relief:

**Option 1 — split `fat.asm` into loader-FAT vs channel-FAT. ✗ Does not split.**
The loader and the moved verbs **share** the core (`fat_mount`, `fat_find`, the `fat_io_*`
byte engine, `write_sector` — measured intersection). `LOAD"A:"` reads program bytes through
the *same* `fat_io_open`/`getbyte` stream that `OPEN#`/`INPUT#` use. There is no loader-only
vs channel-only partition to cut; the attempt collapses into "duplicate the core," i.e.
Option 2/A.

**Option 2 — reuse `disk/fat.asm`. ✓ Feasible for the separable subset; no third engine.**
`disk/fat.asm` already provides the mount/find/dir/FAT primitives FILES/KILL/NAME/FIELD need
(§2.4). Binding the *separable* verbs to it adds **no** duplication. Gap: no per-byte channel
(needed by OPEN#/INPUT#/PRINT#) — would have to be composed from `fat_read_file_sector` +
local byte buffering. Risk: `disk/fat.asm` is oracle-locked to `bdos-acceptance` /
`bdos-cbios-selfcheck`; BASIC-side callers must not perturb persisted state (low risk — RAM is
re-init'd every boot; verified by re-running the gates).

**Option 3 — minimal move (FILES/KILL/NAME). ✓ The only clean move. Relief = 462 B gross.**
Confirmed cleanly separable (§2.3): thin parse (`parse_disk_fcb`), FAT/dir work available in
`disk/fat.asm`, output via **CHPUT (BIOS, always mapped)**. Net relief after retaining
per-verb parse stubs in `basic.rom`: **~250–350 B** (est.).

**Option 4 — move-all (incl. `fat.asm`), drop interop. ✗ Reverses the decision — escalate.**
Additionally does not solve the *interpreter* coupling; still not clean.

**The unlisted reality — the channel/record verbs (2603 B, the bulk):** relocating them needs
a **cross-slot interpreter-services ABI** (stable `$4004`-reachable entry points for `eval`,
`str_eval`, `var` get/set, `skip_spaces`, error dispatch, and the PRINT-item loop), because
each verb calls these dozens of times mid-statement. Building that ABI is a **sizeable
sub-project** (re-entrancy: the verb calls back while the executor is mid-line; register/param
conventions; a trampoline). It is buildable but it is **not** "move two files + a dispatcher."

---

## 4. ⚠️ Escalation: the premise shifted

The decision's cost/benefit assumed **~3 KB freed** by moving management verbs, blocked only by
`fat.asm` coupling. Measurement shows:

- **Clean relief available now: ~250–350 B** (FILES/KILL/NAME), not ~3 KB.
- The ~3 KB is **interpreter-woven** (163 sites) and needs a cross-slot interpreter-services
  ABI to relocate — a project comparable in size to the rest of this work.
- `fat.asm` itself (2121 B, the cleanly-relocatable engine) is **pinned** to `basic.rom` for
  the latent foreign-disk-ROM interop, so it yields no relief under the decision.

This does not *reverse* the direction, but it right-sizes it. Three ways forward (§8-D1):

1. **Phase A only** — take the clean ~300 B, build the STATEMENT dispatcher, stop. Modest
   relief, low risk, proves the mechanism. Good "unblock the next small `basic/*.asm` add."
2. **Phase A now, Phase B later** — do A; when bigger relief is needed, invest in the
   interpreter-services ABI and relocate the channel/record verbs (~2.6 KB more).
3. **Reconsider the lever** — for feature-complete headroom, the **C-BIOS repack** path
   (`docs/cbios-repack-space-analysis.md`, Approach 0 ~5.3 KB / Approach 1 ~7 KB) frees far
   more for arguably less architectural risk and ships as an IPS exactly like today. It is
   orthogonal to this work and currently deferred only on tooling/priority.

**Recommendation: 2 (Phase A now, Phase B gated).** Phase A is genuinely clean, delivers the
dispatcher "one gap," and is faithful (a real MSX keeps FILES/KILL/NAME in the disk ROM).
Phase B is specced in shape (§6.4) but **not** authorized by this spec — it needs its own
go/no-go once the ABI is designed.

---

## 5. Recommended design — Phase A (FILES / KILL / NAME → `disk.rom`)

Move the three directory-management verbs to `disk.rom`, dispatched via STATEMENT expansion,
executing against `disk/fat.asm`, output via BIOS `CHPUT`. **One `CALSLT` per verb
invocation, zero interpreter callbacks** (args pre-parsed in `basic.rom`; output via
always-mapped BIOS).

### 5.1 The parse/execute split (the seam)

```
 basic.rom (slot 0, page 1)                      disk.rom (slot 3-1, page 1)
 ─────────────────────────────                   ────────────────────────────────
 interp.asm dispatch chain
   cp FILES_TOKEN → ex_stmt_ext(FN_FILES) ─┐
   cp KILL_TOKEN  → ex_stmt_ext(FN_KILL)  ─┤
   cp NAME_TOKEN  → ex_stmt_ext(FN_NAME)  ─┘
                                            │
 ex_stmt_ext(fn):                           │  STATEMENT handler @ $4004:
   parse args with LOCAL interpreter  ......│    reads REQ_FN + the RAM param block
     (parse_disk_fcb → DISK_FCB_NAME,       │    dispatches FN_FILES/KILL/NAME
      second name for NAME, wildcard)       │    executes via disk/fat.asm primitives
   stage into a RAM param block             │    output via CHPUT ($00A2, BIOS)
   ld a,(DISKSLOT); CALSLT $4004  ──────────┼──▶ returns A = status (0 ok / err code)
   on return: map status → error/continue   │
   jp exec_stmt                             │
```

- **Parse stays in `basic.rom`** — `parse_disk_fcb`, the `var_str_type` string check,
  `upcase`, `skip_spaces` all run in-slot with plain `CALL` (no ABI change).
- **The param block is RAM** (page 3, always mapped) so both slots read it with no marshalling:
  reuse `DISK_FCB_NAME` ($E0DB) for the primary 8.3 name; add a second 11-byte name cell for
  `NAME`'s target and a 1-byte `REQ_FN` selector. All in existing `$E0xx` scratch.
- **Execution is in `disk.rom`**, calling `disk/fat.asm` locally; output through `CHPUT`
  (BIOS page 0, mapped from any slot). **No call reaches back into `basic.rom`.**
- **Return contract:** `A = 0` success, else an error selector; `basic.rom` maps it to the
  existing `stmt_error` / disk-error path. `CALSLT` preserves nothing but `A`/flags per its
  contract — the front-end holds no live registers across the call.

### 5.2 What executes in `disk.rom` per verb (all primitives already exist in `disk/fat.asm`)

- **FILES** — `fat_mount`; scan root-dir sectors via `read_sector`; `name_cmp` against the
  wildcard pattern; emit each 8.3 name via `CHPUT` with the existing column/​wrap formatting
  (ported from `df_emit`, which is already CHPUT-based). `print_crlf` is replaced by two
  `CHPUT` (CR, LF) to stay BIOS-only.
- **KILL** — `fat_mount`; `fat_find`; free the cluster chain via `fat_write_fat_entry` and
  erase the dir entry (compose the small `fat_delete` equivalent from `disk/fat.asm`
  primitives — `disk/fat.asm` has the FAT-write + dir access but no packaged `fat_delete`).
- **NAME** — `fat_mount`; `fat_find` (old); rewrite the dir entry's name field
  (`read_sector` + in-place name overwrite + `write_sector`), using the existing dir-update
  path.

### 5.3 The STATEMENT-expansion dispatcher (the "one gap")

- **Consumer (`basic/interp.asm`):** replace the three `jp z,ex_files/ex_kill/ex_name` targets
  with a shared `ex_stmt_ext` shim that (a) records which function, (b) parses, (c) `CALSLT`s
  `disk.rom`'s `$4004`. **Keep the token recognition in `basic.rom`** — the tokeniser already
  assigns FILES/KILL/NAME tokens; we are moving *bodies*, not tokenisation. (A general
  unknown-statement slot-walk is out of scope for Phase A — see §8-D3.)
- **Provider (`disk/init.asm`):** set the header word at `$4004` to a real `statement`
  handler; the handler reads `REQ_FN` and branches to the three verb bodies placed in a disk
  gap. Guard the header value change with the existing header assembly.
- **Direct-CALSLT vs slot-walk:** Phase A uses `DISKSLOT` + `CALSLT $4004` directly (single
  built-in disk; matches how `dskio_calslt` already reaches `$4010`). This is not the fully
  general MSX slot-walk, but it is correct for the release target (patched C-BIOS + our
  `disk.rom` in slot 3‑1) and reuses proven capture. Note the limitation in the header comment.

### 5.4 Placement, build, IPS wiring

- Place the three verb bodies + FILES formatter at a `disk.rom` gap ORG (e.g. `$681D`, 3464 B —
  ample) with a `ds gap_end - $, $00` fill-guard, exactly like the tape patch. **Re-measure
  gaps on a fresh build first** (§2.2 caveat).
- **`disk.rom` change** → rebuild `disk.rom` + `make machines` (reinstall the machine config;
  probes read the installed `disk.rom` in slot 3‑1).
- **`basic.rom` change** (the dispatcher shim + removing the three bodies) → rebuild
  `zerobas-msx1.ips` + reinstall — **machine probes run the installed IPS, not
  `build/basic.rom`** (memory `ips-rebuild-after-basic-change`); `--cart` probes read
  `build/basic.rom`. Both rebuilds are needed for this change.

### 5.5 Net byte accounting (Phase A)

- `basic.rom` **frees** the FILES (237) + KILL (48) + NAME (177) bodies = **462 B**, **minus**
  the retained `ex_stmt_ext` shim + per-verb parse front-ends (est. **~120–200 B**) →
  **net ~260–340 B reclaimed** in `basic.rom`.
- `basic/fat.asm` **stays** (loader interop) — `fat_delete`/`name_cmp` remain used by nothing
  in `basic.rom` after the move; **remove them from `basic/fat.asm`** for extra relief if they
  become dead (check: `name_cmp`/`fat_delete` callers are only the moved verbs → likely
  reclaimable, adding to net relief; verify with a dead-symbol pass post-move).
- `disk.rom` **grows** ~500–700 B (verb bodies + FILES formatter + `statement` dispatcher),
  well within the `$681D` gap.

---

## 6. Phase B (channel + record verbs) — specced in shape only, NOT authorized

For the record, so the phasing is explicit. **Do not implement without a separate go/no-go.**

- **Prerequisite:** a **cross-slot interpreter-services ABI** — stable `$4004`-region entry
  points (or a dedicated secondary vector) exposing `eval`, `str_eval`, `var` get/set,
  `skip_spaces`, error dispatch, and a way to drive the PRINT-item loop, all re-entrant while
  the executor is mid-line. Register/param conventions + a trampoline. This is the real cost.
- **Then** split each channel/record verb parse/execute like Phase A, but the parse↔execute
  boundary is crossed *multiple times per statement* (e.g. `PRINT#` evaluates each item then
  writes it), so the ABI's per-call overhead and correctness dominate.
- **CAS: coupling:** the channel verbs also serve `CAS:` (tape) — that path stays in
  `basic.rom` regardless; the disk-channel and cas-channel would have to be cleanly separated
  first, itself non-trivial.
- **Relief:** up to ~2.6 KB (channel 1428 + record 1175) minus retained parse front-ends.
- **Verdict:** worthwhile only if feature-complete headroom is needed *and* the C-BIOS repack
  (§4.3) is rejected. Escalate before starting.

---

## 7. Verification — standing gates + end-to-end

Gates that must stay green (run all after any shared-parse edit — a cursor-clobber regression
once surfaced only in the full suite):

- `make diskbasic-acceptance` **34/34**
- `make bdos-acceptance` **12/12** (guards `disk/fat.asm` reuse)
- `make bdos-cbios-selfcheck` **10/10**
- `make unit-test` **38/38**

End-to-end (Phase A):

- **Moved verbs** — `FILES` (bare + wildcard pattern), `KILL`, `NAME` via the
  `diskbasic_probe_*` harness on the `C-BIOS_MSX1_*_BASIC_DISK` machine (patched C-BIOS +
  `disk.rom` in slot 3‑1). Confirm the STATEMENT `CALSLT` round-trips and errors map correctly.
- **Loader path unchanged** — `LOAD"A:"`/`BLOAD`/`SAVE`/`BSAVE`/`RUN"A:"` still work (proves
  the `fat.asm`-in-`basic.rom` interop is untouched).
- **Channel/record verbs unchanged** — `OPEN#`/`PRINT#`/`INPUT#`/`FIELD`/`GET`/`PUT` still
  work (they did not move in Phase A).
- **Gotchas:** rebuild+reinstall **both** `disk.rom` (machine) and `zerobas-msx1.ips` (BASIC
  patch) before probing; test-disk mutation → `/tmp` copies + `git status`/restore.

Clean-room: all new code original; STATEMENT-expansion protocol from
[expansion-protocol.md](expansion-protocol.md) + MSX2 TH (no disassembly). **C-BIOS untouched**
(the page-0 repack is the separate deferred option). No reference-ROM disassembly.

---

## 8. Decisions — SIGNED OFF (user, 2026-07-09)

- **D1 — Scope. → Phase A now, Phase B gated.** Implement FILES/KILL/NAME relocation + the
  STATEMENT dispatcher now; the channel/record verbs (~2.6 KB, need the interpreter-services
  ABI) are deferred behind a separate go/no-go (§4/§6.4).
- **D2 — FAT engine. → Reuse `disk/fat.asm`.** No third engine; bind the moved verbs to the
  existing disk-side FAT12 primitives (§2.4). Verification cost accepted: re-run
  `bdos-acceptance` + `bdos-cbios-selfcheck` to confirm no perturbation.
- **D3 — dispatcher generality. → Direct `DISKSLOT`+`CALSLT $4004`** (recommended default;
  matches `dskio_calslt`). Document the "single built-in disk / not a general slot-walk"
  limitation in the header comment.
- **D4 — reclaim `fat_delete`/`name_cmp`** from `basic/fat.asm` if dead post-move
  (recommended default; do a dead-symbol pass after the move for extra relief).

On sign-off, implement one committed step at a time behind the standing gates:
(1) STATEMENT dispatcher (consumer shim + provider `$4004` handler, no verbs yet — prove the
round-trip with a stub); (2) FILES; (3) KILL; (4) NAME; (5) dead-symbol reclaim + final gate
sweep.

## 9. Outcome (2026-07-09)

Implemented as commit `29210b6`, merging spec-steps 1+2 (the FILES gate cell is the natural
round-trip proof, and basic.rom being byte-full made the shim + FILES removal atomic anyway):

- **disk/init.asm** `$4004` STATEMENT vector → `statement_ext`.
- **disk/kernel.asm** `statement_ext` (dispatch on `A` = `STMT_*`) + `db_files` (the do_files
  walk/emit, rebound to `SECTOR_BUF` / local `read_sector` / **`name_cmp_wild`** for `?`
  patterns / BIOS `CHPUT`; loop counters `DB_HASPAT`/`DB_ENTIDX` in page-3 RAM — a
  `$4000–$7FFF` disk-ROM store silently no-ops). Placed in the `$681D` corridor; the
  `ds $75A5 - $` pad absorbs it (canonical addresses net-zero).
- **basic/interp.asm** `ex_stmt_ext` — RDSLT the `$4004` vector via `DISKSLOT`, `CALSLT` it,
  text cursor preserved on the stack across the call (CALSLT clobbers HL).
- **basic/files.asm** `ex_files` reduced to the arg-parse front-end; `do_files` body removed.
- Shared codes `STMT_FILES/KILL/NAME` mirrored in `basic/sysvars.inc` + `disk/equates.inc`.

**One bug found + fixed in verification:** first pass bound `db_files` to disk `name_cmp`
(exact-match only) → wildcard `FILES"*.bas"` returned empty. Switched to the disk kernel's
existing `name_cmp_wild` (`?`-aware) → 34/34.

**Deferred (KILL/NAME) — reopen criteria:** revisit if (a) more basic.rom relief is genuinely
needed for a new `basic/*.asm` addition, or (b) Phase B (the channel/record verbs) is
authorized — at which point the write-path `disk/fat.asm` binding gets built + re-verified
once for all of them. The `ex_stmt_ext`/`statement_ext` seam is ready to carry them.
