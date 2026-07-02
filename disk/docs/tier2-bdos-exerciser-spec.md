<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 BDOS exerciser spec — `BDOSX.COM`, the FCB-cluster probe tool

**Status: PHASE 1 COMPLETE (2026-07-02).** The blocking Tier-2 gap ("run a named `.COM` other
than COMMAND.COM itself") is now fixed — see [tier2-m21-spec.md](tier2-m21-spec.md) M21a+M21b.
Typing `BDOSX` at `A>` now loads and runs the exerciser: all 11 of its BDOS calls
(FSIZE/FOPEN/RDSEQ×2/SETRND/RDBLK/WRBLK/FCLOSE) execute with return addresses byte-identical to
stock, and its 384-byte read-back data buffer + FCB/register-snapshot buffer are 0-byte-diff
against stock (`capture --at 0x01bc --mem 0x0400:0x180` / `--mem 0x0300:0x180`). Resume board:
[tier2-STATE.md](tier2-STATE.md).

## 1. Goal
A small MSX-DOS `.COM` program (`BDOSX.COM`) that calls a fixed, deterministic sequence of
FCB-cluster BDOS functions — `$23` FSIZE, `$0F` FOPEN, `$14` RDSEQ ×2, `$24` SETRND, `$27`
RDBLK, `$26` WRBLK, `$10` FCLOSE — against a small file it controls, records every call's
outward registers + delivered data into a fixed RAM buffer, then self-loops. Run unmodified
on **ours** and **stock** via the existing differential harness (`disk_probe_diff.py capture
--mem`), the buffer diffs in one shot: identical ⇒ that whole cluster is proven byte-for-byte;
a localized divergence ⇒ a new, precisely-scoped milestone (same shape as every M1x/M2x fix
so far), found in one dispatch instead of the current one-reframe-per-function grind.

**Why now:** [tier2-STATE.md](tier2-STATE.md) "Next action" flags the FCB cluster + console
tier as the next work, but **none of it is isolable by a COMMAND.COM builtin** (`DIR`/`TYPE`
exercise `$11/$12/$1B/$0F` at most) — this tool is the named prerequisite
([[bdos-exerciser-com-test]]).

## 2. Scope — Phase 1 only (this spec)
**In scope:** the FCB read/write/close cluster — `$23 $0F $14 $24 $27 $26 $10` — fully
deterministic, **no keyboard input needed** (one boot, one typed command, no further keys).

**Explicitly OUT of scope (Phase 2, future spec):** the console-input cluster (`$01` CONIN,
`$06` DIRIO, `$07` DIRIN, `$08` INNOE, `$0B` CONST, `$0C` CPMVER). Several of these **block**
waiting for a key, so exercising them needs timed `--keys` injection mid-program rather than
one pre-staged burst, a materially different mechanism. STATE.md's architectural expectation
is that these ride the already-proven CHGET/CHSNS primitives with **no page-1 disk-ROM code
at all** ($0C returns a kernel-internal constant), so they're lower-risk than the FCB cluster,
which *does* dispatch into page-1 canonical `$50xx` entries — the exact bug class (unwired
`$00`-pad ⇒ CALL-slide) M13/M15/M17/M18/M19/M20 all turned out to be. Phase 1 targets the
higher-risk cluster first; Phase 2 reuses this spec's buffer/diff mechanism once scoped.

## 3. Architecture — reuse everything, add the minimum
Per [tier2-STATE.md](tier2-STATE.md) tooling guardrail ("use the ONE harness, don't write a
58th probe"), this is a **generic reuse of two already-existing primitives** in
`disk_probe_diff.py`, plus one small, already-precedented disk-image helper:

1. **`BDOSX.COM`** (new, this spec) — the TPA program (§4). Assembled with `pasmo` (same
   toolchain as `disk.rom`/`basic.rom`).
2. **Disk injection** (new, ~30 lines) — a throwaway copy of `test.dsk` gets `BDOSX.COM` +
   `BDOSX.BIN` (the file it exercises) added via `fat12_add()`, the generic FAT12-file-injector
   **already written and proven** in `probes/disk/disk_probe_bdos.py` (`disk_probe_bdos.fat12_add`,
   reads geometry from the BPB, allocates a free cluster chain, writes a root-dir entry — no
   FAT12 code duplicated, just imported as a sibling module).
3. **Run + diff** (zero new code) — `disk_probe_diff.py capture --at <done> --mem
   <base>:<len> --keys '\rBDOSX\r' --keys-at 20 --machine both --diska <built disk>`. `capture`
   already supports an anchor address, a memory-range diff, and pre-staged keystrokes
   (the exact mechanism the M19/OI-3/M20 sessions used to accept the date prompt and, for
   SDATE, type a real date) — **no new mode is added to the harness.**

No disk.rom change. No Tier-2 kernel/veneer code is touched by this spec — it is a pure test
tool. `make unit-test` / `disk.rom` invariants are unaffected (nothing in the ROM build changes).

## 4. `BDOSX.COM` — the exerciser program
TPA `.COM` (`org $0100`), auto-typed as a command at the `A>` prompt (not AUTOEXEC.BAT — the
current test.dsk boots straight to `A>` per the M19/M20 repros, and typing a command name
reuses that exact proven flow rather than adding an AUTOEXEC.BAT variant disk).

### 4.1 Memory layout
| Region | Address | Size | Contents |
|---|---|---|---|
| Code | `$0100`–`$02FF` | ≤512 B (budget; actual size read from the `.sym` after assembly) | the call sequence below |
| `fcb` | `$0300` | 37 B | the single reused FCB (CP/M/MSX2-TH layout, [[msx-diskrom-shared-kernel]] / `disk/PROVENANCE.md` §FCB layout) |
| `regs` | `$0340` | 8 records × 8 B = 64 B | one record per BDOS call (§4.3) |
| `data` | `$0400` | 3 × 128 B = 384 B | raw DTA snapshots for the 3 calls that deliver a record (RDSEQ×2, RDBLK) |
| `done` | (end of code) | — | `jr done` self-loop; the `capture --at` anchor. Exact address taken from the assembled `.sym`, never hand-guessed (per the M15 §7.3 lesson: don't eyeball addresses in a cramped/hand-laid-out region). |

One contiguous `capture --mem $0300:0x0180` (=384) covers `fcb`+`regs`; a second
`--mem $0400:0x0180` (=384) covers `data` — **two capture invocations**, not one over-wide
range, to keep each Tcl memory-read loop small and each diff easy to eyeball. (If in practice
one combined range is just as fast, collapsing to one invocation is a fine implementation-time
simplification — not a spec-load-bearing choice.)

### 4.2 Test file — `BDOSX.BIN`
384 bytes (3 whole 128-byte records, no partial-record/EOF edge case — that fidelity question
is already characterised elsewhere ([[msxdos-oracle-disk]], `disk_probe_bdos.py` PART A); this
tool is about **dispatch/wiring**, not sub-record framing). Deterministic, position-varying
content so a misplaced byte is caught: `byte[i] = (i*5 + 7) & 0xFF`. Generated in Python
(mirrors `oracle2_bin()`'s existing pattern) and injected via `fat12_add`, never handwritten
into the repo as a binary blob.

### 4.3 Call sequence + `regs` record format
Each `regs` record is 8 bytes: `[func, A, B, C, D, E, H, L]` — the BDOS function number
followed by every register a BDOS call in this cluster can plausibly return through (per
map.grauw.nl's MSX-DOS 2 function spec, which documents this DOS-1-compatible FCB subset
verbatim — **published spec, not stock disassembly**; see §6). Stored with 7 explicit
`ld (regs+n*8+k), reg` stores immediately after each `call $0005` (no shared subroutine reusing
`HL` as both "record pointer" and "value to snapshot" — see §7 for why that shape was rejected).

| # | func | call | in (beyond DE=fcb) | contract (map.grauw.nl dos2_functioncalls.php) |
|---|------|------|---|---|
| 0 | `$23` | FSIZE | FCB freshly zeroed + drive=0 + name=`BDOSX   BIN`, **unopened** | `A=0` found (writes file record-count into the FCB's random field) / `A=$FF` not found |
| 1 | `$0F` | FOPEN | FCB freshly re-zeroed + name (fresh Open, not reusing FSIZE's now-mutated FCB) | `A=0` success / `A=$FF` not found |
| 2 | `$14` | RDSEQ #1 | SETDTA→`data+0` first | `A=0` success (delivers record 0) / `A=1` EOF |
| 3 | `$14` | RDSEQ #2 | SETDTA→`data+128` first | `A=0` success (delivers record 1) / `A=1` EOF |
| 4 | `$24` | SETRND | — (copies current record, now 2, into the FCB's random field) | no result documented; record is captured anyway for the diff |
| 5 | `$27` | RDBLK | SETDTA→`data+256` first; `HL=1` (1 record) | `A=0`/`A=1` error; `HL`=records actually read (delivers record 2, the file's last) |
| 6 | `$26` | WRBLK | `HL=1` (1 record, from `data+256`, at the now-advanced random position = record 3 — **extends the file by one record**; safe, the run's disk is an ephemeral tmp copy, never the committed `test.dsk`, same pattern every write-capable probe already uses) | `A=0`/`A=1` error |
| 7 | `$10` | FCLOSE | — | `A=0`/`A=$FF` fail |

`fillfcb` (zero 37 bytes, set drive=0, `ldir` the 11-byte 8.3 name from a fixed table) runs
before records 0 and 1 (fresh FCB for FSIZE, fresh FCB again for Open — sidesteps any ambiguity
about what FSIZE's unopened-FCB write left behind); the FCB is left alone and threaded through
records 2–7 as MSX-DOS's own FCB bookkeeping evolves it, matching normal FCB usage.

## 5. Acceptance criteria
- `pasmo -s probes/disk/bdosx.sym --bin probes/disk/bdosx.asm probes/disk/bdosx.com` succeeds
  (3-pass; verify code fits the `$0100`–`$02FF` budget from the `.sym`, per the M15 §7.3 lesson).
- The disk-builder script produces a working throwaway disk (`BDOSX.COM` + `BDOSX.BIN` present,
  root-dir entries valid) from a copy of `test.dsk`.
- `capture --at <done> --keys '\rBDOSX\r' --keys-at 20 --settle 40 --machine both --mem
  0x0300:0x180` and the same with `--mem 0x0400:0x180`: **alignment guard passes** (both sides
  reach `done`) — this alone proves the whole cluster runs to completion on ours without a
  hang/derail, independent of what the byte diff shows.
- Byte diff of `fcb`+`regs`: either **byte-identical** (cluster proven, close this spec, update
  `tier2-bdos-coverage.md` rows for `$0F/$10/$14/$23/$24/$26/$27` to ✅) or a **localized
  divergence** at one record — becomes the next milestone's starting evidence (same shape as
  M13/M17/M18/M19/M20: a `regs` mismatch pinpoints exactly which call and which register).
- Byte diff of `data`: the two RDSEQ + one RDBLK 128-byte snapshots identical ⇒ delivered bytes
  match `BDOSX.BIN`'s known content on both machines (same fidelity check `disk_probe_bdos.py`
  PART A already validated for the Tier-1 `bdos_entry`, now for the Tier-2 kernel-dispatch path).
- No `disk.rom` change; `make unit-test` unaffected (nothing in the ROM build changes — this
  spec adds a test tool, not a fix).

## 6. Clean-room note
`BDOSX.COM` is 100% our own code. Every BDOS function contract cited (§4.3) traces to
map.grauw.nl's published MSX-DOS 2 function specification (which documents this DOS-1-compatible
FCB subset verbatim, cross-referenceable against the MSX2 Technical Handbook's BDOS chapter and
CP/M 2.2's equivalent function numbers — the same class of source already used for every prior
Tier-2 milestone, e.g. GETALLOC/M20). The FCB layout is the published CP/M/MSX2-TH standard
already in `disk/PROVENANCE.md` §FCB layout. No stock ROM, MSXDOS.SYS, or COMMAND.COM bytes are
read, dumped, or decoded — only BDOS entry/exit registers and our own RAM (the buffers above),
the same allowed observation class as every `capture`/`callseq` use to date.

## 7. Design notes / rejected shapes
- **A shared `snap` subroutine taking `HL` = destination pointer** was considered and rejected:
  `HL` is also the *outward result register* for `$27` RDBLK (records actually read), so a
  subroutine using `HL` as an address would have to clobber the very value it's trying to save.
  Inline `ld (addr), reg` stores after each call (7 explicit stores × 8 call sites) cost a little
  code size but need no register gymnastics — the right tradeoff for a diagnostic tool that runs
  rarely, not shipped ROM code where net-zero size actually matters.
- **AUTOEXEC.BAT auto-run** (the Tier-1 `disk_probe_bdos.py` ORACLE.COM pattern) was considered
  and rejected in favor of typing the command name at `A>`: the current Tier-2 harness already
  boots `test.dsk` straight to a live `A>` and injects a typed command via `--keys` (proven by
  every M13–M20 repro); adding a second boot-disk variant with an AUTOEXEC.BAT would duplicate
  disk-image machinery the harness doesn't need.
- **One `--mem` range spanning `fcb`+`regs`+`data` in a single `capture` call** was considered;
  split into two calls instead (§4.1) purely to keep each Tcl read-loop and diff small and easy
  to eyeball. Not load-bearing — collapse to one call at implementation time if it's just as fast.

## 8. Open questions (do not block sign-off; resolve during/after implementation)
- Exact final layout addresses (`fcb`/`regs`/`data`) are provisional pending the assembled
  `.sym` — if code doesn't fit under `$0300`, shift `regs`/`data` up by the overrun, no
  spec-level impact.
- Whether MSX-DOS-1 actually zero-pads or errors on the WRBLK-triggered file extension (record
  3, past the original 3-record file) is *unknown and fine to be unknown* — Phase 1's job is
  proving ours and stock behave identically for this exact deterministic sequence, not asserting
  what "correct" MSX-DOS behavior is.
