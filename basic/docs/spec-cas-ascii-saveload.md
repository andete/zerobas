<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec (signed off): cassette ASCII program SAVE `,A` + ASCII CLOAD/LOAD

**Status: M0 DONE 2026-07-08 (format pinned; D1 resolved → interop-faithful 256-byte
blocks). No implementation code yet — M1 (ASCII LOAD) is the next action.** The cassette
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
- **M1 — ASCII CLOAD / LOAD"CAS:"** (§4) + gate. *(next)*
- **M2 — SAVE"CAS:name",A** (§5) + gate.

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
onto the first data block, `call new_prog` (LOAD replaces), then drive `ascii_read_lines`
with the tape as its byte source (D2). The tape getbyte wrapper counts bytes and
re-`TAPION`s at each **256-byte** boundary (§0.1) so a multi-block program reads across
leaders; `ascii_read_lines` stops at the first **Ctrl-Z (`$1A`)**, so trailing padding is
never read. `,R` handling is unchanged — the `LOAD"CAS:",R`/`RUN` caller already runs on
the flag (Tier-1 `parse_close_run`).

## 5. Design — SAVE"CAS:name",A (Milestone 2)

**Parse.** In `sav_is_cas` ([`../save.asm:339`](../save.asm)), the `,A` after the
`"CAS:"` name currently → `load_error`; make it accept `,A` (any case) → `cas_ascii_save`,
anything else still errors. Mirrors `sav_ascii_flag` on the disk side.

**Frame + sink (`cas_ascii_save`).** Write the `$EA` header block (`TAPOON` long + 10×
`$EA` + `tape_name_emit` + `TAPOOF`), then walk the program with LIST's detokeniser
feeding a **tape sink**: set `PRDEST:=1`, `PRDEV:=<tape>` (a new value), `TAPOON`
short (open first data block), `call list_walk`, append the EOF `$1A`, pad the final
block to 256 with `$1A`, close (`TAPOOF`), restore `PRDEST:=0`. The new `pchar` sink case
(`PRDEV=<tape>`) writes each byte via `TAPOUT` and counts bytes, re-framing
(`TAPOOF` + `TAPOON` short) every **256** (§0.1). Baud is whatever the active word selects
(`SCREEN,,,baud` / default 1200 via the TAPOON `cas_seed`); no new speed parsing.

## 6. Decisions (signed off 2026-07-08 — see the header for the résumé)

**D1 — Cassette ASCII block format.** **RESOLVED (M0) → A, interop-faithful 256-byte
blocks.** The MSX2 TH + three real ASCII tapes pinned the format unambiguously (§0.1):
`$EA`×10 header, 256-byte data blocks with short leaders, Ctrl-Z EOF, CR+LF lines. The
per-256 re-framing reuses our existing per-block `TAPOON`/`TAPOOF`/`TAPION` machinery,
the read side is padding-robust (stop at first `$1A`), and it keeps interop for all
program sizes — the three tapes double as M1 load oracles. Own-design single-block (the
rejected alternative B) would have been cheaper but lost real-MSX interop for >256-byte
programs.

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

- Numeric `INPUT#`, tape *sequential channels* (`OPEN"CAS:" FOR INPUT|OUTPUT`) — the
  other, larger Tier-2 item, tracked separately.
- No change to the tokenised cassette SAVE/LOAD paths, the (de)tokeniser, the disk ASCII
  paths, or the tape signal layer (TAPOON/TAPOUT/TAPION/TAPIN).
- `CSAVE` stays tokenised-only (ASCII save is spelled `SAVE"CAS:",A`, matching MSX).
