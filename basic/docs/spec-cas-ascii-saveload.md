<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec (signed off): cassette ASCII program SAVE `,A` + ASCII CLOAD/LOAD

**Status: COMPLETE 2026-07-08. M0 (format pinned), M1 (ASCII LOAD), M2 (ASCII SAVE)
all DONE + gated (`probes/basic/basic_probe_cas_ascii.py` for load; the three
`M2 oracle:` cells of `probes/basic/basic_probe_tape_save.py` for save — format,
single-block round-trip, >256-byte multi-block round-trip). Both sides taught the
SAME real-time-tape lesson: signalling is real-time on read AND write, so a whole
256-byte block must be moved in one tight loop (buffer-then-flush on write; slurp-
then-serve on read), never interleaved byte-by-byte with tokenise/detokenise work
— see §4 (read) and §5 (write).** The cassette
counterpart to the disk ASCII arc
([`spec-ascii-saveload.md`](spec-ascii-saveload.md), IMPLEMENTED 2026-07-07), which
explicitly deferred cassette ASCII as "a tracked follow-on" (its §7 decision 1). This is
the "last open follow-on" named in the disk close-out and in the tape option-surface
audit ([`../../tape/docs/cas-device-option-surface.md`](../../tape/docs/cas-device-option-surface.md)
Tier 2). Model per [[opus-vs-sonnet-model-split]]: signed-off spec → Sonnet
implementation, with the §7 round-trip as the acceptance test.

**Sign-off (2026-07-08):** D1 — **pin the real block format from the MSX2 TH first**
(a no-code characterization milestone, M0), *then* choose interop-256B vs own-design
with facts in hand. **[M0 done → D1 RESOLVED: interop-faithful 256-byte blocks; see §0.1.]**
D2 — **getbyte indirection** (option A). D3 — **core + CLOAD autodetect** (`SAVE"CAS:",A`
+ `LOAD"CAS:"` + `CLOAD` autodetecting `$EA`); `MERGE"CAS:"` / `RUN"CAS:"` deferred. D4 —
LOAD then SAVE, each its own commit + gate. D5 — Sonnet implementation once M0 fixes the
format.

## 0. Milestone order (as signed off)

- **M0 — pin the format (no code). ✅ DONE 2026-07-08** (findings §0.1; D1 resolved).
- **M1 — ASCII CLOAD / LOAD"CAS:"** (§4) + gate. **✅ DONE 2026-07-08.** 3-way header
  dispatch in `do_tape_prog` + `cas_ascii_load`/`cal_getbyte`/`cal_refill` (256-byte
  `CAL_BUF` block buffer behind the `ARL_GETBYTE` getbyte indirection). Gate:
  `probes/basic/basic_probe_cas_ascii.py` (real `HARDBOIL.CAS` load oracle + >256-byte
  2-block synthetic + tokenised no-regression). See §4 for the three hard requirements
  the buffer design turns on (`CAL_BUF` below the stack's reach — the decisive bug, fixed
  by moving it from `$F100` to `$E600`; refill state in RAM across `TAPIN`; prompt block-1
  `TAPION`). *(next: M2)*
- **M2 — SAVE"CAS:name",A** (§5) + gate. **✅ DONE 2026-07-08.** `sav_is_cas` accepts
  `,A` → `cas_ascii_save`: `$EA` header block, then LIST's detokeniser (`list_walk`)
  piped through a new **PRDEV=3 tape sink** (`pchar`, print.asm) that BUFFERS bytes
  into `CAS_WBUF` and flushes a full 256-byte block via a tight `TAPOUT` loop
  (`cas_flush_block`), Ctrl-Z EOF + `$1A` pad on the final block. Gate: the three
  `M2 oracle:` cells of `basic_probe_tape_save.py`. See §5 for the real-time write-gap
  bug the buffer-then-flush design fixes (the write mirror of M1's §4 read lesson).

## 0.1 M0 findings — the pinned cassette ASCII format

**Sources (cross-validated, per [[validate-oracle-artifacts]]):**
1. **MSX2 Technical Handbook**, cassette chapter (Konamiman's public English translation,
   allowed source B — [`docs/allowed-sources.md`](../../docs/allowed-sources.md) line 109):
   <https://konamiman.github.io/MSX2-Technical-Handbook/md/Chapter5a.html>. States: ASCII
   files are marked by **`0EAH`×10** after the long header + a **6-byte** filename
   (vs `0D3H`×10 BASIC / `0D0H`×10 machine-code); the body is **256-byte blocks**, each
   preceded by a short header; **Ctrl-Z (`1AH`) is embedded in the data** as EOF.
2. **Read-only `.cas` data artifacts** (reading ASCII *data* bytes, not ROM code):
   three real ASCII tapes in `~/Documents/msx/msx/…` — `HOBBIT.CAS`, `timecurb.cas`,
   `HARDBOIL.CAS`. Each shows `$EA`×10 + 6-char name, then one 256-byte data block of
   line-numbered text (`"10 SCREEN 0:WIDTH 39…\r\n"`) with an embedded Ctrl-Z EOF.

**Pinned facts:**
- **Header block:** `$EA`×10 + 6-char space-padded name (add `ASCII_ID = $EA` to
  `sysvars.inc`). Long leader (new file).
- **Line format:** identical to our disk ASCII — `<lineno> <space> <detok body> CR LF`
  per line. `timecurb.cas` confirms **CR+LF** (`0D 0A`), matching what we already write.
- **Data blocks:** **fixed 256 bytes**, each with a **short** leader. EOF is the first
  **Ctrl-Z (`$1A`)** in the stream.
- **Final-block padding is producer-dependent and therefore READ-IRRELEVANT:** `HOBBIT`
  (256 B, spec-faithful) pads with `$1A`; `HARDBOIL`/`timecurb` (from converters, 264 B)
  pad with `$00`. → **On write, pad the last block with `$1A` to 256** (spec + HOBBIT).
  **On read, stop at the first `$1A` and ignore all padding** — this makes the reader
  robust to every producer's padding and sidesteps the ambiguity entirely.

**D1 RESOLVED → interop-faithful (256-byte blocks).** The format is unambiguous, the
incremental cost over a single block is small (a mod-256 counter that re-frames
`TAPOOF`/`TAPOON` on write and re-`TAPION`s on read — reusing the *exact* per-block
machinery `tape_save_basic`/`do_tape_prog` already have for the 2-block tokenised file),
and it keeps interop for all program sizes. **Bonus:** the three real tapes above become
ready-made read-only load oracles for the M1 gate. All local samples are single-block
(small programs); the multi-block (>256 B) path is spec-pinned and exercised by an M2→M1
round-trip of a >256-byte program.

## 1. The gap (what errors today)

The cassette side handles the **tokenised** program format only:

- `SAVE"CAS:name",A` is a documented `load_error` ([`../save.asm:352`](../save.asm)) —
  the `,A` clause is explicitly rejected on the tape branch (`sav_is_cas`).
- `CLOAD` / `LOAD"CAS:"` read only the tokenised format: `do_tape_prog`
  ([`../cload.asm:193`](../cload.asm)) requires header byte 0 == `BASIC_ID` (`$D3`) and
  `load_error`s anything else — an `$EA` ASCII file cannot be loaded from tape at all.
- There is **no** `MERGE"CAS:"` (MERGE is disk-only, [`../files.asm:1482`](../files.asm)).

The disk side already does all of this; only the cassette byte layer is missing.

## 2. The cassette ASCII format (clean-room basis)

The **payload** is byte-identical to the disk ASCII format we already write (that spec
§2): line-numbered text, `<lineno> <space> <detok body> CR LF` per line, terminated by
Ctrl-Z (`$1A`). The only cassette-specific parts are the **file-type id** and the
**block framing**:

- **Header block id = `$EA`** (ASCII), ×10, then the 6-char filename — vs `$D3` for
  tokenised (`BASIC_ID`) and `$D0` for binary (`BINARY_ID`). Already named in
  [`../../probes/lib/cas_encode.py:28`](../../probes/lib/cas_encode.py) ("ASCII
  (SAVE/LOAD) = 0xEA") and to be added to `sysvars.inc` as `ASCII_ID` next to the
  existing ids. Source: MSX2 Technical Handbook cassette chapter (same allowed source as
  `BASIC_ID`/`BINARY_ID`).
- **Block framing — PINNED in M0 (§0.1).** An ASCII cassette file is **fixed 256-byte
  data blocks**, each with its own short leader (vs the tokenised/binary format's single
  data block, and vs how our own `tape_save_basic` writes the whole image in one block).
  **Write:** chunk the listing into 256-byte tape blocks; the last block carries the
  EOF Ctrl-Z (`$1A`) and is padded to 256 with `$1A`. **Read:** stop at the first `$1A`,
  ignoring padding (robust across producers). Confirmed by the MSX2 TH cassette chapter
  and three real ASCII `.cas` tapes (§0.1).

No `$FF`/`$FE` disk marker is involved — those are the disk-file wrappers; cassette uses
the header-block id. Clean-room: public format + our own (de)tokeniser; no reference-ROM
read ([[no-reference-rom-disasm]]).

## 3. This is a bounded feature — most machinery already exists

| Need | Already exists | Reuse |
|---|---|---|
| detokenise program → ASCII text | `list_walk` + the `pchar`/`PRDEST`/`PRDEV` sink ([`../list.asm`](../list.asm), [`../print.asm:434`](../print.asm)) | SAVE adds a **new `PRDEV` = tape sink** — the LPT/CRT Tier-1 work already made `pchar` a device multiplexer |
| read ASCII text → tokenise + store | `ascii_read_lines` ([`../files.asm:1564`](../files.asm)) | LOAD reuses it — **but its byte source is hardcoded `fat_io_getbyte`** ([`../files.asm:1155`](../files.asm)); see D2 |
| clear current program on LOAD | `new_prog` | ASCII CLOAD/LOAD calls it (disk ASCII load already does) |
| cassette byte layer | `TAPOON`/`TAPOUT`/`TAPOOF`, `TAPION`/`TAPIN` (tape IPS) | the sink writes via `TAPOUT`; the source reads via `TAPIN` |
| header-block framing | `tape_save_basic` ($D3 header + data block), `do_tape_prog` (read + `$D3` gate) | SAVE mirrors it with `$EA`; LOAD adds an `$EA` branch at the byte-0 gate |
| detect ASCII vs tokenised on load | the byte-0 id read in `do_tape_prog` ([`../cload.asm:193`](../cload.asm)) | becomes a 3-way branch (`$D3`→tokenised, `$EA`→ASCII, else→error) |

## 4. Design — ASCII CLOAD / LOAD"CAS:" (Milestone 1)

**Detection.** In `do_tape_prog`, byte 0 of the header is already read for the `$D3`
check. Make it a branch: `$D3` → the existing tokenised path (unchanged); `$EA` → the
new `cas_ascii_load`; anything else → `load_error`. Both `CLOAD` and `LOAD"CAS:"` reach
`do_tape_prog`, so both transparently accept either format (D3).

**Body (`cas_ascii_load`).** Skip the remaining 15 header bytes (as today), `call
new_prog` (LOAD replaces), then drive `ascii_read_lines` with the tape as its byte source
(D2). `ascii_read_lines` stops at the first **Ctrl-Z (`$1A`)**, so trailing padding is
never read. `,R` handling is unchanged — the `LOAD"CAS:",R`/`RUN` caller already runs on
the flag (Tier-1 `parse_close_run`).

**The tape byte source MUST buffer a whole block — not read per byte (D2 refinement,
2026-07-08).** `TAPIN` is a *real-time* read: the (emulated) tape keeps moving whether or
not the CPU is polling, so any CPU-heavy work *between* two `TAPIN` calls desyncs the
next byte. `ascii_read_lines` does a full `dispatch_line`→`tokenise`→`store_line` between
byte reads, which is more than enough to desync — a 34-byte synthetic file corrupts after
line 1 (M1 first-cut, confirmed). This is *why the format is 256-byte blocks*: on real
hardware each block is slurped in one tight uniform-cost loop, tokenised during the
**inter-block leader gap**, then the next block is re-locked with `TAPION`. So the tape
getbyte serves bytes instantly from a **256-byte RAM block buffer**, refilled by a tight
`TAPIN`×256 loop (+`TAPION` re-lock) at each block boundary. This mirrors the disk path
exactly — `fat_io_getbyte` already serves from a 512-byte sector buffer, which is why disk
ASCII load never hit this. Tokenising happens only while draining the RAM buffer (no tape
I/O), so its cost is harmless.

**Three hard requirements the M1 implementation had to satisfy (each cost real iterations;
captured so M2's tape sink honours the write-side mirror):**
1. **`CAL_BUF` must sit BELOW the stack's reach — this was the decisive M1 bug.** The first
   placement, `$F100` (page-aligned, in the "free `$F00A..$F37F` span below the C-BIOS
   sysvars `~$F380`"), was NOT safe: the C-BIOS stack lives just under the sysvars and grows
   down, and the call-heavy `dispatch_line`/`tokenise` pass drove `SP` down into `$F1xx`,
   overwriting a correctly-filled block *before* `cal_getbyte` served it — a **single-block**
   file (HOBBIT) loaded as an EMPTY program. Fixed by relocating `CAL_BUF` to **`$E600`**,
   page-aligned inside the file data sector buffer `FSECTOR_BUF` (`$E5C0..$E7BF`): that
   buffer is used only by disk I/O and a cassette CLOAD/LOAD does none, so it is dead for the
   whole load — and `$E600` is far below any stack descent. Verified: HOBBIT + HARDBOIL +
   a 552 B multi-block synthetic + a clean re-encode of timecurb's text all load correctly
   after the move; all failed at `$F100`.
2. **The refill loop's state lives in RAM, NOT on the stack, across `TAPIN`.** `TAPIN`
   clobbers every register, so `cal_refill` keeps its fill position in a RAM cell
   (`CAL_CNT`) and recomputes the store address each byte — the "state in RAM across a BIOS
   tape call" discipline `ctp_body` already uses (it guards `CLPTR` in RAM).
3. **The block-1 `TAPION` must be prompt** (right after the header skip, before `new_prog`
   and the reader entry) — deferring it makes it miss the data-block leader and fail to
   relock. `cas_ascii_load` therefore primes block 1 itself; `cal_getbyte` `TAPION`s only
   blocks 2+ (the safe mid-tape re-lock the 256-byte format is built around).

**Chosen scratch homes (M1):** `ARL_GETBYTE` (getbyte vector, 2 B) and `CAL_NEEDFILL`
(refill flag, 1 B) sit in the free `$E0CE`/`$E0EB` page-3 gaps; `CAL_CNT` (block position,
1 B) reuses the `$E0EA` VRAM-flag gap (dead outside a cassette load); **`CAL_BUF` is a
dedicated page-aligned 256-byte buffer at `$E600`**, inside the idle `FSECTOR_BUF` span
(see requirement 1), page-aligned so the byte address is `$E6`/`CAL_CNT` with no add.

**Note on real-tape samples.** HOBBIT.CAS and HARDBOIL.CAS load correctly; `timecurb.cas`
does NOT — but its *content* loads fine when re-encoded as a spec-conformant `.cas`, so its
failure is an artifact quirk of that particular multi-file game tape (264-byte `$00`-padded
blocks), not a reader bug. The gate uses HARDBOIL (real) + a synthetic multi-block, not
timecurb.

## 5. Design — SAVE"CAS:name",A (Milestone 2) — IMPLEMENTED 2026-07-08

**Parse.** In `sav_is_cas` ([`../save.asm:339`](../save.asm)) the `,A` after the
`"CAS:"` name now → `cas_ascii_save` (any case); anything else still errors. Mirrors
`sav_ascii_flag` on the disk side.

**Frame + sink (`cas_ascii_save`).** Write the `$EA` header block (`TAPOON` long +
10× `$EA` + `tape_name_emit` + `TAPOOF`, a tight loop like `tape_save_basic`'s
`$D3` header), then set `PRDEST:=1`, `PRDEV:=3` (the new cassette sink), `call
list_walk`, append the EOF `$1A`, pad the final block to 256 with `$1A`, restore
`PRDEST:=0`/`PRDEV:=0`. Baud is whatever the active word selects (`CSAVE",speed` /
default 1200 via TAPOON's `cas_seed`); no new speed parsing.

**The tape sink MUST buffer a whole block — not TAPOUT per byte (bug found + fixed
2026-07-08; the WRITE mirror of the §4 read lesson).** The first cut had the
`PRDEV=3` `pchar` case `TAPOUT` each byte as `list_walk` produced it, re-framing every
256. It wrote a **byte-perfect** WAV (the decoder recovered `$EA`×10 + name +
`10 A=5\r\n20 B=7\r\n` + `$1A` pad exactly) — but the file **would not load back**: the
reader's `cal_refill` read only `"10 "` (3 bytes) before `TAPIN` returned CF. Cause:
cassette signalling is **real-time on WRITE too**. Between `TAPOUT`s, `list_walk` runs
`list_num` (line-number formatting) and `detok` (per-token dispatch), stamping
**non-uniform inter-byte gaps** into the recorded signal; `TAPIN` loses bit-sync at
the first oversized gap. The tokenised `tape_save_basic` path never hit this because
its data-block loop is *tight* (uniform gaps) and short. Fix = the **write mirror of
M1's block buffer**: `cas_wbyte` (the `PRDEV=3` case) just STORES each byte into
`CAS_WBUF` (no tape I/O), and when the 256th byte fills the block `cas_flush_block`
emits the WHOLE block — `TAPOON` short + a **tight `TAPOUT`×256 loop** (uniform gaps,
position in RAM `CAS_WCNT` across the register-clobbering `TAPOUT`) + `TAPOOF`. The EOF
`$1A` + `$1A` padding run through the same buffer, so the final block is flushed full.
Blocks are separated by arbitrary `list_walk` gaps (just longer leader), and the
reader re-`TAPION`s per block — the interop-faithful 256-byte framing (§0.1) makes
this exact split correct on both ends. `CAS_WBUF` overlays `CAL_BUF` at `$E600` (a SAVE
and a LOAD never coexist; both live in the idle `FSECTOR_BUF`, below any stack
descent — the same placement requirement M1 learned at §4 requirement 1).

**Two hard requirements (write side), mirroring M1's read side:**
1. **Move a whole block in ONE tight loop.** Non-uniform gaps between `TAPOUT`s desync
   the reader; the fill (byte-at-a-time from `list_walk`) touches NO tape, and the
   flush touches tape ONLY in the uniform tight loop. This is why the format is
   256-byte blocks: each block is written/read as one tight burst, blocks separated
   by leader gaps that re-lock with `TAPION`.
2. **The flush loop's position lives in RAM (`CAS_WCNT`), not a register**, because
   `TAPOUT` clobbers everything across the call — the same "state in RAM across a BIOS
   tape call" discipline `tape_save_basic` and (on read) `cal_refill` use.

## 6. Decisions (signed off 2026-07-08 — see the header for the résumé)

**D1 — Cassette ASCII block format.** **RESOLVED (M0) → A, interop-faithful 256-byte
blocks.** The MSX2 TH + three real ASCII tapes pinned the format unambiguously (§0.1):
`$EA`×10 header, 256-byte data blocks with short leaders, Ctrl-Z EOF, CR+LF lines. The
per-256 re-framing reuses our existing per-block `TAPOON`/`TAPOOF`/`TAPION` machinery,
the read side is padding-robust (stop at first `$1A`), and it keeps interop for all
program sizes — the three tapes double as M1 load oracles. Own-design single-block (the
rejected alternative B) would have been cheaper but lost real-MSX interop for >256-byte
programs.

**D2 — Reader byte-source abstraction.** **RESOLVED: A (getbyte indirection) + a
256-byte block buffer behind the *tape* getbyte (refined 2026-07-08, see §4).** The
indirection vector stands; the tape getbyte must NOT call `TAPIN` per byte (real-time
desync — §4), it serves from a 256-byte block buffer refilled by a tight `TAPIN` loop at
each block boundary. This is the interop-faithful design (matches real MSX + the disk
sector-buffer), keeps the buffer bounded to 256 B, and reverses nothing in D1/§0.1.
`ascii_read_lines` calls `fat_io_getbyte` directly today.
- **A. getbyte indirection:** route its reads through a one-cell RAM vector (the read-side
  mirror of `PRDEV`), default `fat_io_getbyte`, re-pointed to a `TAPIN` wrapper during a
  cassette ASCII load. Symmetric with the sink; no size limit. One small refactor of
  shared, working code (like the `list_emit`/`pchar` sink refactor was).
- **B. buffer-then-parse:** read the whole tape file into a RAM scratch buffer, then run
  `ascii_read_lines` over RAM. Avoids touching the reader, but needs a buffer sized to the
  program — awkward/limited for large programs.
- *Recommend:* A.

**D3 — Verb surface.** **RESOLVED: core + CLOAD autodetect.**
- `SAVE"CAS:name",A` (write ASCII) and `LOAD"CAS:name"` (autodetect `$EA`) — **core.**
- `CLOAD` autodetecting ASCII too (a mild, forgiving superset of real MSX, which restricts
  `CLOAD` to tokenised) — **yes**, since both share `do_tape_prog`.
- `MERGE"CAS:"` and `RUN"CAS:"` — **deferred** (tracked follow-ons; `MERGE"CAS:"` becomes
  cheap once D2's getbyte indirection lands, `RUN"CAS:"` needs `do_run` work).

**D4 — Milestone split.** **RESOLVED: yes** — LOAD (M1) then SAVE (M2), each its own
commit + gate cell, matching the disk arc. (M0 format-pin precedes both.)

**D5 — Implementation model.** **RESOLVED: Sonnet** per the split once M0 fixes the
format, driven by the §7 round-trip + codec differential as acceptance.

## 7. Verification (no reference-ROM read)

- **Round-trip self-check (primary):** `SAVE"CAS:F",A` to a `.cas`/WAV → `NEW` →
  `LOAD"CAS:F"` reproduces the program byte-for-byte (mirrors the disk `.bas` round-trip;
  uses the existing typed-tape harness on `C-BIOS_MSX1_EU_TAPE --cart`). Include a
  **>256-byte** program so the multi-block (re-`TAPION`) path is exercised.
- **Real-tape load oracle (M1):** load the three stock ASCII tapes pinned in §0.1
  (`HOBBIT.CAS`, `timecurb.cas`, `HARDBOIL.CAS`) and assert the tokenised image matches
  what tokenising their known text yields — a genuine third-party artifact oracle
  ([[readonly-artifact-oracle]]), not just self-round-trip.
- **Codec differential (pins the format):** extend `cas_encode.build_cas_ascii` /
  `cas_decode` for the `$EA` header + D1 block format; assert the WAV zerobas writes
  decodes to the expected `$EA`-framed ASCII stream, and that a codec-built ASCII `.cas`
  loads on zerobas. (Reading the *data* bytes of an ASCII `.cas` is not a ROM read.)
- **Host unit test:** the tape sink's block-framing byte counter (if D1=A) — emulator-free.
- **Gate:** a new cell in [`../../probes/basic/basic_probe_cas_options.py`](../../probes/basic/basic_probe_cas_options.py)
  (or a dedicated `basic_probe_cas_ascii.py`); update the tape option-surface audit Tier 2
  → done. No regression on `diskbasic-acceptance` (34) / `unit-test` (38).

## 8. Non-goals

- Numeric `INPUT#` — Phase-3 language (tracked disk-side).
- ~~tape *sequential channels* (`OPEN"CAS:" FOR INPUT|OUTPUT`)~~ — **now DONE
  (2026-07-08)**, built ON this spec's $EA/256-byte/Ctrl-Z byte layer: `oo_dev_cas`
  reuses `cas_write_ea_header`/`cas_ascii_finish`/`cas_wbyte` (OUTPUT) and
  `cas_ascii_setup`/`cal_getbyte` (INPUT, via a `cas_in_getbyte` Ctrl-Z→EOF wrapper).
  The MSX2 TH confirms a sequential data file is the same `$EA` ASCII cassette format.
  See [`../../tape/docs/cas-device-option-surface.md`](../../tape/docs/cas-device-option-surface.md)
  §2 + Tier-2. `MERGE"CAS:"`/`RUN"CAS:"` also done there.
- No change to the tokenised cassette SAVE/LOAD paths, the (de)tokeniser, the disk ASCII
  paths, or the tape signal layer (TAPOON/TAPOUT/TAPION/TAPIN).
- `CSAVE` stays tokenised-only (ASCII save is spelled `SAVE"CAS:",A`, matching MSX).
