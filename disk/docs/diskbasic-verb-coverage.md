<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Disk-BASIC verb coverage scoreboard + acceptance-gate scope

**What this is:** a living per-verb scoreboard of how much of the zerobas Disk-BASIC
verb surface is proven against the oracle — the Disk-BASIC counterpart of
[tier2-bdos-coverage.md](tier2-bdos-coverage.md). It exists to answer one question the
BDOS side already answers and the BASIC side does not: *which verbs are locked down by a
self-asserting oracle differential, and which can silently regress?*

**Why it was written (the asymmetry).** BDOS now has **three** coverage layers:

| Layer | BDOS | Disk-BASIC (before this doc) |
|-------|------|------------------------------|
| Per-function/verb **scoreboard** | ✅ [tier2-bdos-coverage.md](tier2-bdos-coverage.md) (8/8) | ❌ none |
| Emulator-free **host unit tests** | ✅ `make unit-test` | ✅ partial (`make unit-test`) |
| Standing **acceptance gate** vs oracle | ✅ `make bdos-acceptance` (11/11, re-asserted every change) | ❌ none — probes are ad-hoc, run by hand |

The individual ingredients on the Disk-BASIC side are real and substantial (see the
matrix): nearly every implemented verb *has* a self-asserting differential probe. What
is missing is the **consolidation** — a standing gate that re-runs them and a scoreboard
that records the result. Today `make probe` runs only a 3-probe smoke test; the ~18
Disk-BASIC differential probes are not gated by anything, so a verb can regress with no
red signal.

**Provenance / how this matrix was seeded.** ⚠️ The cells below are seeded from **static
analysis only** — reading our own `basic/*.asm` source for the verb surface, plus a
classifier over each probe (`grep` for oracle/reference references and for
assert/exit-on-mismatch patterns). No reference ROM was read or disassembled to build this
(clean-room discipline, [no-reference-rom-disasm](../../README.md)).

> **Superseded by a real run (2026-07-05).** The gate now exists
> (`make diskbasic-acceptance`, [diskbasic-acceptance-spec.md](diskbasic-acceptance-spec.md))
> and has been run, so the cells below are **gate-confirmed**, not static guesses — see §0.

---

## 0. Gate baseline — `make diskbasic-acceptance`

**2026-07-05: 23/23 verbs converged.** The ROM is clean.

The gate's *first* run reported 22/23 with SAVE/BSAVE red — but investigation proved that
red was a **flaky-probe false positive, not a ROM bug**:

- The `disk_probe_save.py` `BSAVE→BLOAD` sub-test typed its `bload` command via openMSX
  keyboard injection at emutime t≈26; on `C-BIOS_MSX1_BASIC_DISK` with a disk mounted,
  `type`'s **first keypress doubles** in a narrow (~t=26–27) window → `bbload"…"` → syntax
  error → **BLOAD never ran**, so the region kept the probe's wipe byte. That wipe byte was
  `0x00` (`BIN_SENTINEL`), so "BLOAD did nothing" masqueraded as "loaded zeros" and looked
  like a write bug.
- **Proof the ROM is innocent:** (1) an offline FAT12 dump of the BSAVE'd file showed the
  exact 17-byte pattern on disk — the write path is byte-perfect; (2) changing the sentinel
  to `0xA5` made the failing region read `a5a5…` (wipe kept), *not* `00` — BLOAD demonstrably
  never executed; (3) the same sequence typed at t=36 round-trips byte-identical.
- **Fix (probe, not ROM):** every typed command is now prefixed with a leading space (a
  doubled first key becomes a doubled space, eaten by `skip_spaces`), and `BIN_SENTINEL` is
  nonzero so a no-op BLOAD can never masquerade as zero data again. → SAVE/BSAVE green, 23/23.
- **Follow-up (in progress):** the type-injection harness is being replaced for the
  SAVE/BSAVE case by a **`.bas`-on-disk / boot-auto-run** test (no keyboard typing at all) —
  the robust methodology that removes this whole failure class. See
  [tier2-review-queue.md](tier2-review-queue.md).

Re-run after any kernel/BASIC/ROM change; a red gate means the surface regressed. Repro:
`make diskbasic-acceptance` (needs `make machines-oracle` + seed image + CF-3300 refs).

**Lesson:** neither the static ✅ guess nor the gate's raw red was trustworthy alone — the
*discriminating experiment* (nonzero sentinel + offline disk dump) is what found the truth.
A red gate means "investigate," not "the ROM is broken."

---

## 1. The verb surface (from `basic/*.asm`)

Disk-BASIC verbs, grouped, with their handler location. Tape verbs (CSAVE/CLOAD) are
**out of scope** — they belong to the cassette path, not the disk stack.

| Group | Verbs |
|-------|-------|
| Directory / file-management | `FILES`, `KILL`, `NAME`, `MAXFILES` |
| Program loaders | `SAVE`, `LOAD`, `RUN "file"`, `MERGE`, `BLOAD`, `BSAVE` |
| Sequential channel I/O | `OPEN`, `CLOSE`, `PRINT#`, `PRINT# USING`, `INPUT#`, `LINE INPUT#`, `INPUT$` |
| Random-access record I/O | `FIELD`, `LSET`, `RSET`, `GET #n`, `PUT #n`, `MKI$/MKS$/MKD$`, `CVI/CVS/CVD` |
| File-position functions | `EOF`, `LOF`, `DSKF` |
| Formatting | `CALL FORMAT` |
| **Not implemented (Phase-3 / N/A)** | `LOC`, `DSKI$`, `DSKO$` (direct sector access) — no token defined; excluded from coverage math |

---

## 2. Coverage matrix

Legend — **Impl**: verb exists in source. **Unit**: emulator-free host test in `tests/`.
**Probe**: differential/functional openMSX probe in `probes/disk/`. **Oracle style**:
`live` = differential vs a running CF-3300 / MSX-DOS-1 black box; `artifact` = compared to
a real stock FAT12 image read read-only per public spec
([readonly-artifact-oracle](../../README.md)); `structural` = self-checks the produced
bytes vs the FAT12 spec (no live black box); `smoke` = runs but does **not** assert.
**Gated**: in `make diskbasic-acceptance`. As of the 2026-07-05 baseline (§0) **every row
below is gated and converged — 23/23**; the per-row `❌` column below only marks the pre-gate
state and is superseded by §0.

### Directory / file-management

| Verb | Impl | Unit | Probe (self-asserting) | Oracle | Gated | Notes |
|------|:----:|:----:|------------------------|:------:|:-----:|-------|
| FILES | ✅ | — | `disk_probe_files` ✅ | live | ❌ | also older `diskbasic_probe_files` (smoke, superseded) |
| KILL | ✅ | — | `disk_probe_kill` ✅ | live | ❌ | |
| NAME | ✅ | `test_fren_collision` ✅ | `disk_probe_name` ✅ | live | ❌ | rename-collision path unit-locked (M35) |
| MAXFILES | ✅ | — | `disk_probe_maxfiles` ✅ | live | ❌ | |

### Program loaders

| Verb | Impl | Unit | Probe (self-asserting) | Oracle | Gated | Notes |
|------|:----:|:----:|------------------------|:------:|:-----:|-------|
| SAVE (tokenised) | ✅ | — | `disk_probe_save` ✅ | artifact | ✅ | `SAVE"A:"→RUN"A:"` round-trips |
| BSAVE (binary) | ✅ | — | `disk_probe_save` ✅ | artifact | ✅ | `BSAVE"A:"→BLOAD"A:"` (+`,R`) round-trips; ROM byte-perfect (the earlier red was a flaky-probe artifact — §0) |
| LOAD | ✅ | — | `disk_probe_load_disk` ✅, `disk_probe_load_embedded_nul` ✅ | artifact | ❌ | embedded-NUL regression covered |
| RUN "file" | ✅ | — | `disk_probe_run_disk` ✅ | artifact | ❌ | |
| MERGE | ✅ | — | `disk_probe_merge` ✅ | live | ❌ | |
| BLOAD | ✅ | — | `disk_probe_bload_disk` ✅, `disk_probe_bload_fcb` ✅ | artifact | ❌ | |

### Sequential channel I/O

| Verb | Impl | Unit | Probe (self-asserting) | Oracle | Gated | Notes |
|------|:----:|:----:|------------------------|:------:|:-----:|-------|
| OPEN | ✅ | — | `disk_probe_filewrite`/`fileread`/`append` ✅ | live | ❌ | exercised through the I/O probes |
| CLOSE | ✅ | — | *(incidental only)* | — | ❌ | ⚠️ **thin** — no dedicated self-asserting differential |
| PRINT# | ✅ | `test_print` (host, non-disk) | `disk_probe_filewrite` ✅, `disk_probe_append` ✅ | live | ❌ | |
| PRINT# USING | ✅ | `test_printusing` (host) | `disk_probe_printusing_file` ✅ | live | ❌ | |
| INPUT# | ✅ | — | `disk_probe_fileread` ✅ | live | ❌ | numeric INPUT# is Phase-3 (strings only today) |
| LINE INPUT# | ✅ | — | *(inside `fileread`/`inputdollar`, incidental)* | live | ❌ | ⚠️ **thin** — no dedicated assert of its own |
| INPUT$ | ✅ | — | `disk_probe_inputdollar` ✅ | live | ❌ | |

### Random-access record I/O

| Verb | Impl | Unit | Probe (self-asserting) | Oracle | Gated | Notes |
|------|:----:|:----:|------------------------|:------:|:-----:|-------|
| FIELD | ✅ | `test_field` ✅ | `disk_probe_field` ✅ | live | ❌ | |
| LSET / RSET | ✅ | `test_field` ✅ | `disk_probe_field`/`getput` ✅ | live | ❌ | |
| GET #n | ✅ | `test_rdblk_randrecord` ✅ | `disk_probe_getput` ✅, `disk_probe_rdblk_roundtrip` ✅ | live | ❌ | RDBLK path (M31) |
| PUT #n | ✅ | `test_wrblk_*` (×4) ✅, `test_wrrnd_extend` ✅ | `disk_probe_getput` ✅, `disk_probe_wrblk_roundtrip` ✅ | live | ❌ | WRBLK/WRRND paths (M28/M29/M36) |
| MKI$/MKS$/MKD$, CVI/CVS/CVD | ✅ | — | `disk_probe_mkicvi` ✅ | live | ❌ | |

### File-position functions

| Verb | Impl | Unit | Probe (self-asserting) | Oracle | Gated | Notes |
|------|:----:|:----:|------------------------|:------:|:-----:|-------|
| EOF | ✅ | — | `disk_probe_eof` ✅ | live | ❌ | |
| LOF | ✅ | — | `disk_probe_eof` ✅ | live | ❌ | covered by the EOF probe |
| DSKF | ✅ | — | `disk_probe_dskf` ✅ | live | ❌ | |

### Formatting

| Verb | Impl | Unit | Probe (self-asserting) | Oracle | Gated | Notes |
|------|:----:|:----:|------------------------|:------:|:-----:|-------|
| CALL FORMAT | ✅ | — | `disk_probe_format` ✅ | structural | ✅ | asserts formatted BPB/FAT bytes vs FAT12 spec (720K+360K); older `diskbasic_probe_format` (smoke, kept for provenance) |

---

## 3. Findings

**F1 — Coverage *depth* is good; the ROM is clean at 23/23.** Of ~24 implemented verbs, all
but two (CLOSE, LINE INPUT#) have a dedicated self-asserting probe, and all converge. The
gate's first run *looked* like it found a BSAVE bug, but the red was a **flaky-probe artifact**
(openMSX type-injection), not a ROM defect — investigated and proven innocent (§0). Real
lesson: a red gate is a signal to *investigate*, not proof the ROM regressed.

**F2 — The structural gap is now CLOSED.** `make diskbasic-acceptance` exists and gates the
self-asserting differentials (baseline §0). Before it, the ~18 probes were run by hand and
asserted nowhere ongoing (`make probe` runs only 3 smoke probes) — the exact exposure that
let the BSAVE bug sit unnoticed. This is the "same thing that was lacking," now supplied.

**F3 — No scoreboard existed.** This doc is the seed; it must become probe-run-maintained,
not hand-maintained (same rule as the BDOS scoreboard).

**F4 — Two thin cells.** `CLOSE` and `LINE INPUT#` are only exercised incidentally inside
other probes; neither has a dedicated assert. These are the two real coverage-depth gaps.

**F5 — Two oracle styles, both legitimate, must both be gate-able.** Directory/channel/
record verbs use **live** CF-3300 differentials; the program loaders (SAVE/LOAD/RUN/BLOAD)
use the **read-only FAT12 artifact** oracle. A consolidated gate must run both kinds.

**F6 — Non-asserting smoke probes: KEPT + annotated (revised from "retire").**
`diskbasic_probe_filechannel/files/format` predate the `disk_probe_*` differentials and
assert nothing. Sign-off said retire them, but they turned out to be **cited provenance
anchors** — the spikes that first recorded the file-channel contract, FILES format, and
CALL FORMAT dispatch, cited in [file-channel-protocol.md](file-channel-protocol.md) and
[basic/PROVENANCE.md](../../basic/PROVENANCE.md). Deleting them would break the provenance
trail (dual-mission). So each now carries a header banner marking it *provenance-capture,
NOT part of the acceptance gate* — kills the false-coverage risk without losing the citation.

**F7 — Out of scope (not gaps).** `LOC`, `DSKI$`, `DSKO$` are unimplemented (no token) —
Phase-3 direct-sector territory. Excluded from the coverage denominator.

---

## 4. Proposed acceptance gate (scope only — for sign-off, not yet built)

Mirror `make bdos-acceptance`:

- **`make diskbasic-acceptance`** → `probes/disk/diskbasic_acceptance.py`, a runner that
  replays the self-asserting Disk-BASIC probes (both live and artifact oracle styles) and
  re-asserts each converges, printing an `N/N` scoreboard. Oracle-dependent (needs
  `make machines-oracle` + CF-3300 reference ROMs), so — like the BDOS gate — it stays
  **out of** the emulator-free `make unit-test`.
- **Seed set:** the ✅-live and ✅-artifact probes in §2 (FILES, KILL, NAME, MAXFILES,
  MERGE, SAVE, LOAD, RUN, BLOAD, filewrite, fileread, append, printusing_file, inputdollar,
  field, getput, rdblk_roundtrip, wrblk_roundtrip, mkicvi, eof, dskf, format).
- **This doc becomes the scoreboard:** the runner's output updates the `Gated` column and a
  green-baseline line, exactly as `tier2-bdos-coverage.md` records its 11/11.

### Open decisions (need your call before building)

1. **Close F4 first, or gate-then-fill?** Add dedicated CLOSE + LINE INPUT# differentials
   before standing the gate up, or stand up the gate over what exists (F1) and backfill
   those two cells after? *(Recommend: gate first over the existing strong set, then backfill
   — gets the regression net up fastest.)*
2. **F6 cleanup in-scope?** Retire/upgrade the three smoke `diskbasic_probe_*` as part of
   this, or leave them and just mark them non-coverage here? *(Recommend: retire, to remove
   the false-coverage trap.)*
3. **Scope after Disk-BASIC:** do the same audit + gate for **plain BASIC** verbs next
   (the 21 `basic_probe_*` vs Philips VG-8020), as you flagged ("first the disk basic
   commands")?

---

## 5. Status

- **2026-07-05** — doc created; matrix seeded from static analysis.
- **2026-07-05** — **`AUTOEXEC.BAS` auto-run implemented** (stock-parity feature our disk ROM
  lacked; spec [autoexec-bas-spec.md](autoexec-bas-spec.md)). New `autoexec_run`
  (basic/cload.asm) hooked at cold start; gate gains an `AUTOEXEC` cell
  (`disk_probe_autoexec.py`, differential vs CF-3300 + negative + empty-file), verified green
  individually (full 24-cell sweep pending). This unblocks the `.bas`-on-disk harness (zero
  keyboard typing) that replaces the fragile `type`-injection probes.
- **2026-07-05** — **gate built + baselined (signed off).** `make diskbasic-acceptance`
  (`probes/disk/diskbasic_acceptance.py`) implemented. First run = 22/23; the one red cell
  (SAVE/BSAVE) was investigated and proven a **flaky-probe false positive** (openMSX
  type-injection), not a ROM bug — fixed in-probe → **23/23, ROM clean** (§0). Decisions:
  (1) gate-first ✅ done; (2) smoke probes **kept + annotated**, not retired (F6, provenance);
  (3) plain-BASIC audit = follow-on. Open work: **replace the type-injection SAVE/BSAVE probe
  with a `.bas`-on-disk / boot-auto-run test** (pilot in progress — the robust methodology);
  and the F4 backfill (dedicated CLOSE + LINE INPUT# differentials).
