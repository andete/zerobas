<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Closure spec: CAS: options — Tier 3 (`CLOAD` name-matching + `CLOAD?` verify)

**Status: BOTH ITEMS IMPLEMENTED + GATED (2026-07-09) — tape/CAS Tier-3 COMPLETE.**
Item B (`CLOAD?` verify) landed in `basic/cload.asm` (`do_cload` PRINT_TOKEN detection +
`cas_put` compare-mode + `ctp_verify_done` + `verify_error`); gate
[basic_probe_cas_verify.py](../../probes/basic/basic_probe_cas_verify.py) (4/4: Ok /
mismatch / non-destructive / ASCII-reject). No-regression: cas_match 6/6, cas_ascii/
cas_verbs/cas_options/tape_save, diskbasic-acceptance 34/34, unit-test 38/38. **Build note:
the BASIC ROM page is now byte-exactly full (code ends at `$8000`)** — Item B needed a
size-reclaim pass (cas_put BC-free, merged header read, tightened name-flag + verify-done);
the single dropped nicety is exact-prefix length-mismatch detection (§B).

All four open decisions resolved (see end); decision #1 oracle-confirmed on the stock
CF-3300. Item A (name-matching) landed in `basic/cload.asm` (`cas_open_match` /
`cas_skip_data` / `cas_capture_name`), threaded through `do_cload` / `do_load` / `do_run`
(cload.asm) and `merge_cas` / `oo_dev_cas` (files.asm); gate
[basic_probe_cas_match.py](../../probes/basic/basic_probe_cas_match.py) (6/6), oracle
evidence [basic_probe_cas_match_cf3300.py](../../probes/basic/basic_probe_cas_match_cf3300.py);
no-regression cas_ascii/cas_verbs/cas_options/tape_save + diskbasic-acceptance 34/34 +
unit-test 38/38. Companion to the sweep
[cas-device-option-surface.md](cas-device-option-surface.md) §4 "Tier 3" and the Tier-1
spec [spec-cas-device-closure.md](spec-cas-device-closure.md). This is the **last** open
scope on the tape/CAS option surface — closing it fully closes the `CLOAD` grammar.

Scope confirmed by the user 2026-07-09: **both** Tier-3 items.

**Clean-room basis.** Contracts are the *published* MSX-BASIC user-syntax (MSX2 Technical
Handbook; MSX-BASIC reference) plus this project's own code. No reference ROM read
([no-reference-rom-disasm](../../README.md)). The cassette block layout ($D3/$EA header =
10× id + 6-char name; data blocks) is the already-cited MSX2 TH cassette chapter, as used
by [cload.asm](../../basic/cload.asm) and [cas_encode.py](../../probes/lib/cas_encode.py).

---

## 0. What is open, and why it was deferred

The `CLOAD` row of the option matrix
([cas-device-option-surface.md](cas-device-option-surface.md) §1) is `◐` on two counts:

1. **`CLOAD"name"` / `LOAD"CAS:name"` — the name is parsed-past and *ignored*.** We open
   the **next** tape file regardless. This is an own-design simplification (no tape
   catalogue — [cload.asm:36](../../basic/cload.asm)); Tier 3 turns it into real
   **name-matching** (skip non-matching files until the named one, or "file not found").
2. **`CLOAD?` verify — not implemented at all.** The compare-after-read form.

Both were deferred from Tier 2 as "closer to Tier-2 effort" because each needs a new read
mode: name-matching needs a **skip-non-matching-file loop**, and verify needs a
**compare-instead-of-store** path. This spec pins both.

---

## Item A — `CLOAD["name"]` / `LOAD"CAS:name"` name-matching

### Documented surface
`CLOAD "name"` and `LOAD "CAS:name"` load the tape file **named `name`**, skipping any
earlier files on the tape. Bare `CLOAD` / `LOAD"CAS:"` load the **next** file (unchanged).
Name = up to 6 chars, space-padded, case as-typed (tape names are stored verbatim; MSX
compares the 6-byte field). If the named file is never found before the tape runs out, it
is a load failure (the tape stalls on silence → our existing `load_error`, see §A.4).

### Current behaviour (the gap)
`do_tape_prog` ([cload.asm:284](../../basic/cload.asm)) reads header byte 0, then **skips
the remaining 15 header bytes** (`ctp_skip_hdr`) — the 6-char name (header bytes 10–15) is
discarded. The callers likewise discard the name: `do_cload`'s `skip_quoted`
([cload.asm:268](../../basic/cload.asm)) and `do_load`'s `do_load_fn`
([cload.asm:112](../../basic/cload.asm)) both advance HL past the quoted string without
capturing it. So every caller loads whatever file comes next.

### Contract to implement
1. **A requested-name buffer, `CAS_WANT` (6 bytes) + a flag `CAS_WANT_ON`.**
   - Bare `CLOAD` / `LOAD"CAS:"` (no name): `CAS_WANT_ON = 0` → **match-first / load-next**,
     exactly today's behaviour (no regression).
   - `CLOAD"n"` / `LOAD"CAS:n"`: stage the 6-char, space-padded, up-cased? — **as-typed**
     name into `CAS_WANT` and set `CAS_WANT_ON = 1`. (See §A.5 on case.)
2. **Header capture in `do_tape_prog`.** The 16-byte header read captures bytes 10–15 (the
   name) into a scratch `CAS_HDRNAME` (6 bytes) instead of blind-skipping them. Byte 0 (id)
   is read and kept as today for the $D3/$EA dispatch.
3. **Match test.** After a full header is read:
   - `CAS_WANT_ON = 0` → this file is the target; proceed to load (existing dispatch on the
     id: $D3 → tokenised, $EA → `cas_ascii_*`, else → `load_error`).
   - `CAS_WANT_ON = 1` → compare `CAS_HDRNAME` (6) vs `CAS_WANT` (6). Match → load. Mismatch
     → **skip this file's data** (§A.4) and loop back to read the next header.
4. **Skip-non-matching-file (`cas_skip_data`).** After a header with a non-matching name,
   the data must be consumed to reach the next file's header leader (the tape is real-time;
   we consume, we do not seek). **Format-aware, keyed on the just-read id:**
   - `$D3` tokenised: one data block. `TAPION`, then read the line-link chain discarding
     bytes until the `$0000` end-link — the same length-driven walk as `ctp_line`/`ctp_body`
     but storing nothing. (One block; ends cleanly at `$0000`.)
   - `$EA` ASCII: N× 256-byte blocks. Reuse the `cal_refill` block loop (`TAPION` +
     `TAPIN`×256) **discarding**, block after block, until a block contains Ctrl-Z (`$1A`) —
     the ASCII EOF that every producer puts in the last block (spec-cas-ascii-saveload §0.1).
   - unknown id: `load_error` (an unrecognised file mid-tape is corruption; do not spin).
   Then loop to the next header (`TAPION` for the next header block).
5. **Not-found termination.** If the tape runs out before a match, the next `TAPION`/`TAPIN`
   stalls on silence and returns CF (the same real-tape end condition the whole reader is
   built around, [cload.asm:251](../../basic/cload.asm)) → `load_error`. We do **not** invent
   a catalogue-backed "file not found"; the walls behave as tape always has.

### Design
- **Matching lives in `do_tape_prog`**, so all four callers (`CLOAD`, `LOAD"CAS:"`,
  `RUN"CAS:"`, `MERGE"CAS:"`) get name-matching uniformly. The callers change only to
  **capture** the name into `CAS_WANT` instead of discarding it (a small edit to
  `skip_quoted` → a capturing variant, and to `do_load_fn` / `dr_cas_fn`; `merge_cas`'s
  entry likewise). `CAS_WANT_ON` is cleared at each caller's entry and set only when a name
  is present, so the bare forms keep today's load-next semantics.
- **`do_tape_prog` becomes a loop** `ctp_open: TAPION → read+capture header → match? →
  yes: load (fall through to today's body); no: cas_skip_data → jr ctp_open`. Today's body
  (from the `ctp_hdr_tokenised` label down) is unchanged; only a matching pre-amble wraps it.
- **`cas_skip_data` reuses the existing byte machinery** — the tokenised walk is a
  store-nothing twin of `ctp_line`; the ASCII discard is `cal_refill` with no serve. State
  in RAM across `TAPIN` (the [tape-realtime-read-buffering](../../README.md) rule), never on
  the stack.
- **Note on the `$EA` name check ordering.** The name is in the header block (before any
  data block), so the id + name are both known *before* we commit to loading or skipping —
  no wasted read.

### §A.5 Case handling — DECIDED: case-sensitive (oracle-confirmed 2026-07-09)
**Black-box characterized on the stock National_CF-3300** (no ROM read — observed behaviour
only). Method: an auto-running `AUTOEXEC.BAS = 10 CLOAD"<key>"` on a data disk, a cassette
whose one file is `10 POKE&HD005,&HA5`, cold-boot, then read the program area at `TXTBASE`
to see whether the tape program replaced the AUTOEXEC line (token `$98`=POKE loaded vs
`$9B`=CLOAD not). Zero typed keys (the CF-3300 date prompt hijacks typed input; AUTOEXEC
runs regardless). Result matrix (reproduced twice):

| tape file | search key | loaded? |
|---|---|---|
| `abc` | `CLOAD"abc"` (exact, control) | **YES** |
| `abc` | `CLOAD"xyz"` (absent, control) | **no** |
| `abc` | `CLOAD"ABC"` (UC key / LC file) | **no** |
| `ABC` | `CLOAD"abc"` (LC key / UC file) | **no** |

Two findings:
1. **Case-SENSITIVE.** Both case-variant rows fail to match → the compare is byte-exact, not
   up-cased. **DECISION: case-sensitive**, byte-exact on the 6-space-padded field.
2. **The stock CF-3300 does REAL name-matching** — `CLOAD"xyz"` against a tape holding only
   `abc` loads *nothing* (it does not fall back to "load next"). So Item A's matching is
   **more** oracle-faithful than our current "accept-and-discard the name, load next"
   shortcut ([cload.asm:36](../../basic/cload.asm)); implementing it aligns us *toward* the
   oracle, not away.

(Aside, also observed: on the MSX1 CF-3300, `LOAD"CAS:name"` itself is a no-op — `CLOAD` is
the working stock cassette-load verb. Our `LOAD"CAS:"` is therefore wholly our own
extension; its name-matching should mirror `CLOAD`'s case-sensitive compare for internal
consistency.) Characterization harness: `scratchpad/cf3300_final.py` (to be promoted into a
committed `probes/basic/` oracle probe when Item A's gate lands). NB fixtures must use
collision-safe filenames — macOS's case-insensitive FS silently merges `abc`/`ABC` paths
(cost a false "inconclusive" during characterization).

### Acceptance (gate)
New cells in [basic_probe_cas_verbs.py](../../probes/basic/basic_probe_cas_verbs.py) (or a
dedicated `basic_probe_cas_match.py`) driven on `C-BIOS_MSX1_EU_TAPE --cart build/basic.rom`:
- **A1 — skip-and-match (tokenised).** Fixture `build_cas_basic("AAA", progA) +
  build_cas_basic("BBB", progB)`; `CLOAD"BBB"` loads progB (witness distinguishes A vs B),
  proving AAA was skipped.
- **A2 — skip-and-match (ASCII).** Same, `build_ascii_cas` files, `LOAD"CAS:BBB"` — proves
  the multi-256-byte-block ASCII skip.
- **A3 — mixed skip.** An ASCII file then a tokenised file; match the second — proves
  `cas_skip_data` dispatches on the id.
- **A4 — bare form no-regression.** Bare `CLOAD` still loads the first/next file (existing
  `basic_probe_cas_ascii.py` cells stay green).
- **A5 — not found.** `CLOAD"ZZZ"` on a tape with only AAA/BBB → clean `load_error`
  (no hang; the stall-on-silence CF path).

---

## Item B — `CLOAD?["name"]` verify

### Documented surface
`CLOAD? ["name"]` reads the (named, per Item A) tape program and **compares** it against the
program currently in memory, **without altering memory**. Identical → `Ok`; any difference
(or length mismatch) → **`Verify error`**. Used to confirm a `CSAVE` wrote correctly.

### Current behaviour (the gap)
Not implemented. `CLOAD?` tokenises to `CLOAD_TOKEN` + `PRINT_TOKEN` (`?` abbreviates PRINT,
[interp.asm:107](../../basic/interp.asm)). `do_cload` today only handles bare / quoted-name
forms; a leading `PRINT_TOKEN` falls into `load_error` (`jp nz,load_error`,
[cload.asm:66](../../basic/cload.asm)).

### Contract to implement
1. **Recognise the verify form in `do_cload`.** After `skip_spaces`, if `(HL) ==
   PRINT_TOKEN`, it is `CLOAD?`: `inc HL`, set a `CAS_VERIFY` flag, then parse an optional
   quoted name exactly as the plain form (feeding Item A's `CAS_WANT`), and enter the tape
   reader in verify mode. (`CLOAD` proper clears `CAS_VERIFY`.)
2. **Compare-mode read.** `do_tape_prog`, when `CAS_VERIFY = 1`, must **not** mutate the
   program store (`CLPTR`/`TXTBASE`/`PRGEND`/`relink`) or clear the program. Instead, for
   each byte it would have stored, compare against the corresponding in-memory program byte
   and track a mismatch. A length difference (tape ends earlier/later than the in-memory
   `$0000` end-link) is also a mismatch.
3. **Outcome.** End of tape program: `CAS_VERIFY` mismatch flag set → print `Verify error`
   (new string, §B.4) via the standard error sink; clear → return silently to the REPL
   (`Ok`). Motor off (`TAPIOF`) on both paths. **Memory is never touched** — the current
   program remains loaded and runnable.
4. **Scope: tokenised (`$D3`) only.** Verify compares the *stored image*, which is only
   well-defined for a tokenised file against the tokenised in-memory program. An `$EA` ASCII
   file under `CLOAD?` → `load_error` (verify of a re-tokenised ASCII stream is out of
   charter; document it). This matches the practical use (`CLOAD?` after a `CSAVE`, which
   writes $D3).

### Design
- **A `CAS_VERIFY` flag threaded into the tokenised reader body** (`ctp_line`/`ctp_body`).
  The store steps become "store **or** compare": where the plain path does `ld (hl),a`, the
  verify path does `cp (hl)` and, on non-equal, sets a `CAS_VMISMATCH` sticky flag but
  **keeps reading to the end** (so the tape is fully consumed and the motor stops cleanly —
  do not abort mid-read, which would leave the tape mid-block). The link/lineno/body walk is
  otherwise identical (it must, to line up byte offsets against the in-memory program).
  - The in-memory comparand pointer walks the current program from `TXTTAB`/`TXTBASE` in
    lock-step with the tape read. A length mismatch is caught when either side ends first:
    tape `$0000`-link while in-memory has more, or vice-versa.
  - **Bounds:** verify never writes, so `ctp_oom` cannot fire; but the comparand pointer must
    stop at `PRGEND` — reads past it are a length mismatch, not a store overflow.
- **Do not duplicate the ~90-line reader.** Add the mode branch inside the existing body
  (a handful of `ld a,(CAS_VERIFY)` / branch points at each store), the same way the disk
  and tape readers already share structure. If the branching bloats the hot path
  unacceptably, the fallback is a separate `ctp_verify_line` twin — decide at code time; the
  spec's contract is mode-flagged single-reader first.
- **Interaction with Item A.** `CLOAD?"name"` composes: Item A's matching selects the file,
  then Item B verifies it. `CLOAD?` (bare) verifies the next file. No extra work — verify is
  orthogonal to selection.

### §B.3a As-built length-mismatch caveat
The BASIC ROM page filled exactly to `$8000` implementing this, so the explicit
"in-memory program has MORE lines than the tape" end-check was dropped to reclaim space.
In practice almost all length differences are still caught: the saved link words are
absolute addresses, so a program of a different shape differs byte-for-byte and trips
`CAS_VMIS` during the compare. The only undetected case is a tape that is an EXACT PREFIX
of a longer in-memory program (every compared byte equal, tape ends first) — outside the
verify use case (confirming a same-length `CSAVE` round-trip). Documented limitation.

### §B.4 New error string
Add `err_verify: db "Verify error",13,10,0` and a `load_verify_error` entry that prints it
(mirroring `load_error`/`err_prog_mem` in [cload.asm](../../basic/cload.asm)). "Verify
error" is the standard MSX-BASIC message (MSX-BASIC reference error table — published
user-facing text, not ROM code).

### Acceptance (gate)
Cells alongside Item A's:
- **B1 — verify OK.** `CSAVE"P"` (or a pre-built $D3 fixture matching a typed program),
  then `CLOAD?"P"` → no error, program unchanged (a following `RUN` still works / witness
  intact). Drive by: type program, build the matching `build_cas_basic` fixture, `CLOAD?`.
- **B2 — verify mismatch.** In-memory program differs from the tape fixture by one byte →
  `Verify error` printed (assert the message in the screen capture), **and** memory
  unchanged (the in-memory witness/program survives — proves no mutation).
- **B3 — memory untouched.** After B1 and B2, `LIST`/witness shows the original program
  (verify must be non-destructive — the whole point).
- **B4 — ASCII under CLOAD? → load_error** (documented scope boundary).

---

## Gates summary

Both items land standing cells so they cannot silently regress (the disk-arc lesson). Target
runner: extend [basic_probe_cas_verbs.py](../../probes/basic/basic_probe_cas_verbs.py) (it
already builds tape fixtures and drives the typed C-BIOS tape harness) or a sibling
`basic_probe_cas_match.py`; register in the tape/BASIC acceptance net so
`diskbasic-acceptance` / `make -C tape test` guard it. No-regression guard: the existing
`basic_probe_cas_ascii.py` and `basic_probe_cas_verbs.py` cells (bare-form load, RUN/MERGE/
OPEN) stay green.

Remember: machine probes run the installed `zerobas-msx1.ips` **unless** `--cart` reads
build/basic.rom directly — these cells use `--cart`, so a plain `make -C basic` rebuild
suffices, no IPS reinstall ([ips-rebuild-after-basic-change](../../README.md)).

---

## Open decisions for sign-off — ALL RESOLVED 2026-07-09

1. **Case sensitivity of name-matching** (§A.5) — **case-sensitive**, byte-exact on the
   6-space-padded field. ✅ *Oracle-confirmed on the stock CF-3300* (see §A.5 matrix), not
   just a preference.
2. **`CLOAD?` scope = tokenised only** (§B.4) — ASCII under `CLOAD?` → `load_error`.
   ✅ approved.
3. **Single mode-flagged reader vs. a `ctp_verify` twin** (§B design) — mode-flagged single
   reader; fall back to a twin only if the hot path suffers. ✅ approved.
4. **Gate home** — new sibling `basic_probe_cas_match.py`. ✅ approved.

**Spec fully signed off — cleared to implement (Item A then Item B, committing per item with
its gate).**

## Provenance
Drafted 2026-07-09 from the sweep + static read of [cload.asm](../../basic/cload.asm),
[interp.asm](../../basic/interp.asm), [sysvars.inc](../../basic/sysvars.inc), and
[cas_encode.py](../../probes/lib/cas_encode.py). Published user-syntax for `CLOAD"name"` /
`CLOAD?` and the "Verify error" message is the MSX-BASIC reference; the cassette block
layout is the MSX2 Technical Handbook. No reference ROM read.
