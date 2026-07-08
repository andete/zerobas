<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec (signed off): cassette ASCII program SAVE `,A` + ASCII CLOAD/LOAD

**Status: SIGNED OFF 2026-07-08 — no code written yet; M0 (format-pin) is the next
action.** The cassette counterpart to the disk ASCII arc
([`spec-ascii-saveload.md`](spec-ascii-saveload.md), IMPLEMENTED 2026-07-07), which
explicitly deferred cassette ASCII as "a tracked follow-on" (its §7 decision 1). This is
the "last open follow-on" named in the disk close-out and in the tape option-surface
audit ([`../../tape/docs/cas-device-option-surface.md`](../../tape/docs/cas-device-option-surface.md)
Tier 2). Model per [[opus-vs-sonnet-model-split]]: signed-off spec → Sonnet
implementation, with the §7 round-trip as the acceptance test.

**Sign-off (2026-07-08):** D1 — **pin the real block format from the MSX2 TH first**
(a no-code characterization milestone, M0), *then* choose interop-256B vs own-design
with facts in hand. D2 — **getbyte indirection** (option A). D3 — **core + CLOAD
autodetect** (`SAVE"CAS:",A` + `LOAD"CAS:"` + `CLOAD` autodetecting `$EA`); `MERGE"CAS:"`
/ `RUN"CAS:"` deferred. D4 — LOAD then SAVE, each its own commit + gate. D5 — Sonnet
implementation once M0 fixes the format.

## 0. Milestone order (as signed off)

- **M0 — pin the format (no code).** Characterize the cassette ASCII block layout
  (block size, final-block padding, Ctrl-Z EOF, length- vs terminator-driven read) from
  the MSX2 Technical Handbook cassette chapter + a read-only ASCII `.cas` data artifact
  if available ([[readonly-artifact-oracle]] — reading ASCII *data* bytes is not a ROM
  read). Output: resolve D1 (interop-256B vs own-design) with the pinned facts folded
  back into §2/§5, before any implementation.
- **M1 — ASCII CLOAD / LOAD"CAS:"** (§4) + gate.
- **M2 — SAVE"CAS:name",A** (§5) + gate.

## 1. The gap (what errors today)

The cassette side handles the **tokenised** program format only:

- `SAVE"CAS:name",A` is a documented `load_error` ([`../save.asm:352`](../save.asm)) —
  the `,A` clause is explicitly rejected on the tape branch (`sav_is_cas`).
- `CLOAD` / `LOAD"CAS:"` read only the tokenised format: `do_tape_prog`
  ([`../cload.asm:193`](../cload.asm)) requires header byte 0 == `BASIC_ID` (`$D3`) and
  `load_error`s anything else — an `$EA` ASCII file cannot be loaded from tape at all.
- There is **no** `MERGE"CAS:"` (MERGE is disk-only, [`../files.asm:1116`](../files.asm)).

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
- **Block framing — the one genuinely open format question (D1 below).** On a real MSX
  an ASCII cassette file is written as **multiple fixed 256-byte data blocks** (each its
  own leader + tape block), unlike the tokenised/binary format which is a *single* data
  block — and unlike how our own `tape_save_basic` writes the whole program image in one
  block. The exact block size, the padding of the final partial block, and whether the
  reader is length-driven or Ctrl-Z-driven must be **pinned from the MSX2 TH cassette
  chapter (not posited)** before implementation, exactly as the disk spec pinned CR-vs-CRLF
  by oracle. See D1.

No `$FF`/`$FE` disk marker is involved — those are the disk-file wrappers; cassette uses
the header-block id. Clean-room: public format + our own (de)tokeniser; no reference-ROM
read ([[no-reference-rom-disasm]]).

## 3. This is a bounded feature — most machinery already exists

| Need | Already exists | Reuse |
|---|---|---|
| detokenise program → ASCII text | `list_walk` + the `pchar`/`PRDEST`/`PRDEV` sink ([`../list.asm`](../list.asm), [`../print.asm:249`](../print.asm)) | SAVE adds a **new `PRDEV` = tape sink** — the LPT/CRT Tier-1 work already made `pchar` a device multiplexer |
| read ASCII text → tokenise + store | `ascii_read_lines` ([`../files.asm:1150`](../files.asm)) | LOAD reuses it — **but its byte source is hardcoded `fat_io_getbyte`** ([`../files.asm:1155`](../files.asm)); see D2 |
| clear current program on LOAD | `new_prog` | ASCII CLOAD/LOAD calls it (disk ASCII load already does) |
| cassette byte layer | `TAPOON`/`TAPOUT`/`TAPOOF`, `TAPION`/`TAPIN` (tape IPS) | the sink writes via `TAPOUT`; the source reads via `TAPIN` |
| header-block framing | `tape_save_basic` ($D3 header + data block), `do_tape_prog` (read + `$D3` gate) | SAVE mirrors it with `$EA`; LOAD adds an `$EA` branch at the byte-0 gate |
| detect ASCII vs tokenised on load | the byte-0 id read in `do_tape_prog` ([`../cload.asm:193`](../cload.asm)) | becomes a 3-way branch (`$D3`→tokenised, `$EA`→ASCII, else→error) |

## 4. Design — ASCII CLOAD / LOAD"CAS:" (Milestone 1)

**Detection.** In `do_tape_prog`, byte 0 of the header is already read for the `$D3`
check. Make it a branch: `$D3` → the existing tokenised path (unchanged); `$EA` → the
new `cas_ascii_load`; anything else → `load_error`. Both `CLOAD` and `LOAD"CAS:"` reach
`do_tape_prog`, so both transparently accept either format (D3).

**Body (`cas_ascii_load`).** Skip the remaining 15 header bytes (as today), `TAPION`
onto the data block(s), `call new_prog` (LOAD replaces), then drive `ascii_read_lines`
with the tape as its byte source (D2). Stop at Ctrl-Z / block exhaustion per D1. `,R`
handling is unchanged — the `LOAD"CAS:",R`/`RUN` caller already runs on the flag
(Tier-1 `parse_close_run`).

## 5. Design — SAVE"CAS:name",A (Milestone 2)

**Parse.** In `sav_is_cas` ([`../save.asm:339`](../save.asm)), the `,A` after the
`"CAS:"` name currently → `load_error`; make it accept `,A` (any case) → `cas_ascii_save`,
anything else still errors. Mirrors `sav_ascii_flag` on the disk side.

**Frame + sink (`cas_ascii_save`).** Write the `$EA` header block (`TAPOON` long + 10×
`$EA` + `tape_name_emit` + `TAPOOF`), then walk the program with LIST's detokeniser
feeding a **tape sink**: set `PRDEST:=1`, `PRDEV:=<tape>` (a new value), `TAPOON`
short (open first data block), `call list_walk`, append `$1A`, close the block(s)
(`TAPOOF`), restore `PRDEST:=0`. The new `pchar` sink case (`PRDEV=<tape>`) writes each
byte via `TAPOUT` and, **if D1 = 256-byte blocks**, counts bytes and re-frames
(`TAPOOF`/`TAPOON`) every 256. Baud is whatever the active word selects (`SCREEN,,,baud`
/ default 1200 via the TAPOON `cas_seed`); no new speed parsing.

## 6. Decisions (signed off 2026-07-08 — see the header for the résumé)

**D1 — Cassette ASCII block format.** *The decision that gates everything else.*
**RESOLVED: pin the real format first (M0), then choose A vs B with facts in hand.**
- **A. Interop-faithful (256-byte blocks):** matches a real MSX, so a stock machine can
  load our tape and we can load a stock ASCII tape — in keeping with the project's
  oracle-round-trip dual mission and our already-interop tokenised format. Cost: pin the
  exact block/padding rules from the MSX2 TH; per-256-byte re-`TAPOON`/`TAPION` framing
  (the mid-tape re-lock our 2-block reader already handles); extend `cas_encode`/`cas_decode`
  for multi-block ASCII.
- **B. Own-design single block (until Ctrl-Z):** one data block, reader stops at `$1A`,
  mirroring how `tape_save_basic` already writes one block and `do_tape_prog` stops at the
  program's own terminator. Far cheaper; self-round-trips; **loses guaranteed real-MSX
  ASCII interop.** Must be documented as an own-design deviation (like "load the next
  file" in `cload.asm`).
- *Recommend:* first **pin the real format** from the MSX2 TH (cheap, no code). If it is
  256-byte blocks and interop is wanted → A; otherwise → B. Lean A to stay interop-true,
  but B is defensible and much smaller.

**D2 — Reader byte-source abstraction.** **RESOLVED: A (getbyte indirection).**
`ascii_read_lines` calls `fat_io_getbyte` directly.
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
  uses the existing typed-tape harness on `C-BIOS_MSX1_EU_TAPE --cart`).
- **Codec differential (pins the format):** extend `cas_encode.build_cas_ascii` /
  `cas_decode` for the `$EA` header + D1 block format; assert the WAV zerobas writes
  decodes to the expected `$EA`-framed ASCII stream, and that a codec-built ASCII `.cas`
  loads on zerobas. (Reading the *data* bytes of an ASCII `.cas` is not a ROM read.)
- **Host unit test:** the tape sink's block-framing byte counter (if D1=A) — emulator-free.
- **Gate:** a new cell in [`../../probes/basic/basic_probe_cas_options.py`](../../probes/basic/basic_probe_cas_options.py)
  (or a dedicated `basic_probe_cas_ascii.py`); update the tape option-surface audit Tier 2
  → done. No regression on `diskbasic-acceptance` (34) / `unit-test` (38).

## 8. Non-goals

- Numeric `INPUT#`, tape *sequential channels* (`OPEN"CAS:" FOR INPUT|OUTPUT`) — the
  other, larger Tier-2 item, tracked separately.
- No change to the tokenised cassette SAVE/LOAD paths, the (de)tokeniser, the disk ASCII
  paths, or the tape signal layer (TAPOON/TAPOUT/TAPION/TAPIN).
- `CSAVE` stays tokenised-only (ASCII save is spelled `SAVE"CAS:",A`, matching MSX).
