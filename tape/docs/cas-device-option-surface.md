<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# CAS: & non-disk-device option-surface audit

**What this is.** The tape/device counterpart of the disk-side
[diskbasic-option-surface.md](../../disk/docs/diskbasic-option-surface.md): a standing
sweep of every BASIC statement form that names the **cassette device (`CAS:`)** or another
**non-disk character device** (`LPT:` printer, `CRT:` screen, `GRP:` graphics, `COM:`
serial), against its documented option/parameter surface. It answers the question the
disk audit deliberately routed *out* of its own axis (disk audit §2 "Tape verbs sharing a
disk parser", Tier-2 "OPEN device-name channels"): *for each cassette / device form we
accept, do we handle every documented option, or did we implement the bare form and
silently drop the variants?*

**Why it exists.** The disk sweep closed the disk verbs' option gaps (VRAM `,S`, `OPEN
LEN=`, `FILES`/`KILL` wildcards, `CLOSE` list, WRSEQ write-back) and, in doing so,
enumerated a cluster of **CAS: and device-channel** misses it then punted to "the tape
stack owns them" / "the plain-BASIC axis". This doc is where those land: it is the
same per-*option* lens applied to the cassette and device surface, so a green *verb*
(`SAVE` ✅, `LOAD` ✅, `OPEN` ✅) can no longer hide a red *device option*
(`SAVE"CAS:",A`, `LOAD"CAS:",R`, `OPEN"LPT:"`).

**Genre.** Scoreboard / notebook (the coverage matrix + gap tiers). The behavioural
contract for the cassette signal layer itself is [spec-cassette.md](spec-cassette.md); the
closure specs for the gaps found here will be a companion `spec-cas-device-closure.md`
(written for sign-off *before* any code, per
[spec-before-implementation](../../README.md)).

**Clean-room basis.** The "documented options" column is the *published user-syntax* of
MSX BASIC (MSX2 Technical Handbook; MSX-BASIC reference) — user-facing grammar, not ROM
code. The "implemented" column is read from our own `basic/*.asm` (the statement parsers)
and `tape/tape.asm` (the device layer). No reference/stock ROM was read or disassembled
([no-reference-rom-disasm](../../README.md)).

---

## 0. Method & scope

- **Reference (the "should"):** the published optional-argument grammar of each verb *in
  its device form*.
- **Implemented (the "is"):** the argument parsers in `basic/*.asm`, read statically
  (2026-07-08 sweep), plus the device dispatch sites (`dev_cas` compare in
  [bload.asm](../../basic/bload.asm)/[cload.asm](../../basic/cload.asm)/[save.asm](../../basic/save.asm)).
- **In scope:** every BASIC statement form that carries a device name — the `CAS:`
  cassette forms and the `LPT:`/`CRT:`/`GRP:`/`COM:` character-device channels — plus the
  page-0 BIOS device entry points the tape component's scope admits
  ([DESIGN.md](../DESIGN.md) "Scope": `AUXIN`/`AUXOUT`).
- **Boundary with the loader-stub charter.** BASIC today is **game-loader-scoped**
  ([TODO.md](../../TODO.md)). Some device options below need language machinery outside
  that charter (numeric `INPUT#`, a graphics engine for `GRP:`, serial hardware for
  `COM:`). Those are recorded and flagged *out-of-charter*, not queued for closure — the
  closable set is the CAS: statement options and the two cheap BIOS-backed channels
  (`LPT:`, `CRT:`).

---

## 1. CAS: statement-option matrix

Legend — **✅** fully handled · **◐** partial · **✗** absent · **⚠** absent *and fails
silently* (wrong/ignored behaviour, not a clean error). "Ref" = the documented option.
Evidence is `file:line` in `basic/`.

| Verb (CAS: form) | Documented option surface | Status | Evidence / note |
|---|---|:--:|---|
| `BLOAD"CAS:name"` | `[,R]` | ✅ | `,R` load-and-run parsed via `parse_close_run` ([bload.asm](../../basic/bload.asm) `is_tape`); `,S` VRAM-from-tape cleanly rejected |
| `BSAVE"CAS:name"` | `,start,end[,exec]` | ✅ | full binary header+data block ([save.asm:147](../../basic/save.asm:147) `bsv_is_cas`); `,S` VRAM-to-tape rejected (disk-only) |
| `CLOAD` | `["name"]` / `CLOAD?["name"]` | ◐ | bare + quoted-name load ✅; **name is parsed-past and ignored** (opens the next tape file regardless, [cload.asm:48](../../basic/cload.asm:48)); **`CLOAD?` verify form ✗** |
| `CSAVE` | `["name"][,speed]` | ◐ | name ✅ (6-char, space-pad); **`,speed` (1=1200 / 2=2400) not parsed** — jumps straight to `tape_save_basic` ([save.asm](../../basic/save.asm) `do_csave`); baud instead comes from `SCREEN,,,baud` |
| `LOAD"CAS:name"` | `[,R]` | ◐ | loads a tokenised program ✅; **`,R` parsed-past and ignored** — `dl_is_cas` skips to the closing quote and jumps to `do_tape_prog`, never checks `,R` ([cload.asm:87](../../basic/cload.asm:87)). Asymmetric with `BLOAD"CAS:",R` which *does* honour it |
| `SAVE"CAS:name"` | `[,A]` | ✅ | tokenised save ✅; **`,A` ASCII save ✅** (`cas_ascii_save`, [save.asm](../../basic/save.asm)) — `$EA` header + 256-byte blocks, buffer-then-flush tape sink (M2, 2026-07-08) |
| `RUN"CAS:name"` | `[,R]` | ✅ | `do_run` now has a `CAS:` branch (dev_cmp, [cload.asm](../../basic/cload.asm) `do_run`) → `do_tape_prog` (tokenised OR $EA ASCII) → `run_prog` (2026-07-08) |
| `MERGE"CAS:name"` | (ASCII) | ✅ | `ex_merge` `CAS:` branch → `merge_cas` ([files.asm](../../basic/files.asm)): $EA reader (cas_ascii_setup/drive) into the current program, NO new_prog (2026-07-08) |
| `OPEN"CAS:name" FOR INPUT\|OUTPUT AS #n` | sequential tape channel | ✅ | `do_open` `CAS:` dispatch → `oo_dev_cas` ([files.asm](../../basic/files.asm)): OUTPUT writes the $EA header + `PRINT#` buffers via `cas_wbyte`, CLOSE flushes; INPUT primes block 1 + `INPUT#`/`LINE INPUT#` read via `cas_in_getbyte` (Ctrl-Z EOF). No fat.asm ctx (like LPT/CRT) — not interleavable with a disk file channel (shared $E600 buffer) (2026-07-08) |

**Cross-cutting theme.** The two `◐` "parsed-past and ignored" rows (`LOAD"CAS:",R`,
`CSAVE",speed"`, `CLOAD "name"`) are the same **silent-drop** class the disk audit's
Tier-1 "silent-parse hygiene" finding named: an option a user can type that produces
wrong/ignored behaviour instead of either working or a clean `Syntax error`. Honest-at-
the-walls says each should either function or reject cleanly.

---

## 2. Non-CAS device channels (`OPEN "dev:"`)

The disk audit's Tier-2 "OPEN device-name channels" gap. There is **no device-dispatch
site at `do_open` at all** — the string after the opening quote goes straight to
`parse_disk_fcb`, so any `LPT:`/`CRT:`/`GRP:`/`COM:` name is treated as a (usually
invalid, colon-bearing) disk filename.

| Device | Statement forms | Status | Backing available? | Disposition |
|---|---|:--:|---|---|
| `LPT:` | `OPEN"LPT:" FOR OUTPUT AS #n` → `PRINT#` to printer | ✗ | **yes** — `LPTOUT` (`$00A5`) is implemented in this component ([cbios-lptout-followup](../../tape/tape.asm)); `LPRINT`/BDOS `$05` already print | **closable** (cheap: route the channel sink to LPTOUT) |
| `CRT:` | `OPEN"CRT:" FOR OUTPUT AS #n` → `PRINT#` to screen | ✗ | **yes** — `CHPUT` (`$00A2`) | **closable** (cheap: route the channel sink to CHPUT/the print sink) |
| `GRP:` | `OPEN"GRP:"` → graphics text | ✗ | no — needs the graphics/`DRAW` engine | **out-of-charter** (Phase 3 graphics) |
| `COM:` | `OPEN"COM:"` → RS-232 | ✗ | no — no serial hardware modelled, no oracle | **out-of-scope** (no hardware target) |

---

## 3. Page-0 BIOS device completions (the tape component's own scope)

[DESIGN.md](../DESIGN.md) "Scope" admits page-0 BIOS device entry points C-BIOS stubs and
names `AUXIN`/`AUXOUT` (`$00A3`/`$00A6`) as "the obvious future candidates". These back a
general auxiliary (`COM:`-class) device. With no serial hardware modelled and no oracle
for the signal, they are **deferred, not closable** — admit them only if a concrete
`COM:`/AUX need with a real target appears. Recorded here so the scope note has a home.

---

## 4. Findings, tiered

**Tier 1 — ✅ CLOSED 2026-07-08** (spec + gates:
[spec-cas-device-closure.md](spec-cas-device-closure.md)).

- **CAS: silent-parse hygiene + `,R` handoff.** ✅ `LOAD"CAS:",R` now loads-and-runs (via
  `parse_close_run` + `run_prog`, as `BLOAD"CAS:",R` did); `CSAVE"n",speed` is honoured
  (1200/2400 baud) and a stray/malformed flag is a clean `Syntax error`. Note discovered
  in build: the speed digit is a tokenised *integer* (not ASCII) so it is `eval`-ed; and
  the cassette baud reference tables read zero (the C-BIOS + tape-patch stack has no BIOS
  cold-init seed, no cold-init hook, no `SCREEN,,,baud`). Resolved by seeding CS120/CS240
  (the oracle-sourced 1200/2400 words) in **`TAPOON`'s `cas_seed`** — a seed-if-zero, the
  same job a real MSX main-BIOS cold-init does — so the whole write stack has valid
  reference tables regardless of caller; `csav_speed` then only sets the active word.
  Gate: [basic_probe_cas_options.py](../../probes/basic/basic_probe_cas_options.py) (its
  `,2 → 2400` case is direct evidence `cas_seed` fired: with BASIC no longer seeding,
  the active 2400-word can only match a `cas_seed`-populated CS240).
- **`LPT:` and `CRT:` OPEN channels.** ✅ New `do_open` device-prefix dispatch
  (`dev_lpt`/`dev_crt` via `dev_cmp`), device channels marked in `FCH_MODES`
  (`LPT_MODE`/`CRT_MODE`) with no fat.asm context, a `PRDEV` sink selector in `pchar`
  (→ `LPTOUT`/`CHPUT`), and `CLOSE` skips the flush/`fch_select` for device channels.
  Printer output physically verified via the openMSX logger. Gate:
  [disk_probe_open_device.py](../../probes/disk/disk_probe_open_device.py) (`OPEN(LPT/CRT)`
  in `make diskbasic-acceptance`); no-regression on disk channels: 33/33 unchanged.

**Tier 2 — real, in-charter, larger.**

- **Tape sequential channels `OPEN"CAS:" FOR INPUT|OUTPUT` + `PRINT#`/`INPUT#`/`LINE
  INPUT#`.** Real cassette *file* I/O via channels (not just whole-program CLOAD/CSAVE).
  Needs the device-dispatch from Tier 1 plus a tape-backed channel sink/source over
  `TAPOON`/`TAPOUT` / `TAPION`/`TAPIN`. Note `INPUT#` numeric is already a tracked Phase-3
  language gap, so a first cut is string/`LINE INPUT#` only.
- **CAS: ASCII program save/load** — `SAVE"CAS:",A`, ASCII `CLOAD`, `MERGE"CAS:"`,
  `RUN"CAS:"`. The tape analogue of the disk ASCII-save arc (the "last open follow-on" the
  disk close-out already named). Reuses the disk ASCII detokeniser/reader (`ascii_read_lines`,
  the `pchar`/`PRDEST` sink) over the tape byte layer instead of the disk one. **Spec
  (signed off):** [spec-cas-ascii-saveload.md](../../basic/docs/spec-cas-ascii-saveload.md)
  — format pinned (D1 → interop-faithful 256-byte blocks, `$EA` header, Ctrl-Z EOF, CR+LF;
  §0.1).
  - ✅ **M1 — ASCII `CLOAD` / `LOAD"CAS:"`** (2026-07-08). The byte-0 header check in
    `do_tape_prog` is now a 3-way dispatch (`$D3`→tokenised, `$EA`→`cas_ascii_load`,
    else→`load_error`); `cas_ascii_load` drives the shared `ascii_read_lines` reader
    through a getbyte RAM vector (`ARL_GETBYTE`, default `fat_io_getbyte`) pointed at a
    tape byte source that serves from a 256-byte `CAL_BUF` block buffer (`cal_getbyte`/
    `cal_refill`), refilled by a tight `TAPIN*256` loop at each block boundary — so
    tokenising never happens between two `TAPIN`s (which would desync the real-time read).
    Gate: [basic_probe_cas_ascii.py](../../probes/basic/basic_probe_cas_ascii.py) — real
    5-line tape oracle (`HARDBOIL.CAS`), a >256-byte 2-block synthetic, and a tokenised
    no-regression case.
  - ✅ **M2 — ASCII `SAVE"CAS:name",A`** (2026-07-08). `sav_is_cas` accepts `,A` →
    `cas_ascii_save`: `$EA` header block, then LIST's detokeniser (`list_walk`) piped
    through a new **`PRDEV=3` cassette sink** in `pchar` that BUFFERS bytes into
    `CAS_WBUF` and flushes each full 256-byte block via a tight `TAPOUT` loop
    (`cas_flush_block`) — the WRITE mirror of M1's block buffer. This was necessary, not
    cosmetic: a first cut that `TAPOUT`-ed each byte as `list_walk` produced it wrote a
    byte-perfect WAV that **would not load back** (the detok work between `TAPOUT`s
    stamped non-uniform inter-byte gaps that desync the real-time read — `TAPIN` failed
    after 3 bytes). EOF `$1A` + `$1A`-pad the final block. Gate: the three `M2 oracle:`
    cells of [basic_probe_tape_save.py](../../probes/basic/basic_probe_tape_save.py)
    (format, single-block round-trip, injected >256-byte multi-block round-trip).
  - ✅ **`RUN"CAS:"` + `MERGE"CAS:"`** (2026-07-08). `do_run` gains a `CAS:` branch →
    `do_tape_prog` → `run_prog` (loads tokenised OR $EA, then runs); `ex_merge` gains a
    `CAS:` branch → `merge_cas`, reusing the M1 reader (cas_ascii_setup/drive) WITHOUT
    `new_prog` so lines merge into the current program. Refactored `cas_ascii_load` into
    `cas_ascii_setup`+`cas_ascii_drive` to share. Gate:
    [basic_probe_cas_verbs.py](../../probes/basic/basic_probe_cas_verbs.py).
  - ✅ **`OPEN"CAS:name" FOR OUTPUT|INPUT AS #n`** (2026-07-08). Cassette SEQUENTIAL data
    channels (§2 below). `do_open` `CAS:` dispatch → `oo_dev_cas`; new FCH_MODES values
    `CAS_OUT_MODE`/`CAS_IN_MODE` (device channels like LPT/CRT — no fat.asm ctx). OUTPUT
    writes the $EA header at OPEN, `PRINT#` routes through the `PRDEV=3` sink
    (`cas_wbyte`), CLOSE flushes (`cas_ascii_finish` + `TAPIOF`). INPUT primes block 1
    and `INPUT#`/`LINE INPUT#` read via `cas_in_getbyte` (Ctrl-Z = EOF), routed through
    the `ARL_GETBYTE` vector `read_into_strscr` now uses. Format = the SAME $EA / 256-byte
    / Ctrl-Z ASCII file as SAVE",A" (MSX2 TH cassette chapter, cross-checked by WebFetch
    2026-07-08). A cassette channel must not be interleaved with a disk file channel
    (shared $E600 buffer); EOF()/LOF() on a cassette channel are unsupported (no file
    length). Gate: the OPEN cells of
    [basic_probe_cas_verbs.py](../../probes/basic/basic_probe_cas_verbs.py).
  - ⏳ still open: `CLOAD?` verify, `CLOAD"name"` matching (Tier-3 below).

**Tier 3 — quality-of-life.**

- ✅ **No-name `CSAVE,speed`** (2026-07-08). `CSAVE,2` (no filename, just a speed) now
  honours the baud like `CSAVE"n",2` — a comma route in `do_csave` into `csav_noname`,
  which fills the 6-space name and then runs `csav_speed`. Gate: Item 3 of
  [basic_probe_cas_options.py](../../probes/basic/basic_probe_cas_options.py)
  (`CSAVE,2` → 2400-baud regime).
- ⏳ `CLOAD?` verify form and `CLOAD "name"` actually matching the named file. These are
  **not** the quick wins they first look like: our tape model deliberately loads the
  *next* file and accepts-and-discards the name (own-design, no tape catalogue — see
  [cload.asm](../../basic/cload.asm) header). Real name-matching needs the reader to
  expose each header's 6-char name + a skip-non-matching-block loop + a multi-file tape
  fixture; verify needs a compare-mode read path. Closer to Tier-2 effort.

**Out-of-charter / out-of-scope (recorded, not queued):** `GRP:` (graphics engine, Phase
3); `COM:` + `AUXIN`/`AUXOUT` (no serial hardware/oracle); numeric `INPUT#` (Phase-3
language, already tracked disk-side).

---

## 5. Disposition

Per [spec-before-implementation](../../README.md): the gaps above are captured here (the
sweep) and will be specced for sign-off in a companion closure spec **before** any code.
Recommended closure order: **Tier 1** (CAS: `,R`/hygiene + `LPT:`/`CRT:` channels) →
**Tier 2** (tape sequential channels, then CAS: ASCII) → **Tier 3**.

Each closed option must land a gate cell so it can no longer silently regress — the same
lesson the disk `diskbasic-acceptance` gate and the ASCII-save arc taught. The tape stack
already has a regression harness ([tape-regression.md](tape-regression.md), `make -C tape
test`) to extend; the BASIC-visible device forms want a `diskbasic-acceptance`-style
BASIC-driven cell (or a new `tape-basic-acceptance`).

## Provenance

Sweep performed 2026-07-08 by static read of `basic/*.asm` (statement parsers) and
`tape/tape.asm` (device layer), cross-checked against published MSX-BASIC user-syntax. No
reference ROM read. Companion documents: [spec-cassette.md](spec-cassette.md) (the seven
entry-point contracts), [tape-regression.md](tape-regression.md) (the read/write gate),
[diskbasic-option-surface.md](../../disk/docs/diskbasic-option-surface.md) (the disk-side
audit this parallels).
